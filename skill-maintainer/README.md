last updated: 2026-03-06

# skill-maintainer

Installable Python package providing a `skill-maintain` CLI for monitoring, validating, and maintaining Claude Code skill repos. Runs as project-scoped tooling within fb-claude-skills and is git-installable for use in other repos.

## installation

### within fb-claude-skills (already available)

After `uv sync --all-packages`, the `skill-maintain` command is available in the workspace venv. No additional setup needed.

### in another repo (git install)

```bash
uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=skill-maintainer
```

Then initialize per-repo config:

```bash
skill-maintain init
```

This creates `.skill-maintainer/config.json` in the current directory with default upstream URLs and tracked repo paths.

## data flow

skill-maintainer is a maintenance pipeline. Think of it as a DAG with three input types, seven processing stages, and two output layers.

```
INPUTS                      PROCESSING                      STATE / OUTPUT
------                      ----------                      --------------

SKILL.md files              validate ──────────────────┐
(local, discovered          quality ────────────────────┤
 by glob)                   freshness ──────────────────┤──► CLI reports
                            measure ────────────────────┤    (tables, pass/fail,
upstream docs               upstream ──────────────────►┤     exit codes for CI)
(llms-full.txt via HTTP)    sources ───────────────────►┤
                            test ───────────────────────┘
tracked git repos                                              .skill-maintainer/
(coderef/ or configured     log ──────────────────────────►   state/upstream_hashes.json
 paths)                                                        state/changes.jsonl
```

The `/maintain` slash command orchestrates the pipeline in sequence: `sources → upstream → quality → review`.

## what runs automatically

### pre-commit hook (git)

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

## CLI reference

All subcommands accept `--dir <path>` to target a skill repo other than the current directory.

| Command | What it does |
|---------|-------------|
| `init` | Create `.skill-maintainer/config.json` in the target repo |
| `validate` | Validate skills against Agent Skills spec + best practices |
| `quality` | Unified report: validation + token budget + freshness + description quality |
| `freshness` | Check `metadata.last_verified` staleness across all skills |
| `measure` | Token budget measurement with per-file breakdown |
| `test` | Red/green test suite (skills, plugins, repo hygiene) |
| `upstream` | Fetch Claude Code docs via llms-full.txt, detect page changes |
| `sources` | Pull tracked git repos, detect changes since last run |
| `log` | Query the `.skill-maintainer/state/changes.jsonl` audit log |

### examples

```bash
# baseline before making changes
skill-maintain test

# after making changes -- nothing should go green to red
skill-maintain test --verbose

# full maintenance pass (or use /maintain in Claude Code)
skill-maintain sources
skill-maintain upstream
skill-maintain quality

# target a different repo
skill-maintain quality --dir ~/path/to/other-skill-repo

# check a single skill's token budget
skill-maintain measure --skill tui-design

# see last 5 audit log entries
skill-maintain log --tail 5

# check staleness only, suppress passing skills
skill-maintain freshness --quiet
```

## workflow

### before making changes

```bash
skill-maintain test
```

Note what's green. This is your baseline. If something is already red, decide whether to fix it now or leave it.

### after making changes

```bash
skill-maintain test
```

Nothing should go from green to red unless you intended it. Use `--verbose` to see all results including passes.

### periodic maintenance

```
/maintain
```

Pulls upstream sources, checks for doc changes, runs the quality report, and proposes updates to `.skill-maintainer/best_practices.md`. Run this when you want to sync with upstream and review the maintenance checklist. Or run the phases individually:

```bash
skill-maintain sources   # phase 1: pull tracked repos
skill-maintain upstream  # phase 2: check upstream docs
skill-maintain quality   # phase 3: validate all skills
# phase 4: Claude reviews results and proposes best_practices.md edits
```

Phase 4 never auto-writes. Claude shows proposed changes and waits for approval.

**Where:** `.claude/commands/maintain.md`

### applying best practices to another repo

Two options depending on whether you want a permanent install or a one-off check.

**Option A: `--dir` (no install needed)**

Run from within fb-claude-skills, targeting the other repo:

```bash
# initialize config in the target repo
skill-maintain init --dir ~/claude/mlx-skills

# validate and check quality
skill-maintain validate --all --dir ~/claude/mlx-skills
skill-maintain quality --dir ~/claude/mlx-skills
skill-maintain freshness --dir ~/claude/mlx-skills
skill-maintain measure --dir ~/claude/mlx-skills
```

**Option B: git-install (standalone)**

Add skill-maintainer as a dependency in the target repo:

```bash
cd ~/path/to/other-repo
uv add "skill-maintainer @ git+https://github.com/fblissjr/fb-claude-skills#subdirectory=skill-maintainer"
skill-maintain init
skill-maintain validate --all
skill-maintain quality
```

Option A is simpler for one-off checks. Option B gives the repo its own `skill-maintain` command and lets CI run it without fb-claude-skills present.

**Full end-to-end scenario:**

```bash
# 1. sync upstream knowledge in fb-claude-skills first
skill-maintain sources       # pull tracked repos
skill-maintain upstream      # check Anthropic docs for changes

# 2. review current state
skill-maintain quality       # see your own repo's health

# 3. apply to target repo (option A shown)
skill-maintain init --dir ~/claude/other-repo
skill-maintain quality --dir ~/claude/other-repo

# 4. fix what the report flags
#    - add metadata.last_verified to SKILL.md frontmatter
#    - add WHAT verb + WHEN trigger to descriptions
#    - trim skills over budget (move content to references/)
```

## subcommand details

### validate

Validates one or all skills against the Agent Skills spec plus best-practice checks.

For each skill:
- Runs `skills_ref.validator.validate()` (spec compliance: name format, required fields, allowed fields)
- Checks line count (max 500), word count (max 5000), description quality (WHAT + WHEN pattern), angle brackets in description, unlinked reference files

Reports errors (spec violations) and warnings (best practice issues) separately.

```bash
skill-maintain validate --all
skill-maintain validate --skill tui-design --verbose
```

### quality

Unified report: validation + token budget + staleness + description quality, one row per skill.

For each skill:
- **Validation:** `skills_ref.validator.validate()`
- **Token budget:** chars / 4 estimate. Warn >4000, critical >8000
- **Staleness:** days since `metadata.last_verified`. >30 days = stale
- **Description quality:** checks for WHAT verb ("handles", "generates", etc.) and WHEN trigger ("use when", "when user", etc.)

Exits 1 if any skill fails validation.

```bash
skill-maintain quality
skill-maintain quality --no-log   # skip audit log entry
```

### freshness

Checks `metadata.last_verified` dates across all skills.

```bash
skill-maintain freshness                    # show all
skill-maintain freshness --quiet            # only show stale
skill-maintain freshness --threshold 14     # stricter threshold (days)
skill-maintain freshness --skill tui-design # check one skill
```

### measure

Detailed token budget measurement with per-file breakdown. Classifies files by type (skill_md, reference, script, agent, etc.) and estimates tokens as chars / 4.

```bash
skill-maintain measure
skill-maintain measure --skill tui-design
skill-maintain measure --output report.md   # write to file
```

### test

Red/green test suite with three categories: skills, plugins, repo hygiene.

```bash
skill-maintain test
skill-maintain test --category skills
skill-maintain test --category repo
skill-maintain test --verbose
```

### upstream

Fetches `https://code.claude.com/docs/llms-full.txt`, splits by `Source: <url>` delimiters into per-page sections, hashes each watched page, and reports changes.

Watched pages are configured in `.skill-maintainer/config.json` under `upstream_urls`. Defaults cover: skills, plugins, plugins-reference, discover-plugins, plugin-marketplaces, hooks-guide, hooks, sub-agents, memory.

```bash
skill-maintain upstream
skill-maintain upstream --no-save   # check without persisting hashes
skill-maintain upstream --no-log    # skip audit log entry
```

### sources

Pulls tracked git repos and detects what changed since the last run. Tracked repos are configured in `.skill-maintainer/config.json` under `tracked_repos`.

For each repo:
1. Loads stored SHA from `.skill-maintainer/state/upstream_hashes.json` under `"local_repos"`
2. Records current HEAD SHA
3. Runs `git pull --ff-only`
4. Compares post-pull SHA to stored SHA: `NEW`, `CHANGED` (with commit log), or `UP_TO_DATE`
5. Saves updated SHAs and appends a `source_pull` event to `changes.jsonl`

```bash
skill-maintain sources
skill-maintain sources --no-pull    # check SHAs without pulling
skill-maintain sources --no-save    # don't persist updated SHAs
```

### log

Queries the append-only audit log at `.skill-maintainer/state/changes.jsonl`.

```bash
skill-maintain log --tail 5
skill-maintain log --days 7
skill-maintain log --type upstream_check
```

## configuration

Per-repo config lives at `.skill-maintainer/config.json`. Created by `skill-maintain init`.

```json
{
  "upstream_urls": [
    "https://code.claude.com/docs/en/skills",
    "https://code.claude.com/docs/en/plugins"
  ],
  "tracked_repos": [
    "coderef/agentskills",
    "coderef/mcp/modelcontextprotocol"
  ],
  "llms_full_url": "https://code.claude.com/docs/llms-full.txt"
}
```

To add a tracked source, add an entry to `tracked_repos` and clone or symlink the repo at the specified path.

To add a watched upstream page, add its URL to `upstream_urls`. The page must appear in `llms-full.txt`.

Best practices doc: `.skill-maintainer/best_practices.md` (proposed edits from `/maintain`, reviewed manually before applying).

## state files

Both state files live at `.skill-maintainer/state/`. They are gitignored and auto-generated.

### upstream_hashes.json

```json
{
  "https://code.claude.com/docs/en/skills": "7fdcca7ff9e64a8c",
  "https://code.claude.com/docs/en/plugins": "6f472f023ede34f8",
  "local_repos": {
    "coderef/agentskills": "abc123def456...",
    "coderef/mcp/modelcontextprotocol": "789012ghi345..."
  }
}
```

Top-level keys are URLs (written by `upstream`). The `"local_repos"` key holds git SHAs (written by `sources`). The two subcommands share the file but use different key namespaces.

### changes.jsonl

Append-only audit log. One JSON object per line. Three event types:

```json
{"type": "source_pull", "date": "2026-03-06", "repos_checked": 10, "repos_changed": 3, "changes": [...]}
{"type": "upstream_check", "date": "2026-03-06", "changed_pages": [...], "total_changed": 2}
{"type": "quality_report", "date": "2026-03-06", "skills": 9, "valid": 9, "over_budget": 5, "stale": 0}
```

### metadata.last_verified (in SKILL.md files)

Each SKILL.md has this in frontmatter:

```yaml
metadata:
  last_verified: 2026-03-06
```

Update it when you review or modify a skill. `freshness` and `quality` both read this field.
