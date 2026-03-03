last updated: 2026-03-03

# skill-maintainer

Maintenance tooling for the skill ecosystem in this repo. Not a skill, not a plugin -- just scripts, hooks, and a slash command that run from within this repo.

There is exactly one thing that runs automatically. Everything else runs when you ask for it.

## what runs automatically

### Pre-commit hook (git)

**When:** every `git commit` that includes a staged `SKILL.md` file.

**What it does:**
1. `git diff --cached --name-only --diff-filter=ACM` lists staged files
2. Filters for files ending in `SKILL.md`
3. If none found, exits immediately (cost: ~1ms)
4. For each staged SKILL.md, runs `uv run agentskills validate <skill-dir>`
5. If any fail validation, the commit is blocked with an error message

**What it checks:** the [Agent Skills spec](https://agentskills.io) -- required frontmatter fields (name, description), naming conventions (kebab-case, no consecutive hyphens), allowed fields only, etc.

**Where:** `.git/hooks/pre-commit` (bash script, 28 lines)

**Side effects:** none. Read-only check. Either the commit proceeds or it doesn't.

That's it. Nothing else runs unless you invoke it.

## workflow

### before making changes

```
uv run python skill-maintainer/scripts/run_tests.py
```

Note what's green. This is your baseline. If something is already red, decide whether to fix it now or leave it for later.

### after making changes

```
uv run python skill-maintainer/scripts/run_tests.py
```

Nothing should go from green to red unless you intended it. Use `--verbose` to see all results including passes.

### periodic maintenance

```
/maintain
```

Pulls upstream sources, checks for doc changes, runs the quality report, and proposes updates to `best_practices.md`. Run this when you want to sync with upstream and review the maintenance checklist. Or run the phases individually (see scripts below).

### individual checks

| Script | Purpose | Example |
|--------|---------|---------|
| `run_tests.py` | Full red/green test suite | `uv run python skill-maintainer/scripts/run_tests.py --category repo` |
| `quality_report.py` | Detailed quality table (validation, budget, staleness) | `uv run python skill-maintainer/scripts/quality_report.py` |
| `validate_skill.py` | Spec + best practice validation for one or all skills | `uv run python skill-maintainer/scripts/validate_skill.py --all` |
| `check_freshness.py` | Staleness check on metadata.last_verified dates | `uv run python skill-maintainer/scripts/check_freshness.py --quiet` |
| `measure_content.py` | Per-file token budget breakdown | `uv run python skill-maintainer/scripts/measure_content.py --skill tui-design` |
| `pull_sources.py` | Pull tracked coderef repos, detect changes | `uv run python skill-maintainer/scripts/pull_sources.py --no-pull` |
| `check_upstream.py` | Fetch Claude Code docs, detect page changes | `uv run python skill-maintainer/scripts/check_upstream.py --no-save` |
| `query_log.py` | Query the changes.jsonl audit log | `uv run python skill-maintainer/scripts/query_log.py --tail 5` |

## what you run manually

### /maintain -- full maintenance pass

**When:** you type `/maintain` in Claude Code.

**What it does:** runs three scripts in sequence, then has Claude review the results and propose updates to `best_practices.md`. Four phases:

| Phase | Script | What happens |
|-------|--------|-------------|
| 1 | `pull_sources.py` | Git pulls 10 tracked repos under `coderef/`, reports what changed |
| 2 | `check_upstream.py` | Fetches Claude Code docs from the web, compares hashes, reports changes |
| 3 | `quality_report.py` | Validates all skills, checks token budgets and staleness |
| 4 | (Claude) | Reads change data + `best_practices.md`, proposes specific edits if needed |

Phase 4 never auto-writes. Claude shows you proposed changes and waits for approval.

**Where:** `.claude/commands/maintain.md`

### individual scripts

All scripts run via `uv run python skill-maintainer/scripts/<name>.py` from the repo root.

You can run any of these independently at any time. `/maintain` just orchestrates the first three.

## scripts: what each one does under the hood

### pull_sources.py

Pulls 10 tracked git repos under `coderef/` and detects what changed since the last run.

**Tracked repos** (hardcoded in `TRACKED_REPOS` constant):
```
coderef/agentskills              Agent Skills spec
coderef/skills                   Anthropic example skills
coderef/claude-plugins-official  Official plugin directory
coderef/knowledge-work-plugins   Enterprise patterns
coderef/claude-agent-sdk-python  Claude Agent SDK
coderef/claude-cookbooks         Capability patterns
coderef/mcp/modelcontextprotocol MCP spec
coderef/mcp/python-sdk           Python MCP SDK
coderef/mcp/ext-apps             MCP Apps SDK
coderef/mcp/experimental-ext-skills  Skills-over-MCP
```

**Step by step:**
1. Loads stored SHAs from `state/upstream_hashes.json` under the `"local_repos"` key
2. For each repo: resolves symlinks via `Path.resolve()`, checks `.git` exists
3. Records current HEAD SHA (`git rev-parse HEAD`)
4. Runs `git pull --ff-only` (skipped with `--no-pull`)
5. Records HEAD SHA again after pull
6. Compares post-pull SHA to stored SHA:
   - No stored SHA -> status `NEW`
   - SHA differs -> status `CHANGED`, captures `git log --oneline old..new`
   - SHA matches -> status `UP_TO_DATE`
7. Saves updated SHAs to `upstream_hashes.json["local_repos"]` (skipped with `--no-save`)
8. Appends a `source_pull` event to `changes.jsonl` (skipped with `--no-log`)

**Flags:** `--no-pull` (check only), `--no-save` (don't persist), `--no-log` (skip audit log)

### check_upstream.py

Fetches Claude Code documentation from the web and detects page-level changes.

**Step by step:**
1. Fetches `https://code.claude.com/docs/llms-full.txt` (single HTTP GET via httpx)
2. Splits the response by `Source: <url>` delimiters into per-page sections
3. Loads stored hashes from `state/upstream_hashes.json` (URL-keyed, top level)
4. For each of 9 watched pages (hardcoded in `DEFAULT_PAGES`):
   - SHA-256 hashes the page content (first 16 hex chars)
   - Compares to stored hash: `NEW` if no prior hash, `CHANGED` if differs
5. Saves updated hashes (skipped with `--no-save`)
6. Appends an `upstream_check` event to `changes.jsonl` (skipped with `--no-log`)

**Watched pages:** skills, plugins, plugins-reference, discover-plugins, plugin-marketplaces, hooks-guide, hooks, sub-agents, memory

**Flags:** `--url-file <path>` (custom URL list), `--no-save`, `--no-log`

### quality_report.py

Runs validation, token budget, and staleness checks on every skill in the repo.

**Step by step:**
1. Walks repo with `rglob("SKILL.md")`, skipping `coderef/`, `.venv/`, `node_modules/`, etc.
2. For each skill directory:
   - **Validation:** calls `skills_ref.validator.validate()` (the same validator the pre-commit hook uses)
   - **Token budget:** sums character counts of all text files in the skill dir, divides by 4. Thresholds: 4000 (warn), 8000 (critical)
   - **Staleness:** reads `metadata.last_verified` from frontmatter, computes days since. >30 days = stale
   - **Description quality:** checks for WHAT verb ("handles", "generates", etc.) and WHEN trigger ("use when", "when user", etc.)
3. Prints a table with all results
4. Appends a `quality_report` event to `changes.jsonl` (skipped with `--no-log`)
5. Exits 1 if any skill fails validation, 0 otherwise

**Flags:** `--dir <path>` (custom root), `--no-log`

### validate_skill.py

Validates one or all skills against the Agent Skills spec plus best-practice checks.

**Step by step:**
1. For each skill:
   - Runs `skills_ref.validator.validate()` (spec compliance: name format, required fields, allowed fields)
   - Runs additional checks: line count (max 500), word count (max 5000), description quality (WHAT + WHEN pattern), angle brackets in description, unlinked reference files
2. Reports errors (spec violations) and warnings (best practice issues) separately

**Flags:** `--all` (validate every skill), `--verbose` (show all details), or pass a single skill path

### check_freshness.py

Checks `metadata.last_verified` dates across all skills.

**Step by step:**
1. Discovers all SKILL.md files
2. For each: parses frontmatter, reads `metadata.last_verified`
3. Computes days since that date, flags if over threshold

**Flags:** `<skill-name>` (check one), `--threshold <days>` (default 30), `--quiet` (only show stale)

### measure_content.py

Detailed token budget measurement with per-file breakdown.

**Step by step:**
1. Discovers all skills
2. For each skill: walks all text files, classifies by type (skill_md, reference, script, agent, etc.), measures lines/words/chars
3. Estimates tokens as chars / 4 (rough approximation)
4. Generates a markdown report with per-skill and per-file breakdown

**Flags:** `--skill <name>` (measure one), `--dir <path>`, `--output <file>` (write report to file)

### query_log.py

Queries the append-only audit log (`changes.jsonl`).

**Step by step:**
1. Reads `state/changes.jsonl` line by line (each line is a JSON object)
2. Filters by date range, event type, or tail count
3. Formats output based on event type:
   - `source_pull`: "3/10 repos changed: agentskills, skills, cookbooks"
   - `upstream_check`: "2 pages changed: skills, plugins"
   - `quality_report`: "9/9 valid, 5 over budget, 0 stale"

**Flags:** `--days <n>` (recent window), `--type <event>` (filter), `--tail <n>` (last N events)

## state files

All state lives in `skill-maintainer/state/`. Both files are gitignored and auto-generated.

### upstream_hashes.json

```json
{
  "https://code.claude.com/docs/en/skills": "7fdcca7ff9e64a8c",
  "https://code.claude.com/docs/en/plugins": "6f472f023ede34f8",
  ...
  "local_repos": {
    "coderef/agentskills": "abc123def456...",
    "coderef/skills": "789012ghi345...",
    ...
  }
}
```

Top-level keys are URLs (written by `check_upstream.py`). The `local_repos` key holds git SHAs (written by `pull_sources.py`). The two scripts share the file but use different key namespaces so they don't interfere.

### changes.jsonl

Append-only audit log. One JSON object per line. Three event types:

```json
{"type": "source_pull", "date": "2026-03-03", "repos_checked": 10, "repos_changed": 3, "changes": [...]}
{"type": "upstream_check", "date": "2026-03-03", "changed_pages": [...], "total_changed": 2}
{"type": "quality_report", "date": "2026-03-03", "skills": 9, "valid": 9, "over_budget": 5, "stale": 0}
```

### metadata.last_verified (in SKILL.md files)

Not a state file, but part of the system. Each SKILL.md has this in frontmatter:

```yaml
metadata:
  last_verified: 2026-02-25
```

This is what `check_freshness.py` and `quality_report.py` check. Update it when you review or modify a skill.

## adding a new tracked source

Edit `TRACKED_REPOS` in `pull_sources.py`. Clone or symlink the repo into `coderef/`. That's it.

## adding a new upstream doc page to watch

Edit `DEFAULT_PAGES` in `check_upstream.py`. Add the full URL. The page must exist in `llms-full.txt`.
