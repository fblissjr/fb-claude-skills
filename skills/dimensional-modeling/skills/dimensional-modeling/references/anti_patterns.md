last updated: 2026-02-14

# anti-patterns

Common mistakes when building Kimball-style star schemas in DuckDB, and how to avoid them.

## 1. PRIMARY KEY on SCD Type 2 dimension tables

**The mistake:**
```sql
CREATE TABLE dim_skill (
    hash_key TEXT PRIMARY KEY,  -- WRONG
    ...
);
```

**Why it breaks:** SCD Type 2 requires multiple rows per entity -- one current (`is_current = TRUE`) and N historical (`is_current = FALSE`). All rows share the same `hash_key`. A PRIMARY KEY constraint prevents inserting the new row when closing the old one.

**The fix:** No PRIMARY KEY constraint. Filter on `is_current = TRUE` in queries.

```sql
CREATE TABLE dim_skill (
    hash_key TEXT NOT NULL,  -- no PK constraint
    ...
);
```

**DuckDB note:** columnar storage doesn't benefit from PK indexes for join performance the way row stores do. Predicate pushdown and zone maps handle that.

## 2. Auto-increment sequences instead of hash keys

**The mistake:**
```sql
CREATE TABLE dim_skill (
    skill_id INTEGER DEFAULT nextval('skill_seq'),
    ...
);
```

**Why it breaks:**
- Non-deterministic: same data produces different IDs across databases
- Coordination: sequences require single-writer access
- Not portable: rebuild the DB and all IDs change, breaking fact table references
- DuckDB-specific: `lastval()` is not reliable for getting the just-inserted ID

**The fix:** MD5 hash of natural keys.

```python
hash_key = dimension_key(skill_name)  # deterministic, portable, no coordination
```

## 3. FK constraints between facts and dimensions

**The mistake:**
```sql
CREATE TABLE fact_validation (
    skill_key TEXT REFERENCES dim_skill(hash_key),  -- WRONG
    ...
);
```

**Why it breaks:**
- Can't have FK to a non-PK column (and dimensions have no PK -- see anti-pattern 1)
- Slows bulk loads (the primary write pattern)
- Creates coupling that makes schema evolution harder

**The fix:** Join by convention. The application layer (your Python code) ensures referential integrity.

## 4. Normalizing fact tables

**The mistake:** Creating lookup tables for categorical fact attributes.

```sql
-- DON'T DO THIS
CREATE TABLE dim_validation_status (
    status_id INTEGER PRIMARY KEY,
    status_name TEXT
);

CREATE TABLE fact_validation (
    ...
    status_id INTEGER REFERENCES dim_validation_status(status_id)
);
```

**Why it's wrong:** Fact tables should be denormalized. Categorical attributes that come from the event itself (status, error_type, severity) belong directly in the fact row as TEXT columns. Only create a dimension table when the entity has mutable attributes you need to track over time.

**The fix:** Carry categorical values directly in the fact table.

```sql
CREATE TABLE fact_validation (
    ...
    status TEXT NOT NULL DEFAULT 'success',  -- just a column
    ...
);
```

## 5. Forgetting metadata columns

**The mistake:** Fact or dimension tables without lineage tracking.

```sql
CREATE TABLE fact_validation (
    skill_key TEXT,
    is_valid BOOLEAN,
    validated_at TIMESTAMP
    -- no record_source, no session_id, no inserted_at
);
```

**Why it matters:** Without metadata, you can't answer:
- "Which script wrote this row?" (record_source)
- "Which session was this part of?" (session_id)
- "When was this row physically inserted?" (inserted_at)

**The fix:** Every table gets `record_source`, `session_id`, `inserted_at` (or `created_at` for dimensions).

## 6. Using timestamps as surrogate keys

**The mistake:** Using `created_at` or `event_at` as the join key between tables.

**Why it breaks:** Timestamps have precision issues, clock skew, and aren't guaranteed unique. Two events in the same millisecond will collide.

**The fix:** Hash surrogate keys for dimensions, composite grain (dim keys + timestamp) for facts.

## 7. One big fact table for everything

**The mistake:** Putting all events into a single `fact_event` table with a `type` column.

```sql
CREATE TABLE fact_event (
    event_type TEXT,  -- 'validation', 'change', 'watermark_check', etc.
    event_data TEXT,  -- JSON blob
    ...
);
```

**Why it breaks:**
- No clear grain (each event type has different measures)
- JSON blob prevents columnar optimization
- Queries require constant `WHERE event_type = ...` filtering
- Can't define sensible column types for measures

**The fix:** One fact table per business process, with typed columns for that process's measures.

**Exception:** `fact_session_event` is acceptable as a single event stream because session events share a grain (one event per session per timestamp) and the measures are uniform (event_type + event_data JSON).

## 8. Making dimensions too wide

**The mistake:** Putting every possible attribute into a single dimension table.

```sql
CREATE TABLE dim_skill (
    hash_key TEXT,
    skill_name TEXT,
    skill_path TEXT,
    auto_update BOOLEAN,
    description TEXT,
    author TEXT,
    version TEXT,
    license TEXT,
    total_tokens INTEGER,    -- this is a measure, not a dimension attribute
    last_validated TIMESTAMP, -- this belongs in a fact table
    ...
);
```

**Why it matters:**
- Measures (total_tokens) belong in fact tables, not dimensions
- Timestamps of events (last_validated) are fact table concerns
- Wide dimensions cause unnecessary SCD Type 2 churn (any attribute change creates a new row)

**The fix:** Keep dimensions lean. Only include attributes that describe the entity itself. Measures and event data go in fact tables.

## 9. Not using hash_diff for change detection

**The mistake:** Comparing individual columns to detect changes.

```python
if old_row.skill_path != new_skill_path or old_row.auto_update != new_auto_update:
    # close old row, open new row
```

**Why it's fragile:** Every time you add a new attribute, you need to update the comparison logic. Easy to miss one.

**The fix:** Compare `hash_diff` values. One check covers all mutable attributes.

```python
new_diff = hash_diff(skill_path=new_path, auto_update=new_auto_update)
if old_row.hash_diff != new_diff:
    # close old row, open new row
```

## 10. Treating DuckDB like a row store

**The mistake:** Using single-row INSERT/UPDATE patterns from PostgreSQL.

**Why it matters:** DuckDB is columnar. It's optimized for:
- Batch inserts (not single-row)
- Full column scans (not row lookups)
- Analytical queries (GROUP BY, window functions, CTEs)

**Best practices for DuckDB:**
- Batch inserts when possible (INSERT ... SELECT, or prepared statements with executemany)
- Use `COPY` for large data loads
- Prefer analytical queries over OLTP patterns
- WAL mode for concurrent read/write access
- The `.duckdb` file can be deleted and recreated from source data (it's a cache, not a source of truth)
