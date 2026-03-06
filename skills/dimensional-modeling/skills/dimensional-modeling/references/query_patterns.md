last updated: 2026-02-14

# query patterns

Star schema query cookbook for DuckDB. All patterns assume Kimball conventions: SCD Type 2 dimensions, hash surrogate keys, append-only fact tables.

## basic join pattern

Always filter `is_current = TRUE` when joining dimensions for current-state queries:

```sql
SELECT
    d.skill_name,
    f.validated_at,
    f.is_valid,
    f.error_count
FROM fact_validation f
JOIN dim_skill d ON d.hash_key = f.skill_key AND d.is_current = TRUE
ORDER BY f.validated_at DESC;
```

## latest-per-entity pattern

Get the most recent fact row for each dimension member. Uses window functions:

```sql
SELECT *
FROM (
    SELECT
        d.skill_name,
        f.*,
        ROW_NUMBER() OVER (PARTITION BY f.skill_key ORDER BY f.validated_at DESC) AS rn
    FROM fact_validation f
    JOIN dim_skill d ON d.hash_key = f.skill_key AND d.is_current = TRUE
) sub
WHERE rn = 1;
```

## time-bounded query

Filter facts within a time range. DuckDB supports INTERVAL arithmetic:

```sql
SELECT
    d.source_name,
    COUNT(*) AS check_count,
    SUM(CASE WHEN f.status = 'changed' THEN 1 ELSE 0 END) AS change_count
FROM fact_watermark_check f
JOIN dim_source d ON d.hash_key = f.source_key AND d.is_current = TRUE
WHERE f.checked_at > current_timestamp - INTERVAL '30 days'
GROUP BY d.source_name;
```

## trend analysis (time series)

Track a measure over time using DATE_TRUNC:

```sql
SELECT
    DATE_TRUNC('week', f.measured_at) AS week,
    d.skill_name,
    SUM(f.estimated_tokens) AS total_tokens,
    COUNT(DISTINCT f.file_path) AS file_count
FROM fact_content_measurement f
JOIN dim_skill d ON d.hash_key = f.skill_key AND d.is_current = TRUE
GROUP BY DATE_TRUNC('week', f.measured_at), d.skill_name
ORDER BY week DESC, d.skill_name;
```

## SCD Type 2 point-in-time query

Look up what a dimension looked like at a specific point in time:

```sql
SELECT *
FROM dim_skill
WHERE hash_key = ?
  AND effective_from <= TIMESTAMP '2026-01-15'
  AND (effective_to IS NULL OR effective_to > TIMESTAMP '2026-01-15');
```

This returns the dimension row that was current on January 15th, regardless of whether it's still current now.

## SCD Type 2 change history

See all versions of a dimension entity:

```sql
SELECT
    skill_name,
    skill_path,
    auto_update,
    effective_from,
    effective_to,
    is_current,
    hash_diff
FROM dim_skill
WHERE hash_key = ?
ORDER BY effective_from;
```

## multi-fact query via shared dimension

Join two fact tables through a shared dimension:

```sql
SELECT
    d.skill_name,
    v.is_valid,
    v.error_count,
    m.estimated_tokens AS total_tokens
FROM dim_skill d
JOIN (
    SELECT skill_key, is_valid, error_count,
           ROW_NUMBER() OVER (PARTITION BY skill_key ORDER BY validated_at DESC) AS rn
    FROM fact_validation
) v ON v.skill_key = d.hash_key AND v.rn = 1
JOIN (
    SELECT skill_key, SUM(estimated_tokens) AS estimated_tokens
    FROM fact_content_measurement
    WHERE measured_at > current_timestamp - INTERVAL '7 days'
    GROUP BY skill_key
) m ON m.skill_key = d.hash_key
WHERE d.is_current = TRUE;
```

## freshness check

Identify stale dimensions (haven't been verified recently):

```sql
SELECT
    skill_name,
    skill_path,
    last_verified_at,
    DATEDIFF('day', last_verified_at, current_timestamp) AS days_since_verified
FROM dim_skill
WHERE is_current = TRUE
  AND (last_verified_at IS NULL
       OR DATEDIFF('day', last_verified_at, current_timestamp) > 7)
ORDER BY last_verified_at ASC NULLS FIRST;
```

## aggregation with FILTER clause

DuckDB supports FILTER for conditional aggregation (cleaner than CASE WHEN):

```sql
SELECT
    d.source_name,
    COUNT(*) AS total_checks,
    COUNT(*) FILTER (WHERE f.status = 'changed') AS changes,
    COUNT(*) FILTER (WHERE f.status = 'unchanged') AS no_changes
FROM fact_watermark_check f
JOIN dim_source d ON d.hash_key = f.source_key AND d.is_current = TRUE
GROUP BY d.source_name;
```

## recursive CTE for DAG traversal

Traverse a dependency DAG (e.g., skill dependencies):

```sql
WITH RECURSIVE deps AS (
    SELECT child_key AS key, 1 AS depth
    FROM bridge_dependency
    WHERE parent_key = ?
    UNION ALL
    SELECT b.child_key, d.depth + 1
    FROM bridge_dependency b
    JOIN deps d ON b.parent_key = d.key
    WHERE d.depth < 10  -- prevent infinite recursion
)
SELECT DISTINCT key, depth
FROM deps
ORDER BY depth;
```

## budget trend view

Track token budget trajectory over time (meta-cognition: "am I getting fatter?"):

```sql
CREATE VIEW v_skill_budget_trend AS
SELECT
    d.skill_name,
    DATE_TRUNC('day', f.measured_at) AS measurement_date,
    SUM(f.estimated_tokens) AS total_tokens,
    SUM(f.line_count) AS total_lines,
    SUM(f.word_count) AS total_words,
    COUNT(DISTINCT f.file_path) AS file_count
FROM fact_content_measurement f
JOIN dim_skill d ON d.hash_key = f.skill_key AND d.is_current = TRUE
GROUP BY d.skill_name, DATE_TRUNC('day', f.measured_at)
ORDER BY d.skill_name, measurement_date DESC;
```

## load logging pattern

Wrap script execution in meta_load_log entries:

```python
def log_load_start(con, script_name, session_id=None):
    con.execute("""
        INSERT INTO meta_load_log (script_name, session_id)
        VALUES (?, ?)
    """, [script_name, session_id])

def log_load_complete(con, script_name, rows_inserted, status='success', error=None):
    con.execute("""
        UPDATE meta_load_log
        SET completed_at = current_timestamp,
            rows_inserted = ?,
            status = ?,
            error_message = ?
        WHERE script_name = ?
          AND completed_at IS NULL
    """, [rows_inserted, status, error, script_name])
```
