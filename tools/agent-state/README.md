last updated: 2026-03-12

# agent-state

DuckDB-backed audit and state tracking for pipeline, agent, and CLI runs. Kimball star schema with run hierarchy, watermark history, and skill version lineage.

## installation

### within fb-claude-skills (already available)

After `uv sync --all-packages`, the `agent-state` command is available in the workspace venv.

### in another repo (git install)

```bash
uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/agent-state
```

## storage

Single global DuckDB at `~/.claude/agent_state.duckdb`. Created automatically on first use.

## schema

Schema version: **2** (see `src/agent_state/schemas/agent_state.sql` for full DDL).

### tables

| Table | Type | Purpose |
|-------|------|---------|
| `meta_schema_version` | meta | Schema version tracking |
| `dim_run_source` | dimension | Where runs originate (SCD Type 1) |
| `dim_skill_version` | dimension | Skill content versions (append-only, keyed by content hash) |
| `dim_watermark_source` | dimension | What we track watermarks for |
| `fact_run` | fact | Core audit table (one row per execution) |
| `fact_run_message` | fact | Structured log per run |
| `fact_watermark` | fact | Watermark state history (append-only) |

### views

| View | Purpose |
|------|---------|
| `v_latest_watermark` | Current watermark per source |
| `v_run_tree` | Recursive CTE for hierarchical run display |
| `v_flywheel` | Producer run -> skill version -> consumer run |
| `v_restartable_failures` | Failed runs eligible for retry |

### dim_skill_version columns

| Column | Type | Purpose |
|--------|------|---------|
| `skill_version_id` | INTEGER PK | Auto-increment ID |
| `skill_name` | VARCHAR | Skill name |
| `skill_path` | VARCHAR | Path to SKILL.md |
| `version_hash` | VARCHAR | SHA-256 of SKILL.md content |
| `repo_root` | VARCHAR | Repository root path |
| `token_count` | INTEGER | Estimated token count |
| `is_valid` | BOOLEAN | Spec validation pass/fail |
| `created_at` | TIMESTAMP | When this version was recorded |
| `created_by_run_id` | VARCHAR | Loose FK to fact_run |
| `domain` | VARCHAR | Routing: 'extraction', 'validation', etc. |
| `task_type` | VARCHAR | Routing: 'structured_data_from_document', etc. |
| `status` | VARCHAR | Lifecycle: 'draft', 'active', 'deprecated' (default: 'active') |
| `metadata` | JSON | Arbitrary metadata |

`is_valid` (spec compliance) is orthogonal to `status` (lifecycle state). A skill can be valid but deprecated, or draft but valid.

### schema migrations

Migrations are appended to the bottom of `agent_state.sql` and run idempotently on every database open. The pattern:

1. `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for existing databases
2. Conditional `INSERT INTO meta_schema_version` to record the migration
3. `CREATE INDEX IF NOT EXISTS` for new columns (must come after ALTER TABLE)

The CREATE TABLE statements include all columns for fresh databases; the ALTER TABLE handles existing databases. Both paths are idempotent.

| Version | Description |
|---------|-------------|
| 1 | Initial schema |
| 2 | Add `domain`, `task_type`, `status` to `dim_skill_version` |

## CLI

```bash
agent-state init          # Initialize database
agent-state status        # Show database summary
agent-state runs          # List recent runs
agent-state tree [run_id] # Show hierarchical run tree
agent-state watermarks    # Show current watermarks
agent-state flywheel      # Show producer -> skill -> consumer chain
agent-state migrate       # Import from changes.jsonl / upstream_hashes.json
```

All commands accept `--db <path>` to use a non-default database.

## Python API

```python
from agent_state.database import AgentStateDB
from agent_state.run_context import RunContext
from agent_state.skill_versions import (
    get_or_create_skill_version,
    get_active_skill,
    deprecate_skill_version,
    get_skills_by_domain,
)

# Track a run with automatic status management
with RunContext(db, run_type="pipeline", run_name="my-pipeline") as ctx:
    ctx.log("Starting extraction")
    # ... do work ...
    ctx.set_counts(extract_count=10, insert_count=10)

# Register a skill version with routing metadata
sv_id = get_or_create_skill_version(
    db, "extractor", version_hash,
    domain="extraction",
    task_type="structured_data_from_document",
)

# Query by domain
skills = get_skills_by_domain(db, "extraction")

# Lifecycle management
deprecate_skill_version(db, old_version_id)
active = get_active_skill(db, "extractor")
```

## tests

```bash
uv run pytest tools/agent-state/tests/ -v
```
