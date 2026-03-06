"""Tests for the DuckDB storage layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from readwise_reader.storage.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create a test database in a temp directory."""
    return Database(db_path=tmp_path / "test.duckdb")


@pytest.fixture
def sample_doc() -> dict:
    return {
        "id": "doc_001",
        "url": "https://example.com/article",
        "title": "Test Article",
        "author": "Test Author",
        "category": "article",
        "location": "new",
        "summary": "A test article about testing",
        "word_count": 500,
        "reading_progress": 0.0,
        "tags": {"testing": {}, "python": {}},
    }


class TestDocumentCRUD:
    def test_upsert_and_get(self, db: Database, sample_doc: dict) -> None:
        db.upsert_document(sample_doc)
        result = db.get_document("doc_001")
        assert result is not None
        assert result["title"] == "Test Article"
        assert result["category"] == "article"

    def test_upsert_updates_existing(self, db: Database, sample_doc: dict) -> None:
        db.upsert_document(sample_doc)
        sample_doc["title"] = "Updated Title"
        db.upsert_document(sample_doc)
        result = db.get_document("doc_001")
        assert result is not None
        assert result["title"] == "Updated Title"

    def test_get_nonexistent(self, db: Database) -> None:
        result = db.get_document("nonexistent")
        assert result is None

    def test_delete(self, db: Database, sample_doc: dict) -> None:
        db.upsert_document(sample_doc)
        assert db.delete_document("doc_001") is True
        assert db.get_document("doc_001") is None

    def test_delete_nonexistent(self, db: Database) -> None:
        assert db.delete_document("nonexistent") is False


class TestDocumentQuery:
    def test_query_by_category(self, db: Database) -> None:
        db.upsert_document({"id": "d1", "category": "article", "location": "new"})
        db.upsert_document({"id": "d2", "category": "pdf", "location": "new"})
        db.upsert_document({"id": "d3", "category": "article", "location": "later"})

        results = db.query_documents(category="article")
        assert len(results) == 2

    def test_query_by_location(self, db: Database) -> None:
        db.upsert_document({"id": "d1", "category": "article", "location": "new"})
        db.upsert_document({"id": "d2", "category": "article", "location": "archive"})

        results = db.query_documents(location="new")
        assert len(results) == 1
        assert results[0]["doc_id"] == "d1"

    def test_query_with_limit(self, db: Database) -> None:
        for i in range(10):
            db.upsert_document({"id": f"d{i}", "category": "article"})

        results = db.query_documents(limit=3)
        assert len(results) == 3

    def test_search_documents(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1",
            "title": "Machine Learning Fundamentals",
            "summary": "An introduction to ML concepts",
        })
        db.upsert_document({
            "id": "d2",
            "title": "Cooking Recipes",
            "summary": "Great pasta recipes",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("machine learning")
        assert len(results) == 1
        assert results[0]["doc_id"] == "d1"


class TestHighlights:
    def test_upsert_and_get(self, db: Database) -> None:
        db.upsert_document({"id": "doc1", "title": "Test Doc"})
        db.upsert_highlight(
            {"id": "h1", "text": "Important text", "note": "My note", "color": "yellow"},
            doc_id="doc1",
        )
        results = db.get_highlights(doc_id="doc1")
        assert len(results) == 1
        assert results[0]["content_text"] == "Important text"
        assert results[0]["note"] == "My note"

    def test_search_highlights(self, db: Database) -> None:
        db.upsert_document({"id": "doc1", "title": "Test Doc"})
        db.upsert_highlight({"id": "h1", "text": "Machine learning is powerful"}, doc_id="doc1")
        db.upsert_highlight({"id": "h2", "text": "Cooking is an art"}, doc_id="doc1")
        db.rebuild_fts_indexes()

        results = db.search_highlights("machine learning")
        assert len(results) == 1
        assert results[0]["highlight_id"] == "h1"


class TestTags:
    def test_upsert_and_list(self, db: Database) -> None:
        db.upsert_tag("python", "Python")
        db.upsert_tag("ml", "Machine Learning")

        tags = db.get_all_tags()
        assert len(tags) == 2

    def test_refresh_counts(self, db: Database) -> None:
        db.upsert_tag("testing", "testing")
        db.upsert_document({"id": "d1", "tags": {"testing": {}}})
        db.refresh_tag_counts()

        tags = db.get_all_tags()
        testing_tag = next(t for t in tags if t["tag_key"] == "testing")
        assert testing_tag["doc_count"] == 1


class TestSyncState:
    def test_get_set(self, db: Database) -> None:
        assert db.get_sync_value("last_sync") is None
        db.set_sync_value("last_sync", "2025-01-01T00:00:00Z")
        assert db.get_sync_value("last_sync") == "2025-01-01T00:00:00Z"

    def test_update(self, db: Database) -> None:
        db.set_sync_value("key", "value1")
        db.set_sync_value("key", "value2")
        assert db.get_sync_value("key") == "value2"


class TestLibraryStats:
    def test_stats(self, db: Database) -> None:
        db.upsert_document({"id": "d1", "category": "article", "location": "new"})
        db.upsert_document({"id": "d2", "category": "pdf", "location": "archive"})
        db.upsert_document({"id": "d3", "category": "article", "location": "new"})

        stats = db.library_stats()
        assert stats["total_documents"] == 3
        assert stats["by_category"]["article"] == 2
        assert stats["by_location"]["new"] == 2
        assert stats["inbox_size"] == 2


class TestFTSSearch:
    def test_bm25_returns_results(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1",
            "title": "Introduction to Machine Learning",
            "summary": "A comprehensive guide to ML algorithms",
        })
        db.upsert_document({
            "id": "d2",
            "title": "Cooking with Python",
            "summary": "Recipes for data-hungry developers",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("machine learning")
        assert len(results) >= 1
        assert results[0]["doc_id"] == "d1"

    def test_bm25_relevance_ranking(self, db: Database) -> None:
        # Add a third unrelated doc to give BM25 meaningful IDF values
        db.upsert_document({
            "id": "d1",
            "title": "Cooking with fire",
            "summary": "Grilling techniques and recipes for outdoor cooking",
        })
        db.upsert_document({
            "id": "d2",
            "title": "Database Design Patterns",
            "summary": "Database normalization and database indexing for database performance",
        })
        db.upsert_document({
            "id": "d3",
            "title": "Gardening tips",
            "summary": "How to grow tomatoes in small spaces",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("database")
        # Only the doc with "database" should appear
        doc_ids = [r["doc_id"] for r in results]
        assert "d2" in doc_ids
        assert "d1" not in doc_ids
        assert "d3" not in doc_ids

    def test_highlight_fts(self, db: Database) -> None:
        db.upsert_document({"id": "doc1", "title": "Test"})
        db.upsert_highlight(
            {"id": "h1", "text": "Neural networks transform input data"}, doc_id="doc1",
        )
        db.upsert_highlight({"id": "h2", "text": "Cooking is an art form"}, doc_id="doc1")
        db.rebuild_fts_indexes()

        results = db.search_highlights("neural networks")
        assert len(results) == 1
        assert results[0]["highlight_id"] == "h1"

    def test_fts_empty_table(self, db: Database) -> None:
        db.rebuild_fts_indexes()
        results = db.search_documents("anything")
        assert results == []


class TestIDReconciliation:
    def test_get_doc_id_by_v2_book_id(self, db: Database) -> None:
        db.upsert_document({"id": "abc-123", "title": "Test", "v2_book_id": 42})
        assert db.get_doc_id_by_v2_book_id(42) == "abc-123"
        assert db.get_doc_id_by_v2_book_id(999) is None

    def test_get_doc_id_by_url(self, db: Database) -> None:
        db.upsert_document({
            "id": "abc-123",
            "url": "https://example.com/article",
            "source_url": "https://original.com/article",
        })
        assert db.get_doc_id_by_url("https://example.com/article") == "abc-123"
        assert db.get_doc_id_by_url("https://original.com/article") == "abc-123"
        assert db.get_doc_id_by_url("https://other.com") is None

    def test_set_v2_book_id(self, db: Database) -> None:
        db.upsert_document({"id": "abc-123", "title": "Test"})
        assert db.get_doc_id_by_v2_book_id(42) is None

        db.set_v2_book_id("abc-123", 42)
        assert db.get_doc_id_by_v2_book_id(42) == "abc-123"

    def test_reconcile_orphaned_highlights(self, db: Database) -> None:
        # Create a real document with a v2_book_id
        db.upsert_document({"id": "abc-123", "title": "Test", "v2_book_id": 42})

        # Insert highlights with orphaned v2: prefix doc_id -- routes to staging
        db.upsert_highlight({"id": "h1", "text": "highlight 1"}, doc_id="v2:42")
        db.upsert_highlight({"id": "h2", "text": "highlight 2"}, doc_id="v2:42")
        db.upsert_highlight({"id": "h3", "text": "unrelated"}, doc_id="v2:999")

        # Verify highlights landed in staging, not fact
        staging_count = db.conn.execute(
            "SELECT COUNT(*) FROM staging_highlights"
        ).fetchone()[0]
        assert staging_count == 3

        fact_count = db.conn.execute(
            "SELECT COUNT(*) FROM fact_highlights"
        ).fetchone()[0]
        assert fact_count == 0

        reconciled = db.reconcile_orphaned_highlights()
        assert reconciled == 2

        # Reconciled highlights moved to fact_highlights with real doc_id
        highlights = db.get_highlights(doc_id="abc-123")
        assert len(highlights) == 2

        # v2:999 still in staging (no matching document)
        orphaned = db.conn.execute(
            "SELECT doc_id FROM staging_highlights WHERE highlight_id = 'h3'"
        ).fetchone()
        assert orphaned[0] == "v2:999"

        # Staging should only have the unresolved one left
        staging_remaining = db.conn.execute(
            "SELECT COUNT(*) FROM staging_highlights"
        ).fetchone()[0]
        assert staging_remaining == 1

    def test_resolved_highlight_goes_to_fact(self, db: Database) -> None:
        # A highlight with a real doc_id goes directly to fact_highlights
        db.upsert_document({"id": "doc-real", "title": "Real Doc"})
        db.upsert_highlight({"id": "h1", "text": "good highlight"}, doc_id="doc-real")

        fact_count = db.conn.execute(
            "SELECT COUNT(*) FROM fact_highlights WHERE highlight_id = 'h1'"
        ).fetchone()[0]
        assert fact_count == 1

        staging_count = db.conn.execute(
            "SELECT COUNT(*) FROM staging_highlights"
        ).fetchone()[0]
        assert staging_count == 0


class TestAudit:
    def test_log_change(self, db: Database) -> None:
        db.log_change("doc1", "create", "test")
        db.log_change("doc1", "update", "sync")

        results = db.conn.execute(
            "SELECT * FROM audit_changes WHERE doc_id = ? ORDER BY change_id",
            ["doc1"],
        ).fetchall()
        assert len(results) == 2
