"""Tests for MCP tool functions (unit tests using mocked dependencies)."""

from __future__ import annotations

from pathlib import Path

import pytest

from readwise_reader.storage.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.duckdb")


class TestSearchTools:
    """Test search operations against a real DuckDB instance."""

    def test_search_documents_empty(self, db: Database) -> None:
        results = db.search_documents("anything")
        assert results == []

    def test_search_finds_by_title(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1",
            "title": "Introduction to Rust Programming",
            "summary": "Learn Rust basics",
        })
        db.upsert_document({
            "id": "d2",
            "title": "Python Cookbook",
            "summary": "Python recipes and patterns",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("rust")
        assert len(results) == 1
        assert results[0]["doc_id"] == "d1"

    def test_search_finds_by_summary(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1",
            "title": "Some Article",
            "summary": "Deep dive into transformer architectures",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("transformer")
        assert len(results) == 1

    def test_search_case_insensitive(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1",
            "title": "Machine Learning Guide",
        })
        db.rebuild_fts_indexes()

        results = db.search_documents("machine learning")
        assert len(results) == 1

        results = db.search_documents("MACHINE LEARNING")
        assert len(results) == 1


class TestHighlightSearch:
    def test_search_highlights_by_text(self, db: Database) -> None:
        db.upsert_document({"id": "doc1", "title": "Test"})
        db.upsert_highlight({"id": "h1", "text": "Distributed systems are complex"}, doc_id="doc1")
        db.upsert_highlight({"id": "h2", "text": "Simple is better than complex"}, doc_id="doc1")
        db.rebuild_fts_indexes()

        results = db.search_highlights("distributed")
        assert len(results) == 1
        assert results[0]["highlight_id"] == "h1"

    def test_search_highlights_by_note(self, db: Database) -> None:
        db.upsert_document({"id": "doc1", "title": "Test"})
        db.upsert_highlight(
            {"id": "h1", "text": "Some text", "note": "This is about caching strategies"},
            doc_id="doc1",
        )
        db.rebuild_fts_indexes()

        results = db.search_highlights("caching")
        assert len(results) == 1


class TestTagOperations:
    def test_tag_query(self, db: Database) -> None:
        db.upsert_document({"id": "d1", "tags": {"python": {}}, "category": "article"})
        db.upsert_document({"id": "d2", "tags": {"rust": {}}, "category": "article"})
        db.upsert_document({"id": "d3", "tags": {"python": {}, "ml": {}}, "category": "pdf"})

        results = db.query_documents(tag="python")
        assert len(results) == 2

    def test_combined_filters(self, db: Database) -> None:
        db.upsert_document({
            "id": "d1", "tags": {"python": {}},
            "category": "article", "location": "new",
        })
        db.upsert_document({
            "id": "d2", "tags": {"python": {}},
            "category": "article", "location": "archive",
        })
        db.upsert_document({
            "id": "d3", "tags": {"python": {}},
            "category": "pdf", "location": "new",
        })

        results = db.query_documents(tag="python", category="article", location="new")
        assert len(results) == 1
        assert results[0]["doc_id"] == "d1"


class TestLibraryStats:
    def test_comprehensive_stats(self, db: Database) -> None:
        db.upsert_document({"id": "d1", "category": "article", "location": "new"})
        db.upsert_document({"id": "d2", "category": "article", "location": "archive"})
        db.upsert_document({"id": "d3", "category": "pdf", "location": "new"})
        db.upsert_document({"id": "d4", "category": "tweet", "location": "later"})
        db.upsert_highlight({"id": "h1", "text": "highlight"}, doc_id="d1")
        db.upsert_tag("python", "Python")

        stats = db.library_stats()
        assert stats["total_documents"] == 4
        assert stats["total_highlights"] == 1
        assert stats["total_tags"] == 1
        assert stats["inbox_size"] == 2
        assert stats["by_category"]["article"] == 2
        assert stats["by_location"]["new"] == 2
