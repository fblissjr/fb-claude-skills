"""Tests for skill version routing metadata and lifecycle management."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_state.database import AgentStateDB
from agent_state.skill_versions import (
    deprecate_skill_version,
    get_active_skill,
    get_or_create_skill_version,
    get_skills_by_domain,
)


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    db_path = tmp_path / "test.duckdb"
    return AgentStateDB(db_path)


def test_get_or_create_with_routing_metadata(db: AgentStateDB) -> None:
    """Create with domain + task_type, verify stored."""
    sv_id = get_or_create_skill_version(
        db,
        "extractor",
        "hash_abc",
        domain="extraction",
        task_type="structured_data_from_document",
    )
    rows = db.fetchall_dicts(
        "SELECT domain, task_type, status FROM dim_skill_version WHERE skill_version_id = ?",
        [sv_id],
    )
    assert len(rows) == 1
    assert rows[0]["domain"] == "extraction"
    assert rows[0]["task_type"] == "structured_data_from_document"
    assert rows[0]["status"] == "active"


def test_get_active_skill(db: AgentStateDB) -> None:
    """Only the active version is returned, not deprecated ones."""
    sv1 = get_or_create_skill_version(db, "validator", "hash_v1", domain="validation")
    deprecate_skill_version(db, sv1)
    sv2 = get_or_create_skill_version(db, "validator", "hash_v2", domain="validation")

    result = get_active_skill(db, "validator")
    assert result is not None
    assert result["skill_version_id"] == sv2
    assert result["status"] == "active"


def test_get_active_skill_none(db: AgentStateDB) -> None:
    """Returns None when no active version exists."""
    assert get_active_skill(db, "nonexistent") is None


def test_deprecate_skill_version(db: AgentStateDB) -> None:
    """Deprecating changes status from active to deprecated."""
    sv_id = get_or_create_skill_version(db, "old-skill", "hash_old")
    deprecate_skill_version(db, sv_id)

    rows = db.fetchall_dicts(
        "SELECT status FROM dim_skill_version WHERE skill_version_id = ?",
        [sv_id],
    )
    assert rows[0]["status"] == "deprecated"


def test_get_skills_by_domain(db: AgentStateDB) -> None:
    """Filter by domain returns only matching active skills."""
    get_or_create_skill_version(db, "s1", "h1", domain="extraction", task_type="pdf")
    get_or_create_skill_version(db, "s2", "h2", domain="extraction", task_type="html")
    get_or_create_skill_version(db, "s3", "h3", domain="validation")

    extraction = get_skills_by_domain(db, "extraction")
    assert len(extraction) == 2
    assert {r["skill_name"] for r in extraction} == {"s1", "s2"}

    # Filter by task_type too
    pdf_only = get_skills_by_domain(db, "extraction", task_type="pdf")
    assert len(pdf_only) == 1
    assert pdf_only[0]["skill_name"] == "s1"


def test_get_skills_by_domain_excludes_deprecated(db: AgentStateDB) -> None:
    """Deprecated skills are excluded from domain queries."""
    sv_id = get_or_create_skill_version(db, "old", "h_old", domain="extraction")
    deprecate_skill_version(db, sv_id)
    get_or_create_skill_version(db, "new", "h_new", domain="extraction")

    results = get_skills_by_domain(db, "extraction")
    assert len(results) == 1
    assert results[0]["skill_name"] == "new"


def test_status_defaults_to_active(db: AgentStateDB) -> None:
    """Creating without explicit status defaults to 'active'."""
    sv_id = get_or_create_skill_version(db, "default-status", "hash_def")
    rows = db.fetchall_dicts(
        "SELECT status FROM dim_skill_version WHERE skill_version_id = ?",
        [sv_id],
    )
    assert rows[0]["status"] == "active"
