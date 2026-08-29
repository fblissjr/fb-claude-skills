last updated: 2026-08-03

# skill-maintainer (CLI package)

Installable Python package providing a `skill-maintain` CLI for monitoring, validating, and maintaining Claude Code skill repos. Runs as project-scoped tooling within fb-claude-skills and is git-installable for use in other repos.

> **Primary interface:** For interactive use in Claude Code, install the `skill-maintainer` plugin instead (`/plugin install skill-maintainer@fb-claude-skills`). The plugin embeds the same knowledge and works without Python package installation. This CLI package is best suited for CI pipelines and headless automation.

## installation

### within fb-claude-skills (already available)

After `uv sync --all-packages`, the `skill-maintain` command is available in the workspace venv. No additional setup needed.

### in another repo (git install)

```bash
uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer
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
 by glob)                   provenance ─────────────────┤──► CLI reports
                            measure ────────────────────┤    (tables, pass/fail,
upstream docs               upstream ──────────────────►┤     exit codes for CI)
(llms-full.txt via HTTP)    sources ───────────────────►┤
                            test ───────────────────────┘
tracked git repos                                              .skill-maintainer/
(coderef/ or configured     log ──────────────────────────►   state/upstream_hashes.json
 paths)                                                        state/changes.jsonl
```

The `/maintain` slash command orchestrates the pipeline in sequence: `sources → upstream → quality → review`.

Skill and plugin discovery skip `_deprecated` directories along with the usual `__pycache__`, `.backup`, `node_modules`, `.git`, `coderef`, `.venv`, and `internal`. `_deprecated` holds units kept for reference but no longer published; excluding it keeps them out of quality reports, token budgets, and version checks.

## what runs automatically

### pre-commit hook (git)

**When:** every `git commit` that touches a staged `SKILL.md`, `.claude-plugin/marketplace.json`, or a plugin's version-bearing files.

**What it does:**
1. `git diff --cached --name-only --diff-filter=ACM` lists staged files
2. For each staged SKILL.md, runs `uv run skill-maintain validate <skill-dir>`; blocks the commit on any failure
3. If `.claude-plugin/marketplace.json` is staged and the `claude` CLI is installed, runs `claude plugin validate . --strict` and blocks the commit if it fails. Skipped entirely when `claude` isn't on PATH, so the hook still works on a machine without Claude Code installed.
4. Checks version consistency across `plugin.json`, `marketplace.json`, and `pyproject.toml` for every plugin root touched by the commit, and warns (without blocking) if plugin content changed but no version-bearing file was staged

**What it checks:** the Claude Code skill schema (a superset of the [Agent Skills spec](https://agentskills.io)) -- required frontmatter fields (name, description), naming conventions (kebab-case, no consecutive hyphens), and an allowlist that accepts Claude Code fields (`disable-model-invocation`, `argument-hint`, `model`, ...) while still rejecting unknown ones -- plus marketplace-manifest strictness and plugin version alignment. `skill-maintain validate --strict` additionally flags Claude Code-only fields for cross-vendor portability.

**Where:** `tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample`, installed as `.git/hooks/pre-commit`.

**Side effects:** none. Read-only checks. Either the commit proceeds or it doesn't.

That's it. Nothing else runs unless you invoke it.

## CLI reference

All subcommands accept `--dir <path>` to target a skill repo other than the current directory.

| Command | What it does |
|---------|-------------|
| `init` | Create `.skill-maintainer/config.json` in the target repo |
| `validate` | Validate skills against Agent Skills spec + best practices |
| `quality` | Unified report: validation + token budget + description quality |
| `measure` | Token budget measurement with per-file breakdown |
| `test` | Red/green test suite (skills, plugins, repo hygiene) |
| `upstream` | Fetch Claude Code docs via llms-full.txt; snapshots each watched page to `state/pages/<slug>.md` and reports line/char deltas across runs |
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
skill-maintain quality --dir /path/to/other-skill-repo

# check a single skill's token budget
skill-maintain measure --skill path-privacy

# see last 5 audit log entries
skill-maintain log --tail 5
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
/skill-maintainer:maintain
```

Pulls upstream sources, checks for doc changes, runs the quality report, and proposes updates to `.skill-maintainer/best_practices.md`. Run this when you want to sync with upstream and review the maintenance checklist. Or run the phases individually:

```bash
skill-maintain sources   # phase 1: pull tracked repos
skill-maintain upstream  # phase 2: check upstream docs
skill-maintain quality   # phase 3: validate all skills
# phase 4: Claude reviews results and proposes best_practices.md edits
```

Phase 4 never auto-writes. Claude shows proposed changes and waits for approval.

**Where:** `/skill-maintainer:maintain` (plugin skill, replaces legacy `.claude/commands/maintain.md`)

### applying best practices to another repo

Two options depending on whether you want a permanent install or a one-off check.

**Option A: `--dir` (no install needed)**

Run from within fb-claude-skills, targeting the other repo:

```bash
# initialize config in the target repo
skill-maintain init --dir /path/to/other-skill-repo

# validate and check quality
skill-maintain validate --all --dir /path/to/other-skill-repo
skill-maintain quality --dir /path/to/other-skill-repo
skill-maintain measure --dir /path/to/other-skill-repo
```

**Option B: git-install (standalone)**

Add skill-maintainer as a dependency in the target repo:

```bash
cd /path/to/other-repo
uv add "skill-maintainer @ git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer"
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
skill-maintain init --dir /path/to/other-repo
skill-maintain quality --dir /path/to/other-repo

# 4. fix what the report flags
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
skill-maintain validate --skill path-privacy --verbose
```

### quality

Unified report: validation + token budget + description quality, one row per skill.

For each skill:
- **Validation:** `skills_ref.validator.validate()`
- **Token budget:** chars / 4 estimate. Warn >4000, critical >8000
- **Description quality:** checks for WHAT verb ("handles", "generates", etc.) and WHEN trigger ("use when", "when user", etc.)

Exits 1 if any skill fails validation.

```bash
skill-maintain quality
skill-maintain quality --no-log   # skip audit log entry
```

### measure

Detailed token budget measurement with per-file breakdown. Classifies files by type (skill_md, reference, script, agent, etc.) and estimates tokens as chars / 4.

```bash
skill-maintain measure
skill-maintain measure --skill path-privacy
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

Two repo-hygiene checks guard version drift from opposite sides. It's worth knowing which one is talking when a run goes red.

**Do the manifests agree with each other?** (`check_version_alignment`) walks every entry in `.claude-plugin/marketplace.json` against the `plugin.json` it points to, in both directions: a marketplace entry whose plugin doesn't exist on disk, and a plugin on disk that isn't listed in the marketplace. It also compares a `pyproject.toml` version where the unit has one. This is repo-wide, unlike the pre-commit hook's version check, which only inspects plugins touched by the current commit -- a marketplace entry can otherwise drift for releases at a time with nothing noticing. Returns no findings when the repo has no `marketplace.json`, since that's a legitimate shape for a plugin repo.

**Do the manifests agree with the changelog?** (`check_changelog_claims`) reads the top section of `CHANGELOG.md`, pulls out every `` `name` 0.1.0 → 0.2.0 `` claim, and checks the target against the versions that name actually carries. A failure looks like:

```
FAIL  repo/postmortem   changelog claims (changelog claims postmortem 0.6.0 but manifest reads 0.5.0)
```

That means you wrote the changelog entry and forgot the manifest bump, or bumped and mistyped one of them. The check doesn't care which direction is wrong -- fix whichever it is. This catches what the first check structurally can't: manifests that agree perfectly with each other and disagree with what you told your readers shipped. Both halves have real consumers, since `marketplace update` resolves the manifest while a person reads the changelog to know a fix landed.

Only the **top section** is read, on purpose. Older entries describe the state at their own release and are supposed to disagree with today's manifests; sweeping them would light up every historical entry and turn the check into a wall people mute. Two consequences worth knowing:

- A name can hold two versions at once and both are accepted. In this repo `skill-maintainer` is a plugin and a CLI that version independently by design, so a claim matching either passes rather than the check guessing which you meant.
- A claim that stays unsatisfied until the *next* section lands escapes permanently. The check guards the window, not the history -- so fix a red before writing the next section.

Names the repo doesn't version -- retired units, upstream dependencies -- are reported rather than failed, and the count rides along with the pass:

```
PASS  repo   changelog claims (3/4 top-section claims resolved to a versioned unit; not versioned here: env-forge)
```

Read that count. A green that resolved 0 of 4 claims checked nothing, and looks identical to one that checked everything.

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

## ad-hoc queries (`queries/`)

Some questions get asked rarely enough that a subcommand would cost more than it returns: a flag to document and keep working, and a `duckdb` dependency on a tool that otherwise has none. Those live as plain `.sql` files in `queries/` and get run by hand.

`upstream_churn.sql` answers **how fast does each tracked upstream page actually move?** from `.skill-maintainer/state/changes.jsonl`. It had a consumer in the retired `review_interval_days` tiers; with those gone the query is exploratory, and worth running before anyone proposes a new time-based gate.

Run it from the repo root:

```bash
uv run --with duckdb python -c "import duckdb; print(duckdb.sql(open('tools/skill-maintainer/queries/upstream_churn.sql').read()))"
```

DuckDB reads the JSONL in place, so there's no import step and no second copy of the log to keep in sync. Drop `--with duckdb` if it's already in the environment.

Two cautions the query's own header repeats: `changes` counts only the checks that *found* a change, so the interval it implies is an upper bound on quiet periods rather than a release cadence; and the character deltas aren't comparable across the whole window, because the log changed shape mid-history and only later entries carry them. Rank on `changes`.

If one of these starts getting run every maintenance pass, that's the evidence for promoting it to a subcommand. Until then it stays a file.

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

### metadata.last_verified (removed from SKILL.md)

Retired 2026-08-29 with the calendar review rule it served, along with
`metadata.review_interval_days` and `metadata.freshness`. The `freshness`
subcommand, the staleness arm of `test`, and the freshness column in `quality`
went with them. Do not re-add the fields; nothing reads them.

The reasoning is recorded in `docs/internals/maintenance.md`. In short: a
calendar window is a proxy for source movement and a lazy one wherever movement
is observable, and every source this repo tracks is either in-repo code, whose
drift the version cascade surfaces, or an upstream page whose hash is already
snapshotted. Both triggers are change-based, so the elapsed-time proxy was
carrying no signal the repo did not already have.

Unrelated despite the shared name: the `last_verified` inside
`best_practices.md`'s per-section provenance comments. That is hash-triggered,
still live, and read by the `best_practices provenance` arm of `test`.

### metadata.version (removed from SKILL.md)

SKILL.md frontmatter no longer carries a `version` field. `plugin.json` is the sole version source for a plugin; `/skill-maintainer:sync-versions` no longer touches SKILL.md. Do not add `version:` back to a skill's frontmatter -- it was a second source of truth for the same number `plugin.json` already tracks.
