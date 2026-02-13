last updated: 2026-02-13

# api reference

Function-level documentation for the skill-maintainer Python scripts. All scripts are run via `uv run python skill-maintainer/scripts/<script>.py`.

## docs_monitor.py

CDC-style change detection for documentation sources. Three-layer pipeline: DETECT (HEAD request) -> IDENTIFY (fetch + hash pages) -> CLASSIFY (keyword heuristic).

### detect_change

```python
def detect_change(
    bundle_url: str,
    stored_watermark: dict,
    timeout: float = 10.0,
) -> tuple[bool, dict]
```

Layer 1: HEAD request to check Last-Modified / ETag headers.

**Parameters:**
- `bundle_url` -- URL to llms-full.txt
- `stored_watermark` -- `{last_modified, etag, last_checked}` from state
- `timeout` -- HTTP timeout in seconds (default: 10.0)

**Returns:** `(changed, new_watermark)` -- changed is True if headers differ or server doesn't support conditional headers.

**Side effects:** None. Pure network check.

**Error behavior:** Returns `(True, stored_watermark)` on any exception, causing fallthrough to identify layer.

### identify_changes

```python
def identify_changes(
    bundle_url: str,
    watched_pages: list[str],
    stored_pages: dict,
    timeout: float = 30.0,
) -> tuple[list[dict], dict]
```

Layer 2: Fetch the bundle, split into pages, compare hashes.

**Parameters:**
- `bundle_url` -- URL to llms-full.txt
- `watched_pages` -- list of page URLs to monitor (empty = all pages)
- `stored_pages` -- `{url: {hash, content_preview, last_changed}}` from state
- `timeout` -- HTTP timeout in seconds (default: 30.0)

**Returns:** `(changes, new_pages_state)` where changes is a list of `{url, old_hash, new_hash, old_content, new_content}` dicts.

**Side effects:** None. Pure computation on fetched data.

### classify_change

```python
def classify_change(old_content: str, new_content: str) -> str
```

Layer 3: Keyword heuristic on diff text.

**Parameters:**
- `old_content` -- previous page content (empty string for initial capture)
- `new_content` -- current page content

**Returns:** One of `"BREAKING"`, `"ADDITIVE"`, `"COSMETIC"`.

**Classification logic:**
- Empty old_content -> `ADDITIVE` (initial capture)
- Diff contains breaking keywords (removed, deprecated, must now, etc.) -> `BREAKING`
- Diff contains additive keywords (new, added, now supports, etc.) -> `ADDITIVE`
- Otherwise -> `COSMETIC`

### check_local_file

```python
def check_local_file(file_path: Path, stored_hash: str) -> dict | None
```

Check a local file (e.g., PDF) for changes via SHA-256 hash.

**Returns:** Change dict `{url, old_hash, new_hash, classification, summary}` or None if unchanged.

### check_source

```python
def check_source(
    source_name: str,
    source_config: dict,
    state: dict,
) -> list[dict]
```

Run the full CDC pipeline for one docs source.

**Parameters:**
- `source_name` -- key from config.yaml sources section
- `source_config` -- the source's config dict (`{llms_full_url, pages, hash_file}`)
- `state` -- mutable state dict (modified in place)

**Returns:** List of classified change dicts `{source, url, classification, old_hash, new_hash, summary}`.

**Side effects:** Mutates `state["docs"][source_name]` with updated watermarks and page hashes.

### generate_report

```python
def generate_report(all_changes: list[dict]) -> str
```

Generate markdown report from change dicts, grouped by classification.

### CLI

```
uv run python skill-maintainer/scripts/docs_monitor.py [OPTIONS]

  --config PATH    Path to config.yaml (default: skill-maintainer/config.yaml)
  --state PATH     Path to state.json (default: skill-maintainer/state/state.json)
  --source NAME    Check only this source
  --output PATH    Write report to file instead of stdout
```

---

## source_monitor.py

Git-based upstream code change detection. Shallow-clones repos, checks commits, extracts Python APIs via AST, detects deprecations.

### clone_repo

```python
def clone_repo(url: str, dest: Path, since: str) -> bool
```

Shallow bare clone scoped to the time window.

**Parameters:**
- `url` -- git repository URL
- `dest` -- destination path for bare clone
- `since` -- git date string (e.g., "30days", "2024-01-15")

**Returns:** True if clone succeeded.

**Timeout:** 120 seconds.

### get_recent_commits

```python
def get_recent_commits(repo_path: Path, since: str) -> list[dict]
```

Get recent commits with metadata.

**Returns:** List of `{hash (12 chars), subject, author, date}` dicts. No merge commits.

### get_changed_files

```python
def get_changed_files(repo_path: Path, since: str) -> list[str]
```

Get deduplicated, sorted list of files changed since the given date.

### extract_public_api

```python
def extract_public_api(file_path: Path) -> list[str]
```

Extract public function and class names from a Python file using AST. Only includes names not starting with `_`.

**Returns:** List of strings like `"def validate(path)"`, `"class Validator [check, run]"`.

### check_deprecations

```python
def check_deprecations(commits: list[dict]) -> list[str]
```

Scan commit messages for deprecation keywords: deprecat, removed, breaking, rename, replace, migrate, backward compat.

**Returns:** List of formatted strings `"  - [hash] subject"`.

### check_source

```python
def check_source(
    source_name: str,
    source_config: dict,
    state: dict,
    since: str,
) -> dict
```

Full pipeline for one source repo. Clones to temp dir, analyzes, cleans up.

**Returns:** `{source, repo, commits_count, changed_files_count, watched_hits, deprecations, commits, classification}`.

**Side effects:** Mutates `state["sources"][source_name]`. Creates and removes temp directory.

**Classification:**
- deprecations found -> `BREAKING`
- watched files changed -> `ADDITIVE`
- any commits -> `COSMETIC`
- no commits -> `NONE`

### CLI

```
uv run python skill-maintainer/scripts/source_monitor.py [OPTIONS]

  --config PATH    Path to config.yaml
  --state PATH     Path to state.json
  --source NAME    Check only this source
  --since RANGE    Time range for git log (default: 30days)
  --output PATH    Write report to file
```

---

## check_freshness.py

Lightweight staleness check (<100ms). Reads state.json timestamps, warns if stale. Never blocks skill invocation (always exits 0).

### parse_threshold

```python
def parse_threshold(threshold_str: str) -> timedelta
```

Parse threshold strings: `"7d"` -> 7 days, `"24h"` -> 24 hours, `"7"` -> 7 days.

### get_last_checked

```python
def get_last_checked(state: dict, source_name: str) -> str | None
```

Get the most recent check timestamp for a source. Checks both docs state (watermark + page timestamps) and sources state (git-based). Returns the newest timestamp found, or None.

### check_skill_freshness

```python
def check_skill_freshness(
    skill_name: str,
    config: dict,
    state: dict,
    threshold: timedelta,
) -> dict
```

Check freshness of a single skill across all its sources.

**Returns:** `{name, is_stale, last_checked, staleness_days, sources, message}` where sources is a list of per-source status dicts.

### CLI

```
uv run python skill-maintainer/scripts/check_freshness.py [SKILL] [OPTIONS]

  SKILL              Skill name (default: all tracked skills)
  --config PATH      Path to config.yaml
  --state PATH       Path to state.json
  --threshold RANGE  Staleness threshold (default: 7d)
  -q, --quiet        Only output warnings for stale skills
```

**Exit code:** Always 0 (warning tool, not a gate).

---

## apply_updates.py

Apply detected changes to skills. Supports three modes: report-only, apply-local (default), create-pr.

### validate_skill

```python
def validate_skill(skill_path: Path) -> tuple[bool, list[str]]
```

Run `uv run skills-ref validate` on a skill directory.

**Returns:** `(is_valid, errors)`.

**Timeout:** 30 seconds.

### backup_skill / restore_from_backup / cleanup_backup

```python
def backup_skill(skill_path: Path) -> Path
def restore_from_backup(skill_path: Path, backup_path: Path) -> None
def cleanup_backup(backup_path: Path) -> None
```

Backup creates `{skill_name}.backup` sibling directory. Restore replaces skill from backup and removes backup. Cleanup removes backup.

### get_changes_for_skill

```python
def get_changes_for_skill(
    skill_name: str,
    config: dict,
    state: dict,
) -> list[dict]
```

Extract pending changes relevant to a specific skill by checking its configured sources against docs and source state.

**Returns:** List of change dicts with `type` ("docs" or "source") and source-specific fields.

### generate_update_context

```python
def generate_update_context(
    skill_name: str,
    skill_path: Path,
    changes: list[dict],
) -> str
```

Generate structured markdown prompt for Claude-assisted skill updates. Includes current SKILL.md content and detected changes.

### apply_report_only / apply_local

```python
def apply_report_only(skill_name, skill_path, changes) -> str
def apply_local(skill_name, skill_path, changes, state, state_path) -> str
```

- `report_only` -- generates report with validation status and update context, no file changes
- `apply_local` -- creates backup, generates context, records attempt in state. Does NOT auto-edit files.

**Side effects (apply_local):** Creates backup directory. Mutates `state["updates"][skill_name]`.

### CLI

```
uv run python skill-maintainer/scripts/apply_updates.py --skill NAME [OPTIONS]

  --skill NAME       Required. Skill name from config.yaml
  --mode MODE        report-only | apply-local | create-pr (default: apply-local)
  --config PATH      Path to config.yaml
  --state PATH       Path to state.json
  --output PATH      Write report to file
```

---

## update_report.py

Unified report combining docs and source changes, mapped to affected skills.

### find_affected_skills

```python
def find_affected_skills(
    config: dict,
    changed_sources: list[str],
) -> dict[str, list[str]]
```

Map changed source names to skills that depend on them.

**Returns:** `{skill_name: [source_names]}`.

### generate_unified_report

```python
def generate_unified_report(config: dict, state: dict) -> str
```

Generate markdown report with: affected skills, docs changes, source changes, suggested actions.

### CLI

```
uv run python skill-maintainer/scripts/update_report.py [OPTIONS]

  --config PATH    Path to config.yaml
  --state PATH     Path to state.json
  --output PATH    Write report to file
```

---

## validate_skill.py

Validates skills against Agent Skills spec and best practices. Wraps skills-ref validator and adds additional checks.

### check_best_practices

```python
def check_best_practices(skill_path: Path) -> list[str]
```

Additional checks beyond skills-ref:
- SKILL.md line count (max 500) and word count (max 5000)
- Description quality: checks for WHAT verbs and WHEN triggers
- Angle brackets in description (forbidden in frontmatter)
- README.md in skill folder (not recommended)
- Reference files linked from SKILL.md body

**Returns:** List of warning strings.

### validate_single

```python
def validate_single(
    skill_path: Path,
    verbose: bool = False,
) -> tuple[bool, list[str], list[str]]
```

Run both skills-ref validation and best practice checks.

**Returns:** `(is_valid, errors, warnings)`. `is_valid` is based only on skills-ref errors, not warnings.

### CLI

```
uv run python skill-maintainer/scripts/validate_skill.py [PATH] [OPTIONS]

  PATH               Path to skill directory
  --all              Validate all skills in config.yaml
  --config PATH      Path to config.yaml
  -v, --verbose      Show detailed error and warning output
```

**Exit code:** 0 if valid (or --all and all valid), 1 if any validation errors.

---

## shared patterns

### state helpers

All scripts share identical `load_config`, `load_state`, `save_state` functions:

```python
def load_config(config_path: Path) -> dict    # yaml.safe_load
def load_state(state_path: Path) -> dict      # orjson.loads, returns {} for empty/missing
def save_state(state_path: Path, state: dict) # orjson.dumps with OPT_INDENT_2
```

### defaults

All scripts use consistent defaults:
- Config: `skill-maintainer/config.yaml`
- State: `skill-maintainer/state/state.json`

### timestamps

All timestamps are UTC ISO 8601 format: `2026-02-13T19:23:53.534257+00:00`.
