-- Readwise Reader DuckDB Schema (star schema pattern)

-- 1. DIMENSION: Documents (articles, PDFs, tweets, etc.)
CREATE TABLE IF NOT EXISTS dim_documents (
    doc_id VARCHAR PRIMARY KEY,
    url VARCHAR,
    title VARCHAR,
    author VARCHAR,
    category VARCHAR,                 -- article, email, rss, pdf, epub, tweet, video, note
    location VARCHAR,                 -- new, later, archive, feed
    summary TEXT,
    word_count INTEGER,
    reading_progress FLOAT,
    image_url VARCHAR,
    site_name VARCHAR,
    source_url VARCHAR,
    notes TEXT,
    published_date TIMESTAMP,
    content_html TEXT,
    content_hash VARCHAR,
    tags JSON,                        -- {"tag_name": {...}} mirror of Reader format
    v2_book_id INTEGER,                 -- Readwise Core v2 API book ID (for highlight reconciliation)
    parent_id VARCHAR,
    created_in_reader TIMESTAMP,
    updated_in_reader TIMESTAMP,
    saved_at TIMESTAMP,
    first_opened_at TIMESTAMP,
    last_opened_at TIMESTAMP,
    last_moved_at TIMESTAMP,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- 2. FACT: Highlights (atomic embeddable items)
CREATE TABLE IF NOT EXISTS fact_highlights (
    highlight_id VARCHAR PRIMARY KEY,
    doc_id VARCHAR REFERENCES dim_documents(doc_id),
    content_text TEXT,
    note TEXT,
    color VARCHAR,
    location_pointer VARCHAR,
    tags JSON,
    properties JSON,
    highlighted_at TIMESTAMP,
    embedding FLOAT[]                 -- Stub: for future PyLate multi-vector embeddings
);

-- 2b. STAGING: Highlights awaiting document reconciliation (no FK)
CREATE TABLE IF NOT EXISTS staging_highlights (
    highlight_id VARCHAR PRIMARY KEY,
    doc_id VARCHAR,                    -- v2:{book_id} pending reconciliation
    content_text TEXT,
    note TEXT,
    color VARCHAR,
    location_pointer VARCHAR,
    tags JSON,
    properties JSON,
    highlighted_at TIMESTAMP,
    embedding FLOAT[]
);

-- 3. DIMENSION: Tags
CREATE TABLE IF NOT EXISTS dim_tags (
    tag_key VARCHAR PRIMARY KEY,
    tag_name VARCHAR,
    doc_count INTEGER DEFAULT 0,
    highlight_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP
);

-- 4. Sync state tracking
CREATE TABLE IF NOT EXISTS sync_state (
    sync_key VARCHAR PRIMARY KEY,
    sync_value VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Audit log
CREATE TABLE IF NOT EXISTS audit_changes (
    change_id INTEGER PRIMARY KEY,
    doc_id VARCHAR,
    change_type VARCHAR,              -- 'create', 'update', 'delete', 'sync'
    details VARCHAR,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE SEQUENCE IF NOT EXISTS seq_audit START 1;

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_doc_url ON dim_documents(url);
CREATE INDEX IF NOT EXISTS idx_doc_category ON dim_documents(category);
CREATE INDEX IF NOT EXISTS idx_doc_location ON dim_documents(location);
CREATE INDEX IF NOT EXISTS idx_doc_updated ON dim_documents(updated_in_reader);
CREATE INDEX IF NOT EXISTS idx_highlight_doc ON fact_highlights(doc_id);
CREATE INDEX IF NOT EXISTS idx_staging_doc ON staging_highlights(doc_id);
CREATE INDEX IF NOT EXISTS idx_audit_doc ON audit_changes(doc_id);
CREATE INDEX IF NOT EXISTS idx_docs_v2_book_id ON dim_documents(v2_book_id);
