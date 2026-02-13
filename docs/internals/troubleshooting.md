last updated: 2026-02-13

# troubleshooting

Common issues and recovery procedures for the skill-maintainer system.

## docs_monitor issues

### "fetch failed" error in report

**Symptom:** Report shows `classification: ERROR` with `summary: fetch failed: <exception>`.

**Cause:** The llms-full.txt URL is unreachable or returned a non-200 status.

**Fix:**
1. Check network connectivity
2. Verify the URL in config.yaml is correct: `uv run python -c "import httpx; r = httpx.get('<url>'); print(r.status_code)"`
3. If the URL has moved, update `llms_full_url` in config.yaml

### detect layer always returns "changed"

**Symptom:** Every run reports changes even when nothing actually changed.

**Cause:** The server doesn't return `Last-Modified` or `ETag` headers. The detect layer falls through to identify.

**Impact:** Minor performance hit (always fetches the full bundle) but functionally correct -- the identify layer hashes pages and will report no changes if content is unchanged.

### pages not being tracked

**Symptom:** `check_source` returns no changes but you know a page changed.

**Cause:** The page URL in config.yaml `pages` list doesn't match the `Source:` URL in llms-full.txt.

**Fix:** Check the exact URL format. Run: `uv run python -c "import httpx; text=httpx.get('<llms_full_url>').text; [print(l) for l in text.split('\n') if l.startswith('Source:')]"` to see available page URLs.

### state.json has stale content_preview

**Symptom:** content_preview in state.json doesn't match current page content.

**Cause:** Normal -- content_preview is updated when the hash changes. If the hash matches, the preview is preserved from the last change.

**Not a problem:** The preview is only used for diff display. The hash is the authoritative comparison.

---

## source_monitor issues

### "clone failed" / "skipped"

**Symptom:** Source check reports 0 commits and "skipped (no recent commits or clone failed)".

**Causes:**
1. No commits in the time window (normal, not an error)
2. Git clone failed (network, auth, bad URL)
3. Timeout exceeded (120 seconds for clone)

**Fix:**
- Check the repo URL is accessible: `git ls-remote <url> HEAD`
- Try a wider time window: `--since 90days`
- For private repos, ensure git credentials are configured

### AST extraction returns empty API

**Symptom:** `watched_hits` shows a Python file with empty `api` list.

**Cause:** `extract_public_api` only extracts top-level public functions and classes (names not starting with `_`). Nested definitions, module-level constants, and type aliases are not captured.

**Not a problem:** API extraction is informational only, used for report enrichment.

---

## check_freshness issues

### "has never been checked"

**Symptom:** `skill-maintainer: <skill> has never been checked`.

**Cause:** No timestamps found in state.json for any of the skill's configured sources. Normal on first setup.

**Fix:** Run the monitors to capture initial state:
```bash
uv run python skill-maintainer/scripts/docs_monitor.py
uv run python skill-maintainer/scripts/source_monitor.py
```

### all skills show stale after state.json reset

**Symptom:** All skills report as stale after state.json was cleared or reformatted.

**Cause:** State.json reset loses all timestamps. Expected behavior.

**Fix:** Run both monitors to recapture state. All skills will show as fresh after.

---

## apply_updates issues

### "skill not found in config.yaml"

**Symptom:** `Error: skill '<name>' not found in config.yaml`.

**Fix:** Check the skill name matches a key under `skills:` in config.yaml. Names are case-sensitive.

### "skill path does not exist"

**Symptom:** `Error: skill path does not exist: <path>`.

**Fix:** The `path` value in config.yaml points to a directory that doesn't exist. Check for typos and ensure the skill directory has been created.

### backup directory persists

**Symptom:** A `.backup` directory exists next to a skill directory.

**Cause:** An `apply-local` run created the backup but it was never cleaned up.

**Fix:** If you're done reviewing, remove it: `rm -rf <path>.backup`. The backup is a complete copy of the skill directory at the time of the update attempt.

### validation fails after update

**Symptom:** `uv run skills-ref validate <path>` fails after making changes.

**Common causes:**
- SKILL.md frontmatter syntax error (check YAML formatting)
- `name` field doesn't match directory name
- `description` exceeds 1024 characters
- Missing required frontmatter fields

**Fix:** Run with verbose output to see specific errors:
```bash
uv run python skill-maintainer/scripts/validate_skill.py <path> -v
```

---

## validate_skill issues

### "SKILL.md not found"

**Symptom:** Best practices check reports "SKILL.md not found".

**Fix:** Ensure the path points to a directory containing a `SKILL.md` file (not the file itself). The validator expects a directory path.

### warnings vs errors

**Distinction:**
- **Errors** come from skills-ref and indicate spec violations. These cause validation failure (exit code 1).
- **Warnings** come from best practice checks and are informational. They do not cause validation failure.

Common warnings:
- "SKILL.md has N lines (recommended max: 500)" -- consider moving details to references/
- "Description may be missing WHAT/WHEN" -- improve description with action verbs and trigger conditions
- "Reference file not linked from SKILL.md" -- add a reference to the file in the skill body

---

## state.json corruption

### symptoms

- Scripts crash with `orjson.JSONDecodeError`
- Unexpected behavior (always reporting changes, never reporting changes)
- Missing sections in state

### recovery

1. **Check the file:** `uv run python -c "import orjson; print(orjson.loads(open('skill-maintainer/state/state.json','rb').read()))"`
2. **Reset entirely:** Replace with `{}` and rerun both monitors
3. **Partial recovery:** Edit the file to fix JSON syntax, preserving what you can

State.json is in the git repo, so you can also restore from a previous commit:
```bash
git checkout HEAD -- skill-maintainer/state/state.json
```

---

## general tips

### running from the right directory

All scripts expect to be run from the repo root (`fb-claude-skills/`). Paths in config.yaml and defaults are relative to this.

### checking what changed since last run

```bash
# Docs changes
uv run python skill-maintainer/scripts/docs_monitor.py

# Source repo changes
uv run python skill-maintainer/scripts/source_monitor.py

# Combined report mapped to skills
uv run python skill-maintainer/scripts/update_report.py

# Staleness overview
uv run python skill-maintainer/scripts/check_freshness.py
```

### quick validation of all skills

```bash
# Spec validation only (fast)
uv run skills-ref validate mcp-apps/skills/create-mcp-app/SKILL.md

# Spec + best practices (includes warnings)
uv run python skill-maintainer/scripts/validate_skill.py --all -v
```
