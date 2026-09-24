"""Tests that document and highlight search actually rank by BM25.

Both search methods used to call `match_bm25` as a table function
(`FROM fts_main_<table>.match_bm25(id, ?) fts`). DuckDB's FTS extension
defines it as a scalar macro, so that query raised a CatalogException on
every call and each search silently took the ILIKE fallback: no score, and
rows ordered by recency. The ascending `ORDER BY fts.score` that followed
never ran; it was also backwards, since a higher BM25 score is a better match.

Each test pins both halves: the BM25 path ran (every row carries a
non-null `score`, which the fallback never returns) and the stronger match
comes first. Deleting either test lets search regress to the fallback
without a failure, because the fallback also returns the matching rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from readwise_reader.storage.database import Database


def _fts_ready(db: Database, table: str) -> bool:
    """True when the FTS index for `table` was built (the extension loaded)."""
    row = db.conn.execute(
        "SELECT count(*) FROM information_schema.schemata WHERE schema_name = ?",
        [f"fts_main_{table}"],
    ).fetchone()
    return bool(row and row[0])


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "search.duckdb")


def test_search_documents_ranks_stronger_match_first(db: Database) -> None:
    # Inserted weak-first so recency or insertion order cannot produce the
    # expected order by accident.
    db.upsert_document({
        "id": "weak",
        "title": "A long survey of many topics in computing",
        "summary": "one brief mention of machine learning among databases, "
        "networking, compilers, operating systems, graphics and security",
    })
    db.upsert_document({
        "id": "strong",
        "title": "Machine learning",
        "summary": "machine learning, machine learning, for machine learning people",
    })
    db.upsert_document({"id": "none", "title": "Cooking", "summary": "pasta"})
    db.rebuild_fts_indexes()
    if not _fts_ready(db, "dim_documents"):
        pytest.skip("DuckDB fts extension unavailable; BM25 ranking cannot be exercised")

    results = db.search_documents("machine learning")

    assert [r["doc_id"] for r in results] == ["strong", "weak"]
    assert all(r["score"] is not None for r in results), "ILIKE fallback ran, not BM25"
    assert results[0]["score"] > results[1]["score"]


def test_search_highlights_ranks_stronger_match_first(db: Database) -> None:
    db.upsert_document({"id": "doc1", "title": "Doc"})
    db.upsert_highlight(
        {"id": "weak", "text": "a passing note on machine learning among many unrelated "
         "remarks about databases, networking, compilers and graphics"},
        doc_id="doc1",
    )
    db.upsert_highlight(
        {"id": "strong", "text": "machine learning, machine learning, machine learning"},
        doc_id="doc1",
    )
    db.upsert_highlight({"id": "none", "text": "cooking is an art"}, doc_id="doc1")
    db.rebuild_fts_indexes()
    if not _fts_ready(db, "fact_highlights"):
        pytest.skip("DuckDB fts extension unavailable; BM25 ranking cannot be exercised")

    results = db.search_highlights("machine learning")

    assert [r["highlight_id"] for r in results] == ["strong", "weak"]
    assert all(r["score"] is not None for r in results), "ILIKE fallback ran, not BM25"
    assert results[0]["score"] > results[1]["score"]
