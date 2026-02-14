#!/usr/bin/env python3
"""
DuckDB-backed dimensional store for skill-maintainer state.

Kimball-style star schema with:
- MD5 hash surrogate keys on all dimensions (no integer sequences)
- SCD Type 2 on dimension tables (effective_from/to, is_current, hash_diff)
- No primary keys on fact tables (grain = composite dimension keys + timestamp)
- Metadata columns on all tables (record_source, session_id, inserted_at)
- Meta tables for schema versioning and load logging

The Store class is the single entry point. All CDC scripts call record_*()
to write facts and get_*() to read current state. export_state_json()
produces backward-compatible output matching the old state.json format.

Usage:
    from store import Store
    store = Store()  # uses default paths
    store.record_watermark_check("anthropic-skills-docs", ...)
    store.export_state_json()  # -> dict matching old format

    # CLI: query history
    uv run python skill-maintainer/scripts/store.py --history 30
"""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import orjson
import yaml


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")

SCHEMA_VERSION = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(*natural_keys) -> str:
    """MD5 surrogate key from natural key components. Kimball-style."""
    parts = [str(k) if k is not None else "-1" for k in natural_keys]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


def _hash_diff(**attributes) -> str:
    """MD5 of non-key attributes for SCD Type 2 change detection."""
    parts = [f"{k}={v}" for k, v in sorted(attributes.items()) if v is not None]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Schema DDL (v2: Kimball dimensional model)
# ---------------------------------------------------------------------------

_SCHEMA_DDL = """
-- Dimensions (SCD Type 2)

CREATE TABLE IF NOT EXISTS dim_source (
    hash_key         TEXT NOT NULL,
    source_name      TEXT NOT NULL,
    source_type      TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS dim_page (
    hash_key         TEXT NOT NULL,
    source_key       TEXT NOT NULL,
    url              TEXT NOT NULL,
    effective_from   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    effective_to     TIMESTAMP,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE,
    hash_diff        TEXT,
    record_source    TEXT NOT NULL DEFAULT 'config_sync',
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    session_id       TEXT,
    last_verified_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_source_dep (
    skill_key        TEXT NOT NULL,
    source_key       TEXT NOT NULL,
    effective_from   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    effective_to     TIMESTAMP,
    is_current       BOOLEAN NOT NULL DEFAULT TRUE,
    record_source    TEXT NOT NULL DEFAULT 'config_sync',
    created_at       TIMESTAMP NOT NULL DEFAULT current_timestamp
);

-- Facts (no PKs, no sequences)

CREATE TABLE IF NOT EXISTS fact_watermark_check (
    source_key       TEXT NOT NULL,
    checked_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    last_modified    TEXT,
    etag             TEXT,
    changed          BOOLEAN NOT NULL,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'docs_monitor',
    session_id       TEXT
);

CREATE TABLE IF NOT EXISTS fact_change (
    source_key       TEXT NOT NULL,
    page_key         TEXT,
    detected_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    classification   TEXT NOT NULL,
    old_hash         TEXT,
    new_hash         TEXT,
    summary          TEXT,
    content_preview  TEXT,
    commit_hash      TEXT,
    commit_count     INTEGER,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL,
    session_id       TEXT
);

CREATE TABLE IF NOT EXISTS fact_validation (
    skill_key        TEXT NOT NULL,
    validated_at     TIMESTAMP NOT NULL DEFAULT current_timestamp,
    is_valid         BOOLEAN NOT NULL,
    error_count      INTEGER DEFAULT 0,
    warning_count    INTEGER DEFAULT 0,
    errors           TEXT,
    warnings         TEXT,
    trigger_type     TEXT,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'validate_skill',
    session_id       TEXT
);

CREATE TABLE IF NOT EXISTS fact_update_attempt (
    skill_key        TEXT NOT NULL,
    attempted_at     TIMESTAMP NOT NULL DEFAULT current_timestamp,
    mode             TEXT,
    status           TEXT,
    changes_applied  INTEGER DEFAULT 0,
    backup_path      TEXT,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'apply_updates',
    session_id       TEXT
);

CREATE TABLE IF NOT EXISTS fact_content_measurement (
    skill_key        TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    file_type        TEXT NOT NULL,
    measured_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    line_count       INTEGER,
    word_count       INTEGER,
    char_count       INTEGER,
    estimated_tokens INTEGER,
    content_hash     TEXT,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'measure_content',
    session_id       TEXT
);

CREATE TABLE IF NOT EXISTS fact_session_event (
    session_id       TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    event_at         TIMESTAMP NOT NULL DEFAULT current_timestamp,
    target_path      TEXT,
    metadata         TEXT,
    started_at       TIMESTAMP,
    ended_at         TIMESTAMP,
    working_dir      TEXT,
    inserted_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    record_source    TEXT NOT NULL DEFAULT 'journal',
    _session_id      TEXT
);

-- Meta

CREATE TABLE IF NOT EXISTS meta_schema_version (
    version          INTEGER NOT NULL,
    applied_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    description      TEXT
);

CREATE TABLE IF NOT EXISTS meta_load_log (
    script_name      TEXT NOT NULL,
    started_at       TIMESTAMP NOT NULL DEFAULT current_timestamp,
    completed_at     TIMESTAMP,
    rows_inserted    INTEGER DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'running',
    error_message    TEXT,
    session_id       TEXT
);

-- Views (filter to is_current = TRUE on dimension joins, use hash keys)

CREATE OR REPLACE VIEW v_latest_watermark AS
SELECT source_key, checked_at, last_modified, etag, changed
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY source_key ORDER BY checked_at DESC) AS rn
    FROM fact_watermark_check
)
WHERE rn = 1;

CREATE OR REPLACE VIEW v_latest_page_hash AS
SELECT page_key, detected_at, new_hash AS current_hash, content_preview
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY page_key ORDER BY detected_at DESC) AS rn
    FROM fact_change
    WHERE page_key IS NOT NULL
)
WHERE rn = 1;

CREATE OR REPLACE VIEW v_skill_freshness AS
SELECT
    s.skill_name,
    s.skill_path,
    MAX(fc.detected_at) AS last_change_detected,
    MAX(fv.validated_at) AS last_validated,
    COALESCE(SUM(CASE WHEN fc.classification = 'BREAKING' THEN 1 ELSE 0 END), 0) AS breaking_count,
    COALESCE(SUM(CASE WHEN fc.classification = 'ADDITIVE' THEN 1 ELSE 0 END), 0) AS additive_count
FROM dim_skill s
LEFT JOIN skill_source_dep ssd ON ssd.skill_key = s.hash_key AND ssd.is_current = TRUE
LEFT JOIN fact_change fc ON fc.source_key = ssd.source_key
LEFT JOIN fact_validation fv ON fv.skill_key = s.hash_key
WHERE s.is_current = TRUE
GROUP BY s.skill_name, s.skill_path;

CREATE OR REPLACE VIEW v_skill_budget AS
SELECT
    s.skill_name,
    COALESCE(SUM(CASE WHEN m.file_type = 'skill_md' THEN m.estimated_tokens ELSE 0 END), 0) AS skill_md_tokens,
    COALESCE(SUM(CASE WHEN m.file_type = 'reference' THEN m.estimated_tokens ELSE 0 END), 0) AS reference_tokens,
    COALESCE(SUM(m.estimated_tokens), 0) AS total_tokens,
    COALESCE(SUM(m.estimated_tokens), 0) > 4000 AS over_budget
FROM dim_skill s
LEFT JOIN (
    SELECT skill_key, file_path, file_type, estimated_tokens
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY skill_key, file_path ORDER BY measured_at DESC) AS rn
        FROM fact_content_measurement
    )
    WHERE rn = 1
) m ON m.skill_key = s.hash_key
WHERE s.is_current = TRUE
GROUP BY s.skill_name;

CREATE OR REPLACE VIEW v_latest_source_check AS
SELECT source_key, detected_at AS last_checked, commit_hash, commit_count
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY source_key ORDER BY detected_at DESC) AS rn
    FROM fact_change
    WHERE commit_hash IS NOT NULL
)
WHERE rn = 1;

-- Token budget trend: shows how skill token counts change over time.
-- Enables meta-cognition: "Am I getting fatter over time?"
CREATE OR REPLACE VIEW v_skill_budget_trend AS
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
"""


class Store:
    """DuckDB-backed Kimball dimensional store for skill-maintainer."""

    def __init__(
        self,
        db_path: Path = DEFAULT_DB,
        config_path: Path = DEFAULT_CONFIG,
    ):
        self.db_path = db_path
        self.config_path = config_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(db_path))
        self._init_schema()
        self._sync_dimensions()

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Schema initialization and migration
    # ------------------------------------------------------------------

    def _init_schema(self):
        """Create tables and views. Handle schema migration."""
        # Check if meta_schema_version exists
        tables = self.con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        if "meta_schema_version" in table_names:
            row = self.con.execute(
                "SELECT MAX(version) FROM meta_schema_version"
            ).fetchone()
            current_version = row[0] if row and row[0] else 0
        else:
            current_version = 0

        if current_version < SCHEMA_VERSION:
            # Drop old v1 schema objects if they exist
            if current_version == 0 and table_names:
                self._drop_v1_schema(table_names)

            # Create v2 schema
            self.con.execute(_SCHEMA_DDL)

            # Record schema version
            self.con.execute(
                "INSERT INTO meta_schema_version (version, description) VALUES (?, ?)",
                [SCHEMA_VERSION, "Kimball dimensional model: hash keys, SCD Type 2, no fact PKs"],
            )

    def _drop_v1_schema(self, table_names: set):
        """Drop v1 schema objects (integer PKs, sequences, FK constraints)."""
        # Drop views first (depend on tables)
        for view in [
            "v_latest_watermark", "v_latest_page_hash", "v_skill_freshness",
            "v_skill_budget", "v_skill_budget_trend", "v_latest_source_check",
        ]:
            self.con.execute(f"DROP VIEW IF EXISTS {view}")

        # Drop tables
        for table in [
            "fact_session_event", "fact_session", "fact_content_measurement",
            "fact_update_attempt", "fact_validation", "fact_change",
            "fact_watermark_check", "skill_source_dep", "dim_page",
            "dim_skill", "dim_source",
        ]:
            if table in table_names:
                self.con.execute(f"DROP TABLE IF EXISTS {table}")

        # Drop sequences
        for seq in [
            "seq_watermark", "seq_change", "seq_validation",
            "seq_update", "seq_measurement", "seq_event",
        ]:
            self.con.execute(f"DROP SEQUENCE IF EXISTS {seq}")

    # ------------------------------------------------------------------
    # Dimension sync (idempotent, from config.yaml) with SCD Type 2
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def _sync_dimensions(self):
        """Populate/update dimension tables from config.yaml with SCD Type 2."""
        config = self._load_config()

        # Sources
        for name, src in config.get("sources", {}).items():
            url = src.get("llms_full_url") or src.get("repo") or src.get("hash_file", "")
            source_type = src.get("type", "docs")
            hk = _hash_key(name)
            diff = _hash_diff(source_type=source_type, url=url)

            existing = self.con.execute(
                "SELECT hash_diff FROM dim_source WHERE hash_key = ? AND is_current = TRUE",
                [hk],
            ).fetchone()

            if existing:
                if existing[0] != diff:
                    # SCD Type 2: close old row, open new
                    self.con.execute(
                        "UPDATE dim_source SET effective_to = current_timestamp, is_current = FALSE "
                        "WHERE hash_key = ? AND is_current = TRUE",
                        [hk],
                    )
                    self.con.execute(
                        "INSERT INTO dim_source (hash_key, source_name, source_type, url, hash_diff, "
                        "record_source) VALUES (?, ?, ?, ?, ?, 'config_sync')",
                        [hk, name, source_type, url, diff],
                    )
                else:
                    # Touch last_verified_at
                    self.con.execute(
                        "UPDATE dim_source SET last_verified_at = current_timestamp "
                        "WHERE hash_key = ? AND is_current = TRUE",
                        [hk],
                    )
            else:
                self.con.execute(
                    "INSERT INTO dim_source (hash_key, source_name, source_type, url, hash_diff, "
                    "record_source) VALUES (?, ?, ?, ?, ?, 'config_sync')",
                    [hk, name, source_type, url, diff],
                )

            # Pages (for docs sources with watched pages)
            if src.get("type") == "docs" and src.get("pages"):
                source_key = hk
                for page_url in src["pages"]:
                    self._ensure_page(source_key, page_url)

        # Skills
        for name, skill in config.get("skills", {}).items():
            skill_path = skill.get("path", "")
            auto_update = skill.get("auto_update", False)
            hk = _hash_key(name)
            diff = _hash_diff(skill_path=skill_path, auto_update=str(auto_update))

            existing = self.con.execute(
                "SELECT hash_diff FROM dim_skill WHERE hash_key = ? AND is_current = TRUE",
                [hk],
            ).fetchone()

            if existing:
                if existing[0] != diff:
                    self.con.execute(
                        "UPDATE dim_skill SET effective_to = current_timestamp, is_current = FALSE "
                        "WHERE hash_key = ? AND is_current = TRUE",
                        [hk],
                    )
                    self.con.execute(
                        "INSERT INTO dim_skill (hash_key, skill_name, skill_path, auto_update, "
                        "hash_diff, record_source) VALUES (?, ?, ?, ?, ?, 'config_sync')",
                        [hk, name, skill_path, auto_update, diff],
                    )
                else:
                    self.con.execute(
                        "UPDATE dim_skill SET last_verified_at = current_timestamp "
                        "WHERE hash_key = ? AND is_current = TRUE",
                        [hk],
                    )
            else:
                self.con.execute(
                    "INSERT INTO dim_skill (hash_key, skill_name, skill_path, auto_update, "
                    "hash_diff, record_source) VALUES (?, ?, ?, ?, ?, 'config_sync')",
                    [hk, name, skill_path, auto_update, diff],
                )

        # Skill-source dependencies
        for skill_name, skill in config.get("skills", {}).items():
            skill_key = _hash_key(skill_name)
            for source_name in skill.get("sources", []):
                source_key = _hash_key(source_name)
                existing = self.con.execute(
                    "SELECT 1 FROM skill_source_dep WHERE skill_key = ? AND source_key = ? "
                    "AND is_current = TRUE",
                    [skill_key, source_key],
                ).fetchone()
                if not existing:
                    self.con.execute(
                        "INSERT INTO skill_source_dep (skill_key, source_key, record_source) "
                        "VALUES (?, ?, 'config_sync')",
                        [skill_key, source_key],
                    )

    def _ensure_page(self, source_key: str, page_url: str) -> str:
        """Ensure a page dimension row exists. Returns hash_key."""
        hk = _hash_key(source_key, page_url)
        existing = self.con.execute(
            "SELECT 1 FROM dim_page WHERE hash_key = ? AND is_current = TRUE",
            [hk],
        ).fetchone()
        if not existing:
            self.con.execute(
                "INSERT INTO dim_page (hash_key, source_key, url, record_source) "
                "VALUES (?, ?, ?, 'config_sync')",
                [hk, source_key, page_url],
            )
        return hk

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _get_source_key(self, name: str) -> str | None:
        """Get hash_key for a source by name (current row only)."""
        row = self.con.execute(
            "SELECT hash_key FROM dim_source WHERE source_name = ? AND is_current = TRUE",
            [name],
        ).fetchone()
        return row[0] if row else None

    def _get_skill_key(self, name: str) -> str | None:
        """Get hash_key for a skill by name (current row only)."""
        row = self.con.execute(
            "SELECT hash_key FROM dim_skill WHERE skill_name = ? AND is_current = TRUE",
            [name],
        ).fetchone()
        return row[0] if row else None

    def _get_page_key(self, source_key: str, url: str) -> str | None:
        """Get hash_key for a page by source_key + url (current row only)."""
        hk = _hash_key(source_key, url)
        row = self.con.execute(
            "SELECT hash_key FROM dim_page WHERE hash_key = ? AND is_current = TRUE",
            [hk],
        ).fetchone()
        return row[0] if row else None

    def _get_or_create_page_key(self, source_key: str, url: str) -> str:
        """Get or create a page dimension row. Returns hash_key."""
        return self._ensure_page(source_key, url)

    # ------------------------------------------------------------------
    # Record methods (write facts)
    # ------------------------------------------------------------------

    def record_watermark_check(
        self,
        source_name: str,
        last_modified: str,
        etag: str,
        changed: bool,
        record_source: str = "docs_monitor",
        session_id: str | None = None,
    ) -> None:
        """Record a CDC detect-layer watermark check."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            raise ValueError(f"Unknown source: {source_name}")
        self.con.execute(
            """INSERT INTO fact_watermark_check
               (source_key, last_modified, etag, changed, record_source, session_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [source_key, last_modified, etag, changed, record_source, session_id],
        )

    def record_change(
        self,
        source_name: str,
        classification: str,
        old_hash: str = "",
        new_hash: str = "",
        summary: str = "",
        content_preview: str = "",
        page_url: str | None = None,
        commit_hash: str | None = None,
        commit_count: int | None = None,
        record_source: str = "docs_monitor",
        session_id: str | None = None,
    ) -> None:
        """Record a detected change (docs page or source commit)."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            raise ValueError(f"Unknown source: {source_name}")

        page_key = None
        if page_url:
            page_key = self._get_or_create_page_key(source_key, page_url)

        self.con.execute(
            """INSERT INTO fact_change
               (source_key, page_key, classification, old_hash, new_hash,
                summary, content_preview, commit_hash, commit_count,
                record_source, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [source_key, page_key, classification, old_hash, new_hash,
             summary, content_preview[:3000] if content_preview else "",
             commit_hash, commit_count, record_source, session_id],
        )

    def record_validation(
        self,
        skill_name: str,
        is_valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        trigger_type: str = "manual",
        record_source: str = "validate_skill",
        session_id: str | None = None,
    ) -> None:
        """Record a skill validation run."""
        skill_key = self._get_skill_key(skill_name)
        if skill_key is None:
            raise ValueError(f"Unknown skill: {skill_name}")
        errors = errors or []
        warnings = warnings or []
        self.con.execute(
            """INSERT INTO fact_validation
               (skill_key, is_valid, error_count, warning_count, errors, warnings,
                trigger_type, record_source, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [skill_key, is_valid, len(errors), len(warnings),
             orjson.dumps(errors).decode(), orjson.dumps(warnings).decode(),
             trigger_type, record_source, session_id],
        )

    def record_update_attempt(
        self,
        skill_name: str,
        mode: str,
        status: str = "pending_review",
        changes_applied: int = 0,
        backup_path: str = "",
        record_source: str = "apply_updates",
        session_id: str | None = None,
    ) -> None:
        """Record a skill update attempt."""
        skill_key = self._get_skill_key(skill_name)
        if skill_key is None:
            raise ValueError(f"Unknown skill: {skill_name}")
        self.con.execute(
            """INSERT INTO fact_update_attempt
               (skill_key, mode, status, changes_applied, backup_path,
                record_source, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [skill_key, mode, status, changes_applied, backup_path,
             record_source, session_id],
        )

    def record_content_measurement(
        self,
        skill_name: str,
        file_path: str,
        file_type: str,
        line_count: int,
        word_count: int,
        char_count: int,
        content_hash: str,
        record_source: str = "measure_content",
        session_id: str | None = None,
    ) -> None:
        """Record a content size measurement for token budgeting."""
        skill_key = self._get_skill_key(skill_name)
        if skill_key is None:
            raise ValueError(f"Unknown skill: {skill_name}")
        estimated_tokens = char_count // 4  # rough estimate
        self.con.execute(
            """INSERT INTO fact_content_measurement
               (skill_key, file_path, file_type, line_count, word_count,
                char_count, estimated_tokens, content_hash, record_source, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [skill_key, file_path, file_type, line_count, word_count,
             char_count, estimated_tokens, content_hash, record_source, session_id],
        )

    def record_session_event(
        self,
        session_id: str,
        event_type: str,
        target_path: str = "",
        metadata: dict | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
        working_dir: str | None = None,
        record_source: str = "journal",
        capturing_session_id: str | None = None,
    ) -> None:
        """Record a session event.

        Session boundaries are events (event_type='session_start'/'session_end'),
        not a separate table.
        """
        meta_json = orjson.dumps(metadata).decode() if metadata else ""
        self.con.execute(
            """INSERT INTO fact_session_event
               (session_id, event_type, target_path, metadata,
                started_at, ended_at, working_dir,
                record_source, _session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [session_id, event_type, target_path, meta_json,
             started_at, ended_at, working_dir,
             record_source, capturing_session_id],
        )

    def record_session_start(self, session_id: str, working_dir: str = "") -> None:
        """Record the start of a Claude Code session as an event."""
        self.record_session_event(
            session_id=session_id,
            event_type="session_start",
            working_dir=working_dir,
            record_source="journal",
        )

    def record_session_end(self, session_id: str) -> None:
        """Record the end of a Claude Code session as an event."""
        self.record_session_event(
            session_id=session_id,
            event_type="session_end",
            record_source="journal",
        )

    # ------------------------------------------------------------------
    # Meta: load logging
    # ------------------------------------------------------------------

    def log_load_start(self, script_name: str, session_id: str | None = None) -> None:
        """Record the start of a script execution."""
        self.con.execute(
            "INSERT INTO meta_load_log (script_name, session_id) VALUES (?, ?)",
            [script_name, session_id],
        )

    def log_load_end(
        self,
        script_name: str,
        rows_inserted: int = 0,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        """Update the most recent load log entry for this script."""
        self.con.execute(
            """UPDATE meta_load_log SET
                completed_at = current_timestamp,
                rows_inserted = ?,
                status = ?,
                error_message = ?
               WHERE script_name = ?
               AND completed_at IS NULL
               AND status = 'running'""",
            [rows_inserted, status, error_message, script_name],
        )

    # ------------------------------------------------------------------
    # Get methods (read current state)
    # ------------------------------------------------------------------

    def get_latest_watermark(self, source_name: str) -> dict | None:
        """Get the most recent watermark check for a source."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return None
        row = self.con.execute(
            """SELECT checked_at, last_modified, etag, changed
               FROM v_latest_watermark WHERE source_key = ?""",
            [source_key],
        ).fetchone()
        if not row:
            return None
        return {
            "last_checked": row[0].isoformat() if row[0] else "",
            "last_modified": row[1] or "",
            "etag": row[2] or "",
            "changed": row[3],
        }

    def get_latest_page_hash(self, source_name: str, page_url: str) -> dict | None:
        """Get the most recent hash for a specific page."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return None
        page_key = self._get_page_key(source_key, page_url)
        if page_key is None:
            return None
        row = self.con.execute(
            """SELECT detected_at, current_hash, content_preview
               FROM v_latest_page_hash WHERE page_key = ?""",
            [page_key],
        ).fetchone()
        if not row:
            return None
        return {
            "last_changed": row[0].isoformat() if row[0] else "",
            "hash": row[1] or "",
            "content_preview": row[2] or "",
        }

    def get_all_page_hashes(self, source_name: str) -> dict:
        """Get all latest page hashes for a source. Returns {url: {hash, ...}}."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return {}
        rows = self.con.execute(
            """SELECT p.url, v.detected_at, v.current_hash, v.content_preview
               FROM v_latest_page_hash v
               JOIN dim_page p ON p.hash_key = v.page_key AND p.is_current = TRUE
               WHERE p.source_key = ?""",
            [source_key],
        ).fetchall()
        result = {}
        for url, detected_at, hash_val, preview in rows:
            result[url] = {
                "hash": hash_val or "",
                "content_preview": preview or "",
                "last_changed": detected_at.isoformat() if detected_at else "",
            }
        return result

    def get_skill_freshness(self, skill_name: str | None = None) -> list[dict]:
        """Get freshness data for one or all skills."""
        if skill_name:
            rows = self.con.execute(
                "SELECT * FROM v_skill_freshness WHERE skill_name = ?",
                [skill_name],
            ).fetchall()
        else:
            rows = self.con.execute("SELECT * FROM v_skill_freshness").fetchall()

        results = []
        for row in rows:
            results.append({
                "skill_name": row[0],
                "skill_path": row[1],
                "last_change_detected": row[2].isoformat() if row[2] else None,
                "last_validated": row[3].isoformat() if row[3] else None,
                "breaking_count": row[4],
                "additive_count": row[5],
            })
        return results

    def get_skill_budget(self, skill_name: str | None = None) -> list[dict]:
        """Get token budget data for one or all skills."""
        if skill_name:
            rows = self.con.execute(
                "SELECT * FROM v_skill_budget WHERE skill_name = ?",
                [skill_name],
            ).fetchall()
        else:
            rows = self.con.execute("SELECT * FROM v_skill_budget").fetchall()

        results = []
        for row in rows:
            results.append({
                "skill_name": row[0],
                "skill_md_tokens": row[1],
                "reference_tokens": row[2],
                "total_tokens": row[3],
                "over_budget": row[4],
            })
        return results

    def get_skill_budget_trend(self, skill_name: str | None = None) -> list[dict]:
        """Get token budget trend over time. Enables meta-cognition: is a skill growing?"""
        if skill_name:
            rows = self.con.execute(
                "SELECT * FROM v_skill_budget_trend WHERE skill_name = ?",
                [skill_name],
            ).fetchall()
        else:
            rows = self.con.execute("SELECT * FROM v_skill_budget_trend").fetchall()

        results = []
        for row in rows:
            results.append({
                "skill_name": row[0],
                "measured_date": row[1].isoformat() if row[1] else None,
                "total_tokens": row[2],
                "skill_md_tokens": row[3],
                "reference_tokens": row[4],
                "file_count": row[5],
            })
        return results

    def get_recent_changes(self, days: int = 30, classification: str | None = None) -> list[dict]:
        """Get recent changes, optionally filtered by classification."""
        params: list = [days]
        query = """
            SELECT fc.detected_at, ds.source_name, dp.url AS page_url,
                   fc.classification, fc.summary, fc.old_hash, fc.new_hash,
                   fc.commit_hash, fc.commit_count
            FROM fact_change fc
            JOIN dim_source ds ON ds.hash_key = fc.source_key AND ds.is_current = TRUE
            LEFT JOIN dim_page dp ON dp.hash_key = fc.page_key AND dp.is_current = TRUE
            WHERE fc.detected_at >= current_timestamp - INTERVAL (? || ' days')
        """
        if classification:
            query += " AND fc.classification = ?"
            params.append(classification)
        query += " ORDER BY fc.detected_at DESC"

        rows = self.con.execute(query, params).fetchall()
        results = []
        for row in rows:
            results.append({
                "detected_at": row[0].isoformat() if row[0] else "",
                "source_name": row[1],
                "page_url": row[2] or "",
                "classification": row[3],
                "summary": row[4] or "",
                "old_hash": row[5] or "",
                "new_hash": row[6] or "",
                "commit_hash": row[7] or "",
                "commit_count": row[8],
            })
        return results

    def get_recent_validations(self, skill_name: str | None = None, limit: int = 10) -> list[dict]:
        """Get recent validation results."""
        params: list = []
        query = """
            SELECT fv.validated_at, ds.skill_name, fv.is_valid,
                   fv.error_count, fv.warning_count, fv.trigger_type
            FROM fact_validation fv
            JOIN dim_skill ds ON ds.hash_key = fv.skill_key AND ds.is_current = TRUE
        """
        if skill_name:
            query += " WHERE ds.skill_name = ?"
            params.append(skill_name)
        query += " ORDER BY fv.validated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.con.execute(query, params).fetchall()
        results = []
        for row in rows:
            results.append({
                "validated_at": row[0].isoformat() if row[0] else "",
                "skill_name": row[1],
                "is_valid": row[2],
                "error_count": row[3],
                "warning_count": row[4],
                "trigger_type": row[5] or "",
            })
        return results

    def get_latest_source_check(self, source_name: str) -> dict | None:
        """Get the latest source (git) check result."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return None
        row = self.con.execute(
            """SELECT last_checked, commit_hash, commit_count
               FROM v_latest_source_check WHERE source_key = ?""",
            [source_key],
        ).fetchone()
        if not row:
            return None
        return {
            "last_checked": row[0].isoformat() if row[0] else "",
            "last_commit": row[1] or "",
            "commits_since_last": row[2] or 0,
        }

    def get_latest_watermark_checked_at(self, source_name: str) -> str | None:
        """Get timestamp of last watermark check for a source (for freshness)."""
        wm = self.get_latest_watermark(source_name)
        if wm:
            return wm.get("last_checked")
        return None

    def get_latest_page_checked_at(self, source_name: str) -> str | None:
        """Get the most recent page check timestamp for a source."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return None
        row = self.con.execute(
            """SELECT MAX(fc.detected_at)
               FROM fact_change fc
               JOIN dim_page p ON p.hash_key = fc.page_key AND p.is_current = TRUE
               WHERE p.source_key = ?""",
            [source_key],
        ).fetchone()
        if row and row[0]:
            return row[0].isoformat()
        return None

    def get_file_hash(self, source_name: str) -> dict | None:
        """Get latest local file hash for a source (e.g., PDF hash_file)."""
        source_key = self._get_source_key(source_name)
        if source_key is None:
            return None
        # Local file changes have no page_key
        row = self.con.execute(
            """SELECT detected_at, new_hash
               FROM fact_change
               WHERE source_key = ? AND page_key IS NULL
               ORDER BY detected_at DESC LIMIT 1""",
            [source_key],
        ).fetchone()
        if not row:
            return None
        return {
            "hash": row[1] or "",
            "last_checked": row[0].isoformat() if row[0] else "",
        }

    # ------------------------------------------------------------------
    # Export: backward-compatible state.json
    # ------------------------------------------------------------------

    def export_state_json(self) -> dict:
        """Export current DB state as a dict matching the old state.json format."""
        state: dict = {}

        # Docs sources
        docs_sources = self.con.execute(
            "SELECT hash_key, source_name FROM dim_source "
            "WHERE source_type = 'docs' AND is_current = TRUE"
        ).fetchall()

        if docs_sources:
            state["docs"] = {}
            for source_key, source_name in docs_sources:
                source_state: dict = {}

                # Watermark
                wm = self.get_latest_watermark(source_name)
                if wm:
                    source_state["_watermark"] = {
                        "last_modified": wm["last_modified"],
                        "etag": wm["etag"],
                        "last_checked": wm["last_checked"],
                    }

                # Pages
                pages = self.get_all_page_hashes(source_name)
                if pages:
                    pages_state = {}
                    for url, pdata in pages.items():
                        wm_checked = wm["last_checked"] if wm else pdata["last_changed"]
                        pages_state[url] = {
                            "hash": pdata["hash"],
                            "content_preview": pdata["content_preview"],
                            "last_checked": wm_checked,
                            "last_changed": pdata["last_changed"],
                        }
                    source_state["_pages"] = pages_state

                # Local file hash
                fh = self.get_file_hash(source_name)
                if fh:
                    source_state["_file_hash"] = fh["hash"]
                    source_state["_file_last_checked"] = fh["last_checked"]

                if source_state:
                    state["docs"][source_name] = source_state

        # Source repos
        source_repos = self.con.execute(
            "SELECT hash_key, source_name FROM dim_source "
            "WHERE source_type = 'source' AND is_current = TRUE"
        ).fetchall()

        for source_key, source_name in source_repos:
            check = self.get_latest_source_check(source_name)
            if check:
                state.setdefault("sources", {})[source_name] = check

        return state

    def export_state_json_file(self, output_path: Path = DEFAULT_STATE) -> None:
        """Write backward-compatible state.json to disk."""
        state = self.export_state_json()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))

    # ------------------------------------------------------------------
    # Import: one-time migration from state.json
    # ------------------------------------------------------------------

    def import_state_json(self, state: dict) -> dict:
        """Import data from an existing state.json dict.

        Returns a summary dict of what was imported.
        """
        summary = {"watermarks": 0, "pages": 0, "file_hashes": 0, "source_checks": 0}

        # Import docs state
        for source_name, source_data in state.get("docs", {}).items():
            source_key = self._get_source_key(source_name)
            if source_key is None:
                continue

            # Watermark
            wm = source_data.get("_watermark", {})
            if isinstance(wm, dict) and wm.get("last_modified") is not None:
                self.con.execute(
                    """INSERT INTO fact_watermark_check
                       (source_key, checked_at, last_modified, etag, changed,
                        record_source, session_id)
                       VALUES (?, ?, ?, ?, ?, 'migrate_state', NULL)""",
                    [
                        source_key,
                        wm.get("last_checked", _now_iso()),
                        wm.get("last_modified", ""),
                        wm.get("etag", ""),
                        True,
                    ],
                )
                summary["watermarks"] += 1

            # Pages
            pages = source_data.get("_pages", {})
            if isinstance(pages, dict):
                for page_url, page_data in pages.items():
                    if not isinstance(page_data, dict):
                        continue
                    page_key = self._get_or_create_page_key(source_key, page_url)
                    page_hash = page_data.get("hash", "")
                    if page_hash:
                        detected_at = page_data.get("last_changed", _now_iso())
                        self.con.execute(
                            """INSERT INTO fact_change
                               (source_key, page_key, detected_at, classification,
                                old_hash, new_hash, summary, content_preview,
                                record_source, session_id)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'migrate_state', NULL)""",
                            [
                                source_key, page_key, detected_at,
                                "ADDITIVE", "", page_hash,
                                "imported from state.json",
                                page_data.get("content_preview", "")[:3000],
                            ],
                        )
                        summary["pages"] += 1

            # Local file hash
            file_hash = source_data.get("_file_hash")
            if file_hash:
                detected_at = source_data.get("_file_last_checked", _now_iso())
                self.con.execute(
                    """INSERT INTO fact_change
                       (source_key, page_key, detected_at, classification,
                        old_hash, new_hash, summary, record_source, session_id)
                       VALUES (?, NULL, ?, ?, ?, ?, ?, 'migrate_state', NULL)""",
                    [
                        source_key, detected_at,
                        "ADDITIVE", "", file_hash,
                        "imported from state.json (local file)",
                    ],
                )
                summary["file_hashes"] += 1

        # Import source repo state
        for source_name, src_data in state.get("sources", {}).items():
            if not isinstance(src_data, dict):
                continue
            source_key = self._get_source_key(source_name)
            if source_key is None:
                continue

            detected_at = src_data.get("last_checked", _now_iso())
            commit_hash = src_data.get("last_commit", "")
            commits = src_data.get("commits_since_last", 0)
            if commit_hash or commits:
                self.con.execute(
                    """INSERT INTO fact_change
                       (source_key, page_key, detected_at, classification,
                        summary, commit_hash, commit_count,
                        record_source, session_id)
                       VALUES (?, NULL, ?, ?, ?, ?, ?, 'migrate_state', NULL)""",
                    [
                        source_key, detected_at,
                        "ADDITIVE",
                        "imported from state.json (source repo)",
                        commit_hash, commits,
                    ],
                )
                summary["source_checks"] += 1

        return summary

    # ------------------------------------------------------------------
    # CLI: history query
    # ------------------------------------------------------------------

    def print_history(self, days: int = 30, classification: str | None = None) -> None:
        """Print change history to stdout."""
        changes = self.get_recent_changes(days, classification)
        if not changes:
            print(f"No changes in the last {days} days.")
            return

        print(f"# Changes in the last {days} days")
        print()
        for c in changes:
            ts = c["detected_at"][:19] if c["detected_at"] else "?"
            source = c["source_name"]
            cls = c["classification"]
            summary = c["summary"] or ""
            page = c["page_url"]
            commit = c["commit_hash"]

            target = page or (f"commit:{commit}" if commit else "")
            print(f"  {ts}  [{cls:8s}]  {source}: {target}")
            if summary:
                print(f"    {summary}")

    def print_stats(self) -> None:
        """Print database statistics."""
        tables = [
            "dim_source", "dim_skill", "dim_page", "skill_source_dep",
            "fact_watermark_check", "fact_change", "fact_validation",
            "fact_update_attempt", "fact_content_measurement",
            "fact_session_event",
            "meta_schema_version", "meta_load_log",
        ]
        print("# Store Statistics")
        print()

        # Schema version
        row = self.con.execute(
            "SELECT MAX(version) FROM meta_schema_version"
        ).fetchone()
        if row and row[0]:
            print(f"  schema_version: {row[0]}")
        print()

        for table in tables:
            try:
                row = self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = row[0] if row else 0
                if count > 0:
                    print(f"  {table}: {count} rows")
            except duckdb.CatalogException:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DuckDB dimensional store for skill-maintainer.")
    parser.add_argument(
        "--history", type=int, metavar="DAYS",
        help="Show change history for the last N days",
    )
    parser.add_argument(
        "--classification", type=str, default=None,
        help="Filter history by classification (BREAKING, ADDITIVE, COSMETIC)",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show database statistics",
    )
    parser.add_argument(
        "--export", type=Path, default=None,
        help="Export state.json to the given path",
    )
    parser.add_argument(
        "--freshness", action="store_true",
        help="Show skill freshness data",
    )
    parser.add_argument(
        "--budget", action="store_true",
        help="Show token budget data",
    )
    parser.add_argument(
        "--budget-trend", action="store_true",
        help="Show token budget trend over time (meta-cognition: is a skill growing?)",
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help=f"Database path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help=f"Config path (default: {DEFAULT_CONFIG})",
    )
    args = parser.parse_args()

    with Store(db_path=args.db, config_path=args.config) as store:
        if args.history is not None:
            store.print_history(args.history, args.classification)
        elif args.stats:
            store.print_stats()
        elif args.export:
            store.export_state_json_file(args.export)
            print(f"Exported to {args.export}", file=sys.stderr)
        elif args.freshness:
            data = store.get_skill_freshness()
            for d in data:
                name = d["skill_name"]
                last_change = d["last_change_detected"] or "never"
                last_valid = d["last_validated"] or "never"
                breaking = d["breaking_count"]
                additive = d["additive_count"]
                print(f"  {name}: last_change={last_change}, last_validated={last_valid}, "
                      f"breaking={breaking}, additive={additive}")
        elif args.budget:
            data = store.get_skill_budget()
            for d in data:
                name = d["skill_name"]
                total = d["total_tokens"]
                over = " [OVER BUDGET]" if d["over_budget"] else ""
                print(f"  {name}: {total} tokens (skill_md={d['skill_md_tokens']}, "
                      f"refs={d['reference_tokens']}){over}")
        elif args.budget_trend:
            data = store.get_skill_budget_trend()
            if not data:
                print("No budget measurements found. Run measure_content.py first.")
            else:
                current_skill = None
                for d in data:
                    if d["skill_name"] != current_skill:
                        current_skill = d["skill_name"]
                        print(f"\n  {current_skill}:")
                    date = d["measured_date"][:10] if d["measured_date"] else "?"
                    total = d["total_tokens"]
                    files = d["file_count"]
                    print(f"    {date}: {total} tokens ({files} files)")
        else:
            store.print_stats()


if __name__ == "__main__":
    main()
