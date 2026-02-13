---
name: skill-maintainer
description: Monitors upstream documentation, specifications, and source code for changes that affect Claude Code skills. Use when user says "check for skill updates", "are my skills current", "update skills", or wants to monitor Anthropic docs and Agent Skills spec for changes. Provides commands to check, update, and track skill freshness.
metadata:
  author: Fred Bliss
  version: 0.1.0
---

# Skill Maintainer

Detect when best practices, source code, or data sources change, and produce updated skill content or a PR for review. Validates all updates against the Agent Skills spec before applying.

## Commands

| Command | Purpose |
|---------|---------|
| `/skill-maintainer check` | Run all monitors, produce change report |
| `/skill-maintainer update <skill-name>` | Apply detected changes to a specific skill |
| `/skill-maintainer status` | Show freshness status of all tracked skills |
| `/skill-maintainer add-source <url-or-repo>` | Add a new monitored source |

---

## /skill-maintainer check

Run all configured monitors and produce a structured change report.

### Usage

```
/skill-maintainer check
/skill-maintainer check --source anthropic-skills-docs
/skill-maintainer check --since 7d
```

### Process

1. Read `config.yaml` for configured sources and skills
2. Run `docs_monitor.py` against all docs-type sources
3. Run `source_monitor.py` against all source-type repos
4. Produce a unified change report with:
   - What changed (diffs, new content, removed content)
   - Impact classification (breaking / additive / cosmetic)
   - Which skills are affected
   - Suggested actions for each affected skill
5. Write report to stdout and optionally to `state/last_report.md`
6. Update `state/state.json` with check timestamps and content hashes

### Running the monitors

```bash
uv run python skill-maintainer/scripts/docs_monitor.py
uv run python skill-maintainer/scripts/source_monitor.py
uv run python skill-maintainer/scripts/update_report.py
```

---

## /skill-maintainer update

Apply detected changes to a specific skill.

### Usage

```
/skill-maintainer update plugin-toolkit
/skill-maintainer update plugin-toolkit --mode report-only
/skill-maintainer update skill-maintainer --mode apply-local
```

### Update modes

| Mode | Behavior |
|------|----------|
| `report-only` | Produce report only, no file changes |
| `apply-local` (default) | Apply changes locally, validate, user reviews diff |
| `create-pr` | Apply, commit to branch, create PR (for CI) |

### Process

1. Read the latest change report from state
2. Classify changes by type (frontmatter, best practice, API/spec, breaking)
3. For automated patches: apply directly, validate with skills-ref
4. For complex changes: generate update context for Claude-assisted editing
5. Always validate after any update: `uv run skills-ref validate <skill-path>`
6. Never auto-commit; user reviews diff and commits manually

### Running the update pipeline

```bash
uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit
uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit --mode report-only
```

---

## /skill-maintainer status

Show freshness status of all tracked skills.

### Usage

```
/skill-maintainer status
/skill-maintainer status --skill plugin-toolkit
```

### Output

Reads `state/state.json` and shows:
- Last check time for each source
- Last update time for each skill
- Staleness warning if any skill exceeds threshold (default 7 days)
- Summary of pending changes not yet applied

### Running the freshness check

```bash
uv run python skill-maintainer/scripts/check_freshness.py
uv run python skill-maintainer/scripts/check_freshness.py plugin-toolkit
```

---

## /skill-maintainer add-source

Add a new monitored source to config.yaml.

### Usage

```
/skill-maintainer add-source https://code.claude.com/docs/en/hooks-guide
/skill-maintainer add-source https://github.com/org/repo --watch "src/main.py,docs/api.md"
```

### Process

1. Determine source type (docs URL or git repo)
2. Add entry to `config.yaml` with appropriate settings
3. Run initial check to capture baseline hash/state
4. Report what was added and initial state captured

---

## Supporting files

- **[config.yaml](config.yaml)** - Source registry and skill tracking configuration
- **[references/best_practices.md](references/best_practices.md)** - Machine-parseable best practices from official docs
- **[references/monitored_sources.md](references/monitored_sources.md)** - What we monitor and why
- **[references/update_patterns.md](references/update_patterns.md)** - Patterns for applying different change types
- **State directory** (`state/`) - Versioned state: timestamps, content hashes, versions
