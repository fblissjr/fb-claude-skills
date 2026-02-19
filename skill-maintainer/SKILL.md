---
name: skill-maintainer
description: Monitors upstream documentation, specifications, and source code for changes that affect Claude Code skills. Use when user says "check for skill updates", "are my skills current", "update skills", "token budget", "skill history", or wants to monitor Anthropic docs and Agent Skills spec for changes. Provides commands to check, update, track freshness, measure budgets, and query change history.
metadata:
  author: Fred Bliss
  version: 0.2.0
allowed-tools: "Bash(uv run *)"
---

# Skill Maintainer

Detect when best practices, source code, or data sources change, and produce updated skill content or a PR for review. Validates all updates against the Agent Skills spec before applying. All state is stored in DuckDB for temporal queryability and audit trails.

## Commands

| Command | Purpose |
|---------|---------|
| `/skill-maintainer check` | Run all monitors, produce change report |
| `/skill-maintainer update <skill-name>` | Apply detected changes to a specific skill |
| `/skill-maintainer status` | Show freshness status of all tracked skills |
| `/skill-maintainer budget` | Measure token budgets for all tracked skills |
| `/skill-maintainer history` | Query change history with temporal filters |
| `/skill-maintainer journal` | Query session activity log |
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
5. Record all changes in DuckDB (fact_watermark_check, fact_change)
6. Export backward-compatible `state/state.json`

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

1. Query DuckDB for recent changes affecting the skill's sources
2. Classify changes by type (frontmatter, best practice, API/spec, breaking)
3. For automated patches: apply directly, validate with skills-ref
4. For complex changes: generate update context for Claude-assisted editing
5. Always validate after any update: `uv run skills-ref validate <skill-path>`
6. Record validation result and update attempt in DuckDB
7. Never auto-commit; user reviews diff and commits manually

When classifying changes as breaking vs. additive and generating update recommendations, use ultrathink.

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

Reads from DuckDB and shows:
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

## /skill-maintainer budget

Measure token budgets for all tracked skills.

### Usage

```
/skill-maintainer budget
/skill-maintainer budget --skill plugin-toolkit
```

### Output

Walks all tracked skills, measures each file (SKILL.md, references/, agents/), and reports:
- Token count per file (estimated at 1 token ~ 4 chars)
- Budget status: OK (<4000 tokens), OVER (4000-8000), CRITICAL (>8000)
- Breakdown by file type (skill_md, reference, agent, script)

### Running the measurement

```bash
uv run python skill-maintainer/scripts/measure_content.py
uv run python skill-maintainer/scripts/measure_content.py --skill plugin-toolkit
```

---

## /skill-maintainer history

Query change history with temporal filters.

### Usage

```
/skill-maintainer history
/skill-maintainer history --days 90
/skill-maintainer history --classification BREAKING
```

### Output

Shows all recorded changes from DuckDB with:
- Timestamp, source name, page URL or commit hash
- Classification (BREAKING, ADDITIVE, COSMETIC)
- Summary of what changed

### Running the query

```bash
uv run python skill-maintainer/scripts/store.py --history 30
uv run python skill-maintainer/scripts/store.py --history 90 --classification BREAKING
```

---

## /skill-maintainer journal

Query session activity log.

### Usage

```
/skill-maintainer journal
/skill-maintainer journal --days 7
```

### How it works

Events are logged to a JSONL buffer file for performance (no DuckDB writes during hooks).
Batch ingest moves events from JSONL into DuckDB for queryability.

Skills and commands can tag their session using `${CLAUDE_SESSION_ID}` in log writes, which the journal ingest script uses to correlate activity back to the originating skill invocation.

### Running the journal

```bash
# Ingest buffered events into DuckDB
uv run python skill-maintainer/scripts/journal.py ingest

# Query recent activity
uv run python skill-maintainer/scripts/journal.py query --days 7
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
- **State directory** (`state/`) - DuckDB store + backward-compatible state.json
- **[docs/internals/duckdb_schema.md](../docs/internals/duckdb_schema.md)** - DuckDB schema documentation
