"""DuckDB connection management and schema initialization."""

from __future__ import annotations

import importlib.resources
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import orjson

logger = logging.getLogger(__name__)

DEFAULT_DB_DIR = Path.home() / ".readwise-reader"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "reader.duckdb"


class Database:
    """DuckDB database for Readwise Reader data.

    Manages connection lifecycle and provides query helpers.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_file = (
            importlib.resources.files("readwise_reader.storage")
            / "schemas"
            / "reader.sql"
        )
        schema_sql = schema_file.read_text()
        self.conn.execute(schema_sql)
        self.rebuild_fts_indexes()
        logger.info("Database schema initialized at %s", self.db_path)

    def rebuild_fts_indexes(self) -> None:
        """Rebuild DuckDB FTS indexes for full-text search with BM25 scoring."""
        try:
            self.conn.execute("INSTALL fts; LOAD fts;")
            self.conn.execute(
                "PRAGMA create_fts_index("
                "'dim_documents', 'doc_id', 'title', 'summary', 'notes', 'content_html', "
                "overwrite=1);"
            )
            self.conn.execute(
                "PRAGMA create_fts_index("
                "'fact_highlights', 'highlight_id', 'content_text', 'note', "
                "overwrite=1);"
            )
            logger.debug("FTS indexes rebuilt")
        except duckdb.Error as exc:
            logger.warning("Failed to build FTS indexes (will use ILIKE fallback): %s", exc)

    def close(self) -> None:
        self.conn.close()

    # -- Document CRUD --

    def upsert_document(self, doc: dict[str, Any]) -> None:
        """Insert or update a document."""
        tags_json = orjson.dumps(doc.get("tags")).decode() if doc.get("tags") else None
        metadata_json = orjson.dumps(doc.get("metadata")).decode() if doc.get("metadata") else None
        now = datetime.now(UTC).isoformat()

        self.conn.execute(
            """
            INSERT INTO dim_documents (
                doc_id, url, title, author, category, location, summary,
                word_count, reading_progress, image_url, site_name, source_url,
                notes, published_date, content_html, content_hash, tags, v2_book_id,
                parent_id, created_in_reader, updated_in_reader, saved_at,
                first_opened_at, last_opened_at, last_moved_at, metadata, last_synced_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (doc_id) DO UPDATE SET
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                author = EXCLUDED.author,
                category = EXCLUDED.category,
                location = EXCLUDED.location,
                summary = EXCLUDED.summary,
                word_count = EXCLUDED.word_count,
                reading_progress = EXCLUDED.reading_progress,
                image_url = EXCLUDED.image_url,
                site_name = EXCLUDED.site_name,
                source_url = EXCLUDED.source_url,
                notes = EXCLUDED.notes,
                published_date = EXCLUDED.published_date,
                content_html = EXCLUDED.content_html,
                content_hash = EXCLUDED.content_hash,
                tags = EXCLUDED.tags,
                v2_book_id = COALESCE(EXCLUDED.v2_book_id, dim_documents.v2_book_id),
                parent_id = EXCLUDED.parent_id,
                created_in_reader = EXCLUDED.created_in_reader,
                updated_in_reader = EXCLUDED.updated_in_reader,
                saved_at = EXCLUDED.saved_at,
                first_opened_at = EXCLUDED.first_opened_at,
                last_opened_at = EXCLUDED.last_opened_at,
                last_moved_at = EXCLUDED.last_moved_at,
                metadata = EXCLUDED.metadata,
                last_synced_at = EXCLUDED.last_synced_at
            """,
            [
                doc.get("id"),
                doc.get("url"),
                doc.get("title"),
                doc.get("author"),
                doc.get("category"),
                doc.get("location"),
                doc.get("summary"),
                doc.get("word_count"),
                doc.get("reading_progress"),
                doc.get("image_url"),
                doc.get("site_name"),
                doc.get("source_url"),
                doc.get("notes"),
                doc.get("published_date"),
                doc.get("html_content"),
                doc.get("content_hash"),
                tags_json,
                doc.get("v2_book_id"),
                doc.get("parent_id"),
                doc.get("created_at"),
                doc.get("updated_at"),
                doc.get("saved_at"),
                doc.get("first_opened_at"),
                doc.get("last_opened_at"),
                doc.get("last_moved_at"),
                metadata_json,
                now,
            ],
        )

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get a document by ID."""
        result = self.conn.execute(
            "SELECT * FROM dim_documents WHERE doc_id = ?", [doc_id]
        ).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self.conn.description]
        return dict(zip(columns, result))

    def query_documents(
        self,
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
        since: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query documents with optional filters."""
        conditions: list[str] = []
        params: list[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)
        if location:
            conditions.append("location = ?")
            params.append(location)
        if tag:
            conditions.append("tags::VARCHAR ILIKE ?")
            params.append(f"%{tag}%")
        if since:
            conditions.append("updated_in_reader >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT doc_id, url, title, author, category, location, summary,
                   word_count, reading_progress, tags, published_date,
                   created_in_reader, updated_in_reader
            FROM dim_documents
            {where}
            ORDER BY updated_in_reader DESC NULLS LAST
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        results = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document. Returns True if a row was deleted."""
        self.conn.execute("DELETE FROM fact_highlights WHERE doc_id = ?", [doc_id])
        result = self.conn.execute(
            "DELETE FROM dim_documents WHERE doc_id = ? RETURNING doc_id", [doc_id]
        ).fetchone()
        return result is not None

    # -- ID Reconciliation (v2 <-> v3) --

    def get_doc_id_by_v2_book_id(self, v2_book_id: int) -> str | None:
        """Look up a v3 document ID by its v2 book ID."""
        result = self.conn.execute(
            "SELECT doc_id FROM dim_documents WHERE v2_book_id = ?", [v2_book_id]
        ).fetchone()
        return result[0] if result else None

    def get_doc_id_by_url(self, url: str) -> str | None:
        """Look up a document ID by source URL."""
        result = self.conn.execute(
            "SELECT doc_id FROM dim_documents WHERE source_url = ? OR url = ? LIMIT 1",
            [url, url],
        ).fetchone()
        return result[0] if result else None

    def set_v2_book_id(self, doc_id: str, v2_book_id: int) -> None:
        """Associate a v2 book ID with a v3 document."""
        self.conn.execute(
            "UPDATE dim_documents SET v2_book_id = ? WHERE doc_id = ?",
            [v2_book_id, doc_id],
        )

    def reconcile_orphaned_highlights(self) -> int:
        """Move resolved highlights from staging_highlights to fact_highlights.

        For each distinct v2:{id} doc_id in staging, looks up the real v3 document.
        If found, inserts into fact_highlights with the real doc_id and deletes from staging.
        Returns the number of highlights reconciled.
        """
        orphaned = self.conn.execute(
            "SELECT DISTINCT doc_id FROM staging_highlights WHERE doc_id LIKE 'v2:%'"
        ).fetchall()

        reconciled = 0
        for (orphaned_doc_id,) in orphaned:
            v2_id = int(orphaned_doc_id.removeprefix("v2:"))
            real_doc_id = self.get_doc_id_by_v2_book_id(v2_id)
            if real_doc_id:
                # Copy resolved highlights into fact_highlights
                moved = self.conn.execute(
                    """
                    INSERT INTO fact_highlights (
                        highlight_id, doc_id, content_text, note, color,
                        location_pointer, tags, properties, highlighted_at, embedding
                    )
                    SELECT highlight_id, ?, content_text, note, color,
                           location_pointer, tags, properties, highlighted_at, embedding
                    FROM staging_highlights
                    WHERE doc_id = ?
                    ON CONFLICT (highlight_id) DO UPDATE SET
                        doc_id = EXCLUDED.doc_id,
                        content_text = EXCLUDED.content_text,
                        note = EXCLUDED.note,
                        color = EXCLUDED.color,
                        location_pointer = EXCLUDED.location_pointer,
                        tags = EXCLUDED.tags,
                        properties = EXCLUDED.properties,
                        highlighted_at = EXCLUDED.highlighted_at
                    RETURNING highlight_id
                    """,
                    [real_doc_id, orphaned_doc_id],
                ).fetchall()
                # Remove from staging
                self.conn.execute(
                    "DELETE FROM staging_highlights WHERE doc_id = ?",
                    [orphaned_doc_id],
                )
                reconciled += len(moved)
                logger.info(
                    "Reconciled %d highlights: %s -> %s", len(moved), orphaned_doc_id, real_doc_id
                )

        return reconciled

    def search_documents(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Full-text search across documents using BM25 scoring, with ILIKE fallback."""
        try:
            results = self.conn.execute(
                """
                SELECT d.doc_id, d.url, d.title, d.author, d.category, d.location,
                       d.summary, d.word_count, d.reading_progress, d.tags, d.published_date,
                       fts.score
                FROM fts_main_dim_documents.match_bm25(doc_id, ?) fts
                JOIN dim_documents d ON d.doc_id = fts.doc_id
                ORDER BY fts.score
                LIMIT ?
                """,
                [query, limit],
            ).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except duckdb.Error:
            like_pattern = f"%{query}%"
            results = self.conn.execute(
                """
                SELECT doc_id, url, title, author, category, location, summary,
                       word_count, reading_progress, tags, published_date
                FROM dim_documents
                WHERE title ILIKE ? OR summary ILIKE ? OR notes ILIKE ?
                    OR content_html ILIKE ?
                ORDER BY updated_in_reader DESC NULLS LAST
                LIMIT ?
                """,
                [like_pattern, like_pattern, like_pattern, like_pattern, limit],
            ).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]

    # -- Highlight CRUD --

    def upsert_highlight(self, highlight: dict[str, Any], doc_id: str) -> None:
        """Insert or update a highlight.

        Routes to staging_highlights when doc_id is unresolved (v2: prefix),
        otherwise inserts directly into fact_highlights.
        """
        tags_json = (
            orjson.dumps(highlight.get("tags")).decode() if highlight.get("tags") else None
        )
        props_json = (
            orjson.dumps(highlight.get("properties")).decode()
            if highlight.get("properties")
            else None
        )
        table = "staging_highlights" if doc_id.startswith("v2:") else "fact_highlights"
        self.conn.execute(
            f"""
            INSERT INTO {table} (
                highlight_id, doc_id, content_text, note, color,
                location_pointer, tags, properties, highlighted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (highlight_id) DO UPDATE SET
                content_text = EXCLUDED.content_text,
                note = EXCLUDED.note,
                color = EXCLUDED.color,
                location_pointer = EXCLUDED.location_pointer,
                tags = EXCLUDED.tags,
                properties = EXCLUDED.properties,
                highlighted_at = EXCLUDED.highlighted_at
            """,
            [
                str(highlight.get("id")),
                doc_id,
                highlight.get("text"),
                highlight.get("note"),
                highlight.get("color"),
                str(highlight.get("location", "")),
                tags_json,
                props_json,
                highlight.get("highlighted_at"),
            ],
        )

    def get_highlights(
        self, doc_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get highlights, optionally filtered by document."""
        if doc_id:
            results = self.conn.execute(
                """
                SELECT h.*, d.title as doc_title, d.url as doc_url
                FROM fact_highlights h
                LEFT JOIN dim_documents d ON h.doc_id = d.doc_id
                WHERE h.doc_id = ?
                ORDER BY h.highlighted_at DESC NULLS LAST
                LIMIT ?
                """,
                [doc_id, limit],
            ).fetchall()
        else:
            results = self.conn.execute(
                """
                SELECT h.*, d.title as doc_title, d.url as doc_url
                FROM fact_highlights h
                LEFT JOIN dim_documents d ON h.doc_id = d.doc_id
                ORDER BY h.highlighted_at DESC NULLS LAST
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]

    def search_highlights(
        self, query: str, tag: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Full-text search across highlights using BM25 scoring, with ILIKE fallback."""
        try:
            tag_filter = ""
            params: list[Any] = [query]
            if tag:
                tag_filter = "AND h.tags::VARCHAR ILIKE ?"
                params.append(f"%{tag}%")
            params.append(limit)
            results = self.conn.execute(
                f"""
                SELECT h.*, d.title as doc_title, d.url as doc_url, fts.score
                FROM fts_main_fact_highlights.match_bm25(highlight_id, ?) fts
                JOIN fact_highlights h ON h.highlight_id = fts.highlight_id
                LEFT JOIN dim_documents d ON h.doc_id = d.doc_id
                WHERE 1=1 {tag_filter}
                ORDER BY fts.score
                LIMIT ?
                """,
                params,
            ).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]
        except duckdb.Error:
            like_pattern = f"%{query}%"
            conditions = ["(h.content_text ILIKE ? OR h.note ILIKE ?)"]
            params = [like_pattern, like_pattern]
            if tag:
                conditions.append("h.tags::VARCHAR ILIKE ?")
                params.append(f"%{tag}%")
            where = " AND ".join(conditions)
            params.append(limit)
            results = self.conn.execute(
                f"""
                SELECT h.*, d.title as doc_title, d.url as doc_url
                FROM fact_highlights h
                LEFT JOIN dim_documents d ON h.doc_id = d.doc_id
                WHERE {where}
                ORDER BY h.highlighted_at DESC NULLS LAST
                LIMIT ?
                """,
                params,
            ).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in results]

    # -- Tags --

    def upsert_tag(self, tag_key: str, tag_name: str) -> None:
        """Insert or update a tag."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            """
            INSERT INTO dim_tags (tag_key, tag_name, last_used_at)
            VALUES (?, ?, ?)
            ON CONFLICT (tag_key) DO UPDATE SET
                tag_name = EXCLUDED.tag_name,
                last_used_at = EXCLUDED.last_used_at
            """,
            [tag_key, tag_name, now],
        )

    def refresh_tag_counts(self) -> None:
        """Recompute tag usage counts from document and highlight data."""
        # This is approximate -- counts tags mentioned in JSON columns
        tags = self.conn.execute("SELECT tag_key, tag_name FROM dim_tags").fetchall()
        for tag_key, tag_name in tags:
            doc_count = self.conn.execute(
                "SELECT COUNT(*) FROM dim_documents WHERE tags::VARCHAR ILIKE ?",
                [f"%{tag_name}%"],
            ).fetchone()[0]
            highlight_count = self.conn.execute(
                "SELECT COUNT(*) FROM fact_highlights WHERE tags::VARCHAR ILIKE ?",
                [f"%{tag_name}%"],
            ).fetchone()[0]
            self.conn.execute(
                """
                UPDATE dim_tags SET doc_count = ?, highlight_count = ?
                WHERE tag_key = ?
                """,
                [doc_count, highlight_count, tag_key],
            )

    def get_all_tags(self) -> list[dict[str, Any]]:
        """Get all tags with counts."""
        results = self.conn.execute(
            "SELECT * FROM dim_tags ORDER BY doc_count DESC"
        ).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]

    # -- Sync state --

    def get_sync_value(self, key: str) -> str | None:
        """Get a sync state value."""
        result = self.conn.execute(
            "SELECT sync_value FROM sync_state WHERE sync_key = ?", [key]
        ).fetchone()
        return result[0] if result else None

    def set_sync_value(self, key: str, value: str) -> None:
        """Set a sync state value."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            """
            INSERT INTO sync_state (sync_key, sync_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (sync_key) DO UPDATE SET
                sync_value = EXCLUDED.sync_value,
                updated_at = EXCLUDED.updated_at
            """,
            [key, value, now],
        )

    # -- Audit --

    def log_change(self, doc_id: str, change_type: str, details: str = "") -> None:
        """Log an audit change."""
        self.conn.execute(
            """
            INSERT INTO audit_changes (change_id, doc_id, change_type, details)
            VALUES (nextval('seq_audit'), ?, ?, ?)
            """,
            [doc_id, change_type, details],
        )

    # -- Stats --

    def library_stats(self) -> dict[str, Any]:
        """Get library statistics."""
        stats: dict[str, Any] = {}

        # Counts by category
        rows = self.conn.execute(
            "SELECT category, COUNT(*) as cnt FROM dim_documents "
            "GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        stats["by_category"] = {row[0] or "unknown": row[1] for row in rows}

        # Counts by location
        rows = self.conn.execute(
            "SELECT location, COUNT(*) as cnt FROM dim_documents "
            "GROUP BY location ORDER BY cnt DESC"
        ).fetchall()
        stats["by_location"] = {row[0] or "unknown": row[1] for row in rows}

        # Total counts
        stats["total_documents"] = self.conn.execute(
            "SELECT COUNT(*) FROM dim_documents"
        ).fetchone()[0]
        stats["total_highlights"] = self.conn.execute(
            "SELECT COUNT(*) FROM fact_highlights"
        ).fetchone()[0]
        stats["total_tags"] = self.conn.execute(
            "SELECT COUNT(*) FROM dim_tags"
        ).fetchone()[0]

        # Inbox size
        stats["inbox_size"] = self.conn.execute(
            "SELECT COUNT(*) FROM dim_documents WHERE location = 'new'"
        ).fetchone()[0]

        # Last sync
        stats["last_sync"] = self.get_sync_value("last_full_sync")

        return stats
