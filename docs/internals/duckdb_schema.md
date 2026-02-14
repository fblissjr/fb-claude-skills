last updated: 2026-02-14

# duckdb schema (v2)

Kimball-style dimensional store for skill-maintainer state. Replaces the v1 OLTP schema (integer PKs, sequences, FK constraints) with proper dimensional modeling: MD5 hash surrogate keys, SCD Type 2 on all dimensions, no fact table primary keys, metadata columns for lineage tracking.

**Schema version**: 2
**Database location**: `skill-maintainer/state/skill_store.duckdb`

**Reconstruction**: The `.duckdb` file is `.gitignore`d. To rebuild from scratch:
1. Run `uv run python skill-maintainer/scripts/migrate_state.py --force` (imports state.json into v2 schema)
2. Or simply run any monitor script -- `Store.__init__` creates the schema and syncs dimensions from config.yaml automatically.

---

## key generation

All dimension surrogate keys are MD5 hashes of natural keys:

```python
def _hash_key(*natural_keys) -> str:
    """MD5 surrogate from natural key components."""
    parts = [str(k) if k is not None else "-1" for k in natural_keys]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
```

| Dimension | Natural Key(s) | Hash Input |
|-----------|---------------|------------|
| dim_source | source_name | `source_name` |
| dim_skill | skill_name | `skill_name` |
| dim_page | source_key + url | `source_key\|url` |

Fact tables have no surrogate keys. Their grain is the composite of dimension keys + event timestamp.

---

## SCD Type 2 metadata

Every dimension table carries these columns for slowly-changing dimension tracking:

| Column | Type | Description |
|--------|------|-------------|
| hash_key | TEXT NOT NULL | MD5 surrogate from natural keys (no PK -- SCD Type 2 requires multiple rows per entity) |
| effective_from | TIMESTAMP | When this row became current |
| effective_to | TIMESTAMP | When this row was superseded (NULL = current) |
| is_current | BOOLEAN | TRUE for the active row |
| hash_diff | TEXT | MD5 of non-key attributes (change detection) |
| record_source | TEXT | Origin: `config_sync`, `manual`, `cdc_detection` |
| created_at | TIMESTAMP | Row creation time |
| session_id | TEXT | Claude Code session (NULL for config_sync) |
| last_verified_at | TIMESTAMP | Last confirmed still true (staleness signal) |

When `config.yaml` changes a dimension's attributes (e.g., skill path changes), the old row is closed (`effective_to = now(), is_current = FALSE`) and a new row opened. The `hash_diff` detects whether non-key attributes actually changed.

---

## dimensions

### dim_source

Populated from `config.yaml` sources on Store init.

| Column | Type | Description |
|--------|------|-------------|
| hash_key | TEXT NOT NULL | `_hash_key(source_name)` |
| source_name | TEXT | e.g. `anthropic-skills-docs` |
| source_type | TEXT | `docs` or `source` |
| url | TEXT | `llms_full_url` for docs, `repo` URL for source |
| + SCD Type 2 columns | | See above |

### dim_skill

Populated from `config.yaml` skills on Store init.

| Column | Type | Description |
|--------|------|-------------|
| hash_key | TEXT NOT NULL | `_hash_key(skill_name)` |
| skill_name | TEXT | e.g. `plugin-toolkit` |
| skill_path | TEXT | Relative path to skill directory |
| auto_update | BOOLEAN | Always `FALSE` (manual review required) |
| + SCD Type 2 columns | | See above |

### dim_page

One row per watched URL per source. Populated from `config.yaml` pages lists.

| Column | Type | Description |
|--------|------|-------------|
| hash_key | TEXT NOT NULL | `_hash_key(source_key, url)` |
| source_key | TEXT | References dim_source.hash_key (no FK constraint) |
| url | TEXT | Full page URL |
| + SCD Type 2 columns | | See above |

### skill_source_dep

Junction table mapping which sources affect which skills.

| Column | Type | Description |
|--------|------|-------------|
| skill_key | TEXT | References dim_skill.hash_key |
| source_key | TEXT | References dim_source.hash_key |
| effective_from | TIMESTAMP | When this dependency was established |
| effective_to | TIMESTAMP | When this dependency was removed (NULL = active) |
| is_current | BOOLEAN | TRUE for active dependencies |
| record_source | TEXT | Origin of the dependency |
| created_at | TIMESTAMP | Row creation time |

---

## facts (append-only, no PKs, no sequences)

All fact tables include metadata columns:

| Column | Type | Description |
|--------|------|-------------|
| inserted_at | TIMESTAMP | When the row was written to DuckDB |
| record_source | TEXT | Script that produced this row |
| session_id | TEXT | Claude Code session (NULL for automated runs) |

### fact_watermark_check

Records each CDC detect-layer check (HTTP HEAD against `llms_full_url`).

| Column | Type | Description |
|--------|------|-------------|
| source_key | TEXT | References dim_source.hash_key |
| checked_at | TIMESTAMP | When the check ran |
| last_modified | TEXT | HTTP `Last-Modified` header value |
| etag | TEXT | HTTP `ETag` header value |
| changed | BOOLEAN | Whether the watermark indicated a change |

### fact_change

Records each detected content change (CDC identify+classify layers).

| Column | Type | Description |
|--------|------|-------------|
| source_key | TEXT | References dim_source.hash_key |
| page_key | TEXT | References dim_page.hash_key (NULL for source-type/local changes) |
| detected_at | TIMESTAMP | When the change was detected |
| classification | TEXT | `BREAKING`, `ADDITIVE`, `COSMETIC`, or `ERROR` |
| old_hash | TEXT | Previous SHA-256 (empty for initial capture) |
| new_hash | TEXT | Current SHA-256 |
| summary | TEXT | e.g. `+5 -2 lines` or `initial capture` |
| content_preview | TEXT | First 3000 chars of content |
| commit_hash | TEXT | For git source monitoring |
| commit_count | INTEGER | Number of commits in change window |

### fact_validation

Records each skill validation run (via `validate_skill.py` or post-update).

| Column | Type | Description |
|--------|------|-------------|
| skill_key | TEXT | References dim_skill.hash_key |
| validated_at | TIMESTAMP | When validation ran |
| is_valid | BOOLEAN | Pass/fail result |
| error_count | INTEGER | Number of errors found |
| warning_count | INTEGER | Number of warnings found |
| errors | TEXT | JSON array of error messages |
| warnings | TEXT | JSON array of warning messages |
| trigger_type | TEXT | `manual`, `post-update`, or `freshness-check` |

### fact_update_attempt

Records each update attempt from `apply_updates.py`.

| Column | Type | Description |
|--------|------|-------------|
| skill_key | TEXT | References dim_skill.hash_key |
| attempted_at | TIMESTAMP | When the attempt started |
| mode | TEXT | `report-only`, `apply-local`, or `create-pr` |
| status | TEXT | `pending_review`, `applied`, or `reverted` |
| changes_applied | INTEGER | Count of changes applied |
| backup_path | TEXT | Path to backup directory |

### fact_content_measurement

Records token budget measurements from `measure_content.py`.

| Column | Type | Description |
|--------|------|-------------|
| skill_key | TEXT | References dim_skill.hash_key |
| file_path | TEXT | Absolute path to measured file |
| file_type | TEXT | `skill_md`, `reference`, `agent`, `hook`, `command_md`, `script`, `other` |
| measured_at | TIMESTAMP | When the measurement was taken |
| line_count | INTEGER | Lines in file |
| word_count | INTEGER | Words in file |
| char_count | INTEGER | Characters in file |
| estimated_tokens | INTEGER | `char_count / 4` (rough estimate) |
| content_hash | TEXT | SHA-256 of file content |

### fact_session_event

Records session events (from hooks via JSONL buffer). Session boundaries are events (`event_type = 'session_start'` / `'session_end'`), not a separate table.

| Column | Type | Description |
|--------|------|-------------|
| session_id | TEXT | Claude Code session UUID (the session being described) |
| event_type | TEXT | e.g. `session_start`, `session_end`, `file_modified`, `validation_run` |
| event_at | TIMESTAMP | When the event occurred |
| target_path | TEXT | File or resource affected |
| metadata | TEXT | JSON blob with additional context |
| started_at | TIMESTAMP | For session_start events: session start time |
| ended_at | TIMESTAMP | For session_end events: session end time |
| working_dir | TEXT | Working directory |
| _session_id | TEXT | The capturing session (distinct from the described session) |

---

## meta tables

### meta_schema_version

Tracks schema evolution. On init, checks current version and applies migrations sequentially.

| Column | Type | Description |
|--------|------|-------------|
| version | INTEGER | Schema version number |
| applied_at | TIMESTAMP | When this version was applied |
| description | TEXT | What changed in this version |

Current version: 2 (v1 was integer-PK OLTP schema).

### meta_load_log

Tracks each script execution for operational visibility.

| Column | Type | Description |
|--------|------|-------------|
| script_name | TEXT | e.g. `migrate_state`, `journal_ingest` |
| started_at | TIMESTAMP | When the script started |
| completed_at | TIMESTAMP | When it finished (NULL if still running) |
| rows_inserted | INTEGER | Count of rows written |
| status | TEXT | `running`, `success`, `failed`, `partial` |
| error_message | TEXT | Error details if failed |
| session_id | TEXT | Claude Code session |

---

## views

All views filter to `is_current = TRUE` on dimension joins and use `hash_key` / `source_key` / `skill_key` / `page_key` instead of integer IDs.

### v_latest_watermark

Latest watermark check per source. Replaces `state["docs"][name]["_watermark"]` lookup.

```sql
SELECT source_key, checked_at, last_modified, etag, changed
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY source_key ORDER BY checked_at DESC) AS rn
    FROM fact_watermark_check
)
WHERE rn = 1;
```

### v_latest_page_hash

Latest content hash per page. Replaces `state["docs"][name]["_pages"][url]["hash"]` lookup.

```sql
SELECT page_key, detected_at, new_hash AS current_hash, content_preview
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY page_key ORDER BY detected_at DESC) AS rn
    FROM fact_change
    WHERE page_key IS NOT NULL
)
WHERE rn = 1;
```

### v_skill_freshness

Per-skill freshness summary with `is_current = TRUE` filter on dimension joins.

```sql
SELECT
    s.skill_name, s.skill_path,
    MAX(fc.detected_at) AS last_change_detected,
    MAX(fv.validated_at) AS last_validated,
    SUM(CASE WHEN fc.classification = 'BREAKING' THEN 1 ELSE 0 END) AS breaking_count,
    SUM(CASE WHEN fc.classification = 'ADDITIVE' THEN 1 ELSE 0 END) AS additive_count
FROM dim_skill s
LEFT JOIN skill_source_dep ssd ON ssd.skill_key = s.hash_key AND ssd.is_current = TRUE
LEFT JOIN fact_change fc ON fc.source_key = ssd.source_key
LEFT JOIN fact_validation fv ON fv.skill_key = s.hash_key
WHERE s.is_current = TRUE
GROUP BY s.skill_name, s.skill_path;
```

### v_skill_budget

Token budget per skill (latest measurement per file).

```sql
SELECT
    s.skill_name,
    SUM(CASE WHEN m.file_type = 'skill_md' THEN m.estimated_tokens ELSE 0 END) AS skill_md_tokens,
    SUM(CASE WHEN m.file_type = 'reference' THEN m.estimated_tokens ELSE 0 END) AS reference_tokens,
    SUM(m.estimated_tokens) AS total_tokens,
    SUM(m.estimated_tokens) > 4000 AS over_budget
FROM dim_skill s
LEFT JOIN (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY skill_key, file_path ORDER BY measured_at DESC) AS rn
    FROM fact_content_measurement
) m ON m.skill_key = s.hash_key AND m.rn = 1
WHERE s.is_current = TRUE
GROUP BY s.skill_name;
```

### v_skill_budget_trend

Token budget trend over time per skill. Enables meta-cognition: "is a skill getting fatter over time?" With daily measurements, shows growth/shrinkage trends.

```sql
SELECT
    s.skill_name,
    DATE_TRUNC('day', m.measured_at) AS measured_date,
    SUM(m.estimated_tokens) AS total_tokens,
    SUM(CASE WHEN m.file_type = 'skill_md' THEN m.estimated_tokens ELSE 0 END) AS skill_md_tokens,
    SUM(CASE WHEN m.file_type = 'reference' THEN m.estimated_tokens ELSE 0 END) AS reference_tokens,
    COUNT(DISTINCT m.file_path) AS file_count
FROM dim_skill s
JOIN fact_content_measurement m ON m.skill_key = s.hash_key
WHERE s.is_current = TRUE
GROUP BY s.skill_name, DATE_TRUNC('day', m.measured_at)
ORDER BY s.skill_name, measured_date;
```

### v_latest_source_check

Latest source monitoring check per source.

```sql
SELECT source_key, detected_at AS last_checked, commit_hash, commit_count
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY source_key ORDER BY detected_at DESC) AS rn
    FROM fact_change
    WHERE commit_hash IS NOT NULL
)
WHERE rn = 1;
```

---

## entity relationship

```
dim_source ----- dim_page
    |
    +--- skill_source_dep --- dim_skill
    |
    +--- fact_watermark_check
    +--- fact_change ---------- dim_page

dim_skill --+--- fact_validation
            +--- fact_update_attempt
            +--- fact_content_measurement

fact_session_event (session boundaries are events, not a separate dimension)

meta_schema_version
meta_load_log
```

---

## migration from v1

v1 schema (integer PKs, sequences, FK constraints) is automatically detected and dropped when Store initializes on a v1 database. The migration path:

1. Store.__init__ checks `meta_schema_version` table
2. If missing or version < 2, drops all v1 objects (views, tables, sequences)
3. Creates v2 schema from DDL
4. Records version 2 in `meta_schema_version`
5. Syncs dimensions from config.yaml
6. Run `migrate_state.py --force` to re-import state.json data

---

## what changed from v1

| Aspect | v1 | v2 |
|--------|----|----|
| Dimension PKs | INTEGER with MAX(id)+1 | TEXT MD5 hash of natural keys |
| Fact PKs | INTEGER with sequences | None (grain = dim keys + timestamp) |
| Change detection | Check if name exists, UPDATE | hash_diff comparison, SCD Type 2 |
| FK constraints | Hard REFERENCES clauses | None (join by convention) |
| Sequences | 6 sequences | None |
| Metadata | created_at only on dims | record_source, session_id, inserted_at on all tables |
| Session tracking | fact_session (separate table) + fact_session_event | fact_session_event only (boundaries are events) |
| Schema versioning | None | meta_schema_version table |
| Load logging | None | meta_load_log table |
| View joins | On integer IDs | On hash_key with is_current = TRUE filter |

---

## usage patterns

### from Python scripts

```python
from store import Store

with Store() as store:
    # Record a change (record_source defaults based on method)
    store.record_change("anthropic-skills-docs", page_url="https://...",
                        classification="ADDITIVE", ...)

    # Query freshness (views filter to is_current = TRUE)
    freshness = store.get_skill_freshness()

    # Export backward-compatible state.json
    state = store.export_state_json()
```

### CLI queries

```bash
# Show recent changes
uv run python skill-maintainer/scripts/store.py --history 30

# Show DB stats (includes schema version)
uv run python skill-maintainer/scripts/store.py --stats

# Show skill freshness
uv run python skill-maintainer/scripts/store.py --freshness

# Show token budgets
uv run python skill-maintainer/scripts/store.py --budget

# Export state.json
uv run python skill-maintainer/scripts/store.py --export skill-maintainer/state/state.json
```

---

## backward compatibility

`Store.export_state_json()` produces output matching the old `state.json` format:

```json
{
  "docs": {
    "<source_name>": {
      "_watermark": { "last_modified": "...", "etag": "...", "last_checked": "..." },
      "_pages": {
        "<url>": { "hash": "...", "content_preview": "...", "last_checked": "...", "last_changed": "..." }
      }
    }
  },
  "sources": {
    "<source_name>": { "last_checked": "...", "last_commit": "...", "commits_since_last": 0 }
  }
}
```

All CDC scripts call `store.export_state_json_file()` at the end of each run to keep `state.json` in sync for any tools that still read it directly.
