last updated: 2026-02-14

# schema patterns

Reusable templates for dimension tables, fact tables, and meta tables in a Kimball-style DuckDB star schema.

## dimension table template (SCD Type 2)

Every dimension follows this structure. The key constraint: **no PRIMARY KEY** because SCD Type 2 requires multiple rows per entity (one current, N historical).

```sql
CREATE TABLE IF NOT EXISTS dim_<name> (
    -- surrogate key (MD5 of natural keys)
    hash_key         TEXT NOT NULL,

    -- natural key columns (what uniquely identifies the entity)
    <natural_key_1>  TEXT NOT NULL,
    <natural_key_2>  TEXT,            -- optional composite key component

    -- business attributes (the mutable stuff you're tracking)
    <attribute_1>    TEXT,
    <attribute_2>    BOOLEAN,
    <attribute_3>    INTEGER,

    -- SCD Type 2 columns
    effective_from   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    effective_to     TIMESTAMP,       -- NULL = current row
    is_current       BOOLEAN NOT NULL DEFAULT TRUE,
    hash_diff        TEXT,            -- MD5 of non-key attributes

    -- metadata
    record_source    TEXT NOT NULL,   -- lineage: who wrote this row
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    session_id       TEXT,            -- Claude Code session (degenerate dim)
    last_verified_at TIMESTAMP        -- staleness signal
);
```

### example: dim_source (from store.py)

```sql
CREATE TABLE IF NOT EXISTS dim_source (
    hash_key         TEXT NOT NULL,
    source_name      TEXT NOT NULL,
    source_type      TEXT NOT NULL,   -- 'docs' or 'source'
    url              TEXT,
    effective_from   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    effective_to     TIMESTAMP,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE,
    hash_diff        TEXT,
    record_source    TEXT NOT NULL DEFAULT 'config_sync',
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    session_id       TEXT,
    last_verified_at TIMESTAMP
);
```

### example: dim_skill

```sql
CREATE TABLE IF NOT EXISTS dim_skill (
    hash_key         TEXT NOT NULL,
    skill_name       TEXT NOT NULL,
    skill_path       TEXT NOT NULL,
    auto_update      BOOLEAN DEFAULT FALSE,
    effective_from   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    effective_to     TIMESTAMP,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE,
    hash_diff        TEXT,
    record_source    TEXT NOT NULL DEFAULT 'config_sync',
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    session_id       TEXT,
    last_verified_at TIMESTAMP
);
```

## fact table template

Fact tables are append-only event logs. No PKs, no sequences. The grain is the composite of dimension surrogate keys + event timestamp.

```sql
CREATE TABLE IF NOT EXISTS fact_<name> (
    -- dimension keys (TEXT, join by convention to dim_*.hash_key)
    <dim_1>_key      TEXT NOT NULL,
    <dim_2>_key      TEXT,

    -- degenerate dimensions (high cardinality, no separate table)
    session_id       TEXT,

    -- measures (the quantifiable stuff)
    <measure_1>      INTEGER,
    <measure_2>      REAL,
    <measure_3>      TEXT,            -- categorical measure

    -- event timestamp (part of the grain)
    <event>_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,

    -- metadata
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL,
    session_id       TEXT              -- capturing session (if different from measured session)
);
```

### example: fact_validation

```sql
CREATE TABLE IF NOT EXISTS fact_validation (
    skill_key        TEXT NOT NULL,
    validated_at     TIMESTAMP NOT NULL DEFAULT current_timestamp,
    validator        TEXT NOT NULL DEFAULT 'skills-ref',
    is_valid         BOOLEAN NOT NULL,
    error_count      INTEGER DEFAULT 0,
    warning_count    INTEGER DEFAULT 0,
    errors_json      TEXT,
    warnings_json    TEXT,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'validate_skill',
    session_id       TEXT
);
```

### example: fact_content_measurement

```sql
CREATE TABLE IF NOT EXISTS fact_content_measurement (
    skill_key        TEXT NOT NULL,
    measured_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    file_path        TEXT NOT NULL,
    file_type        TEXT NOT NULL,
    line_count       INTEGER DEFAULT 0,
    word_count       INTEGER DEFAULT 0,
    char_count       INTEGER DEFAULT 0,
    estimated_tokens INTEGER DEFAULT 0,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'measure_content',
    session_id       TEXT
);
```

## bridge table pattern

When a many-to-many relationship exists between dimensions (e.g., which sources affect which skills):

```sql
CREATE TABLE IF NOT EXISTS skill_source_dep (
    skill_key        TEXT NOT NULL,
    source_key       TEXT NOT NULL,
    record_source    TEXT NOT NULL DEFAULT 'config_sync',
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp
);
```

Bridge tables are flat routing tables. No SCD Type 2 -- just delete and re-insert when the mapping changes.

## meta tables

Every database needs these two tables for operational visibility:

```sql
-- schema versioning
CREATE TABLE IF NOT EXISTS meta_schema_version (
    version      INTEGER NOT NULL,
    applied_at   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    description  TEXT
);

-- load logging (operational visibility)
CREATE TABLE IF NOT EXISTS meta_load_log (
    script_name  TEXT NOT NULL,
    started_at   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    completed_at TIMESTAMP,
    rows_inserted INTEGER DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'running',
    error_message TEXT,
    session_id   TEXT
);
```

## session events pattern

Session boundaries as events in a fact table, not a separate dimension:

```sql
CREATE TABLE IF NOT EXISTS fact_session_event (
    session_id   TEXT NOT NULL,
    event_type   TEXT NOT NULL,       -- 'session_start', 'session_end', 'tool_use', etc.
    event_at     TIMESTAMP NOT NULL DEFAULT current_timestamp,
    event_data   TEXT,                -- JSON blob for event-specific data
    inserted_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source TEXT NOT NULL,
    session_id_  TEXT                 -- if capturing session differs from measured session
);
```

This avoids a separate fact_session table. Sessions have a start event and an end event. Query `WHERE event_type = 'session_start'` to find sessions.

## degenerate dimension pattern

When the natural key IS the only interesting attribute (session_id, transaction_id):

- Carry directly in fact rows as a TEXT column
- No separate dimension table
- Join across fact tables via the degenerate dimension column

Example: `session_id` appears in every fact table but has no separate `dim_session` table. The session UUID is the only attribute that matters.

## view pattern

Views always filter `is_current = TRUE` on dimension joins unless doing historical analysis:

```sql
CREATE VIEW v_skill_freshness AS
SELECT
    s.skill_name,
    s.skill_path,
    MAX(fc.checked_at) AS last_checked,
    MAX(fc2.changed_at) AS last_changed
FROM dim_skill s
JOIN skill_source_dep dep ON dep.skill_key = s.hash_key
LEFT JOIN fact_watermark_check fc ON fc.source_key = dep.source_key
LEFT JOIN fact_change fc2 ON fc2.source_key = dep.source_key
WHERE s.is_current = TRUE
GROUP BY s.skill_name, s.skill_path;
```
