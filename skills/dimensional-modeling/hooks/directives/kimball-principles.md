# trigger: duckdb
## Dimensional modeling principles (auto-loaded)
- Abstract the data, not the behavior. Model what happened (facts) in what context (dimensions).
- Grain first: state the grain as a sentence before designing tables. When in doubt, go finer.
- Facts are append-only. No primary keys, no sequences. Deterministic surrogate keys via MD5 hash.
- Full dimension table when attributes change (SCD Type 2). Degenerate dimension when key is the only attribute.
- Metadata on every row: inserted_at, record_source, session_id.
- For full methodology, schema patterns, and anti-patterns, invoke /dimensional-modeling:dimensional-modeling.
