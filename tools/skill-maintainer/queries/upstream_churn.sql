-- How fast does each tracked upstream page actually move?
--
-- `review_interval_days` is tiered 30 / 90 / 365 by "how fast the source
-- moves", and `.skill-maintainer/state/changes.jsonl` is the only record of how
-- fast each source actually moved. Nothing read it that way until 2026-08-02,
-- so the tiers had been set from intuition while the evidence sat unread.
--
-- Deliberately a query file and not a CLI subcommand. It has been run once, and
-- one use does not earn a command, a `duckdb` dependency on this tool, or a
-- flag that has to be documented and kept working. If it turns out to get run
-- every maintenance pass, that is the evidence for promoting it.
--
-- Run it:
--   uv run python -c "import duckdb,sys; \
--     print(duckdb.sql(open('tools/skill-maintainer/queries/upstream_churn.sql').read()))"
-- from the repo root, with .skill-maintainer/state/changes.jsonl present.
--
-- SHAPE DRIFT, and why the CASE below is not paranoia: `changed_pages` holds
-- bare strings in pre-0.4.0 entries and structs after (CHANGELOG 1509). Reading
-- the column as JSON and branching on `json_type` is what lets both eras count.
-- `union_by_name` cannot reconcile LIST(VARCHAR) with LIST(STRUCT).
--
-- Consequence for reading the output: `changes` is comparable across the whole
-- window, because a page name is a page name in both formats. `abs_chars` is
-- NOT -- only struct-era rows carry `chars_delta`, so a page whose changes are
-- mostly pre-0.4.0 will understate its volume, and a page first seen after the
-- format change can look artificially volatile. Rank on `changes`.

WITH e AS (
    SELECT *
    FROM read_json(
        '.skill-maintainer/state/changes.jsonl',
        format = 'newline_delimited',
        union_by_name = true,
        ignore_errors = true,
        columns = {type: 'VARCHAR', date: 'VARCHAR', changed_pages: 'JSON'}
    )
    WHERE type = 'upstream_check'
),
x AS (
    SELECT
        e.date,
        CASE WHEN json_type(p) = 'VARCHAR' THEN p ->> '$' ELSE p ->> 'url' END AS page,
        TRY_CAST(p ->> 'chars_delta' AS BIGINT)                               AS chars_delta
    FROM e, UNNEST(from_json(e.changed_pages, '["JSON"]')) AS t (p)
)
SELECT
    page,
    COUNT(*)                              AS changes,
    MIN(date)[1:10]                       AS first_seen,
    MAX(date)[1:10]                       AS last_seen,
    SUM(COALESCE(ABS(chars_delta), 0))    AS abs_chars_struct_era_only
FROM x
WHERE page IS NOT NULL
GROUP BY 1
ORDER BY changes DESC, abs_chars_struct_era_only DESC;
