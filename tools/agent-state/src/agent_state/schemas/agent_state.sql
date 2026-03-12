-- agent-state DuckDB schema (Kimball star schema for run audit + skill lineage)

-- Schema version tracking
CREATE TABLE IF NOT EXISTS meta_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR
);
INSERT INTO meta_schema_version (version, description)
SELECT 1, 'Initial schema'
WHERE NOT EXISTS (SELECT 1 FROM meta_schema_version WHERE version = 1);

-- Sequences
CREATE SEQUENCE IF NOT EXISTS seq_skill_version START 1;
CREATE SEQUENCE IF NOT EXISTS seq_run_message START 1;
CREATE SEQUENCE IF NOT EXISTS seq_watermark START 1;

-- ============================================================
-- DIMENSIONS
-- ============================================================

-- dim_run_source: where runs originate (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_run_source (
    source_key VARCHAR PRIMARY KEY,          -- deterministic hash of source_type + source_name + source_version
    source_type VARCHAR NOT NULL,            -- 'pipeline', 'agent_sdk', 'claude_code'
    source_name VARCHAR NOT NULL,
    source_version VARCHAR,
    config_hash VARCHAR,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- dim_skill_version: flywheel connector (append-only, each content hash = new row)
CREATE TABLE IF NOT EXISTS dim_skill_version (
    skill_version_id INTEGER PRIMARY KEY DEFAULT nextval('seq_skill_version'),
    skill_name VARCHAR NOT NULL,
    skill_path VARCHAR,
    version_hash VARCHAR NOT NULL,           -- content hash (SHA-256 of SKILL.md)
    repo_root VARCHAR,
    token_count INTEGER,
    is_valid BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_run_id VARCHAR,               -- loose FK to fact_run (circular, not enforced)
    domain VARCHAR,                          -- routing: 'extraction', 'validation', etc.
    task_type VARCHAR,                       -- routing: 'structured_data_from_document', etc.
    status VARCHAR DEFAULT 'active',         -- lifecycle: 'draft', 'active', 'deprecated'
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_skill_version_hash ON dim_skill_version(version_hash);
CREATE INDEX IF NOT EXISTS idx_skill_version_name ON dim_skill_version(skill_name);

-- dim_watermark_source: what we track watermarks for
CREATE TABLE IF NOT EXISTS dim_watermark_source (
    watermark_source_key VARCHAR PRIMARY KEY, -- deterministic hash of source_type + identifier
    source_type VARCHAR NOT NULL,             -- 'url', 'git_repo', 'file', 'timestamp'
    identifier VARCHAR NOT NULL,              -- URL, repo path, file path, etc.
    display_name VARCHAR,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- FACTS
-- ============================================================

-- fact_run: core audit table (one row per execution invocation)
CREATE TABLE IF NOT EXISTS fact_run (
    run_id VARCHAR PRIMARY KEY,
    parent_run_id VARCHAR,                    -- self-ref for orchestrator->subagent hierarchy
    correlation_id VARCHAR,                   -- groups related runs
    source_key VARCHAR,                       -- FK to dim_run_source
    run_type VARCHAR NOT NULL,                -- 'pipeline', 'agent_sdk', 'claude_code'
    run_name VARCHAR NOT NULL,
    run_description VARCHAR,

    -- source/destination
    source_type VARCHAR,
    source_identifier VARCHAR,
    destination_type VARCHAR,
    destination_identifier VARCHAR,

    -- skill lineage
    consumes_skill_version_id INTEGER,        -- FK to dim_skill_version
    produces_skill_version_id INTEGER,        -- FK to dim_skill_version

    -- execution
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_ms BIGINT,
    status VARCHAR NOT NULL DEFAULT 'running', -- 'running', 'success', 'failure', 'partial'

    -- row count equivalents
    extract_count INTEGER DEFAULT 0,
    insert_count INTEGER DEFAULT 0,
    update_count INTEGER DEFAULT 0,
    delete_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,

    -- agent-specific
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    total_cost_usd DOUBLE,
    num_turns INTEGER,
    model_name VARCHAR,

    -- CDC
    cdc_type VARCHAR,
    cdc_column VARCHAR,
    cdc_low_watermark VARCHAR,
    cdc_high_watermark VARCHAR,

    -- restartability
    is_restartable BOOLEAN DEFAULT TRUE,
    restart_from_run_id VARCHAR,

    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_run_status ON fact_run(status);
CREATE INDEX IF NOT EXISTS idx_run_type ON fact_run(run_type);
CREATE INDEX IF NOT EXISTS idx_run_started ON fact_run(started_at);
CREATE INDEX IF NOT EXISTS idx_run_parent ON fact_run(parent_run_id);
CREATE INDEX IF NOT EXISTS idx_run_correlation ON fact_run(correlation_id);

-- fact_run_message: structured log per run (ETL_MESSAGE_LOG analog)
CREATE TABLE IF NOT EXISTS fact_run_message (
    message_id INTEGER PRIMARY KEY DEFAULT nextval('seq_run_message'),
    run_id VARCHAR NOT NULL,                  -- FK to fact_run
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR NOT NULL DEFAULT 'INFO',    -- 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    category VARCHAR,
    message VARCHAR NOT NULL,
    detail VARCHAR,                           -- stack traces, extended info
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_message_run ON fact_run_message(run_id);
CREATE INDEX IF NOT EXISTS idx_message_level ON fact_run_message(level);

-- fact_watermark: watermark state history (append-only, replaces upstream_hashes.json)
CREATE TABLE IF NOT EXISTS fact_watermark (
    watermark_id INTEGER PRIMARY KEY DEFAULT nextval('seq_watermark'),
    run_id VARCHAR,                           -- FK to fact_run
    watermark_source_key VARCHAR NOT NULL,     -- FK to dim_watermark_source
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watermark_type VARCHAR,                   -- 'content_hash', 'git_sha', 'timestamp', 'etag'
    previous_value VARCHAR,
    current_value VARCHAR NOT NULL,
    changed BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_watermark_source ON fact_watermark(watermark_source_key);
CREATE INDEX IF NOT EXISTS idx_watermark_run ON fact_watermark(run_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- v_latest_watermark: current watermark per source (replaces upstream_hashes.json reads)
CREATE OR REPLACE VIEW v_latest_watermark AS
SELECT
    fw.watermark_source_key,
    dws.source_type,
    dws.identifier,
    dws.display_name,
    fw.current_value,
    fw.watermark_type,
    fw.checked_at,
    fw.run_id,
    fw.changed
FROM fact_watermark fw
JOIN dim_watermark_source dws ON fw.watermark_source_key = dws.watermark_source_key
WHERE fw.watermark_id = (
    SELECT MAX(fw2.watermark_id)
    FROM fact_watermark fw2
    WHERE fw2.watermark_source_key = fw.watermark_source_key
);

-- v_run_tree: recursive CTE for hierarchical run display
CREATE OR REPLACE VIEW v_run_tree AS
WITH RECURSIVE tree AS (
    SELECT
        run_id, parent_run_id, correlation_id,
        run_type, run_name, status, started_at, ended_at, duration_ms,
        0 AS depth
    FROM fact_run
    WHERE parent_run_id IS NULL
    UNION ALL
    SELECT
        r.run_id, r.parent_run_id, r.correlation_id,
        r.run_type, r.run_name, r.status, r.started_at, r.ended_at, r.duration_ms,
        t.depth + 1
    FROM fact_run r
    JOIN tree t ON r.parent_run_id = t.run_id
)
SELECT * FROM tree
ORDER BY started_at;

-- v_flywheel: joins producer runs -> skill versions -> consumer runs
CREATE OR REPLACE VIEW v_flywheel AS
SELECT
    producer.run_id AS producer_run_id,
    producer.run_name AS producer_name,
    producer.run_type AS producer_type,
    producer.status AS producer_status,
    producer.ended_at AS produced_at,
    sv.skill_version_id,
    sv.skill_name,
    sv.version_hash,
    sv.token_count,
    consumer.run_id AS consumer_run_id,
    consumer.run_name AS consumer_name,
    consumer.run_type AS consumer_type,
    consumer.status AS consumer_status,
    consumer.started_at AS consumed_at
FROM dim_skill_version sv
LEFT JOIN fact_run producer ON sv.created_by_run_id = producer.run_id
LEFT JOIN fact_run consumer ON consumer.consumes_skill_version_id = sv.skill_version_id;

-- v_restartable_failures: failed runs eligible for retry
CREATE OR REPLACE VIEW v_restartable_failures AS
SELECT
    f.run_id,
    f.run_name,
    f.run_type,
    f.status,
    f.started_at,
    f.ended_at,
    f.error_count,
    f.cdc_low_watermark,
    f.cdc_high_watermark,
    f.metadata
FROM fact_run f
WHERE f.status = 'failure'
  AND f.is_restartable = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM fact_run retry
      WHERE retry.restart_from_run_id = f.run_id
        AND retry.status = 'success'
  );

-- ============================================================
-- MIGRATIONS
-- ============================================================

-- v1 -> v2: add routing metadata + lifecycle to dim_skill_version
ALTER TABLE dim_skill_version ADD COLUMN IF NOT EXISTS domain VARCHAR;
ALTER TABLE dim_skill_version ADD COLUMN IF NOT EXISTS task_type VARCHAR;
ALTER TABLE dim_skill_version ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active';

INSERT INTO meta_schema_version (version, description)
SELECT 2, 'Add domain, task_type, status to dim_skill_version'
WHERE NOT EXISTS (SELECT 1 FROM meta_schema_version WHERE version = 2);

CREATE INDEX IF NOT EXISTS idx_skill_version_domain ON dim_skill_version(domain);
CREATE INDEX IF NOT EXISTS idx_skill_version_task_type ON dim_skill_version(task_type);
CREATE INDEX IF NOT EXISTS idx_skill_version_status ON dim_skill_version(status);
