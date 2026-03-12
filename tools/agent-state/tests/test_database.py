"""Tests for database initialization and schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_state.database import AgentStateDB


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    """Create a fresh in-memory-like DB for each test."""
    db_path = tmp_path / "test.duckdb"
    return AgentStateDB(db_path)


def test_init_creates_tables(db: AgentStateDB) -> None:
    """Schema init creates all expected tables."""
    tables = db.fetchall(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    )
    table_names = {row[0] for row in tables}
    expected = {
        "meta_schema_version",
        "dim_run_source",
        "dim_skill_version",
        "dim_watermark_source",
        "fact_run",
        "fact_run_message",
        "fact_watermark",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"


def test_init_creates_views(db: AgentStateDB) -> None:
    """Schema init creates all expected views."""
    views = db.fetchall(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'VIEW' "
        "ORDER BY table_name"
    )
    view_names = {row[0] for row in views}
    expected = {
        "v_latest_watermark",
        "v_run_tree",
        "v_flywheel",
        "v_restartable_failures",
    }
    assert expected.issubset(view_names), f"Missing views: {expected - view_names}"


def test_schema_version(db: AgentStateDB) -> None:
    """Schema version is 1 after init."""
    assert db.schema_version() == 1


def test_idempotent_init(tmp_path: Path) -> None:
    """Creating DB twice doesn't fail (all DDL uses IF NOT EXISTS)."""
    db_path = tmp_path / "test.duckdb"
    db1 = AgentStateDB(db_path)
    db1.close()
    db2 = AgentStateDB(db_path)
    assert db2.schema_version() == 1
    db2.close()


def test_fetchall_dicts(db: AgentStateDB) -> None:
    """fetchall_dicts returns list of dicts with column names."""
    result = db.fetchall_dicts("SELECT 1 AS a, 'hello' AS b")
    assert result == [{"a": 1, "b": "hello"}]


def test_fetchall_dicts_empty(db: AgentStateDB) -> None:
    """fetchall_dicts returns empty list for no results."""
    result = db.fetchall_dicts(
        "SELECT * FROM fact_run WHERE run_id = 'nonexistent'"
    )
    assert result == []


def test_context_manager(tmp_path: Path) -> None:
    """DB works as context manager."""
    db_path = tmp_path / "test.duckdb"
    with AgentStateDB(db_path) as db:
        assert db.schema_version() == 1
