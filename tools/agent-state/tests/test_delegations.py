"""Tests for delegation outcome recording (fact_delegation)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from agent_state.database import AgentStateDB
from agent_state.delegations import get_delegation_stats, record_delegation
from agent_state.models import DelegationOutcome


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    db_path = tmp_path / "test.duckdb"
    return AgentStateDB(db_path)


def test_fact_delegation_table_exists(db: AgentStateDB) -> None:
    tables = db.fetchall(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
    )
    assert "fact_delegation" in {row[0] for row in tables}


def test_delegation_stats_view_exists(db: AgentStateDB) -> None:
    views = db.fetchall(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'VIEW'"
    )
    assert "v_delegation_stats" in {row[0] for row in views}


def test_record_delegation_inserts_row(db: AgentStateDB) -> None:
    key = record_delegation(
        db,
        task_summary="rename config keys across 12 files",
        model_name="haiku",
        outcome=DelegationOutcome.ACCEPTED,
        task_domain="coding",
        verification="diff_review",
        orchestrator_model="opus",
        session_id="sess-1",
    )
    rows = db.fetchall_dicts(
        "SELECT * FROM fact_delegation WHERE delegation_key = ?", [key]
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["task_summary"] == "rename config keys across 12 files"
    assert row["model_name"] == "haiku"
    assert row["outcome"] == "accepted"
    assert row["task_domain"] == "coding"
    assert row["verification"] == "diff_review"
    assert row["orchestrator_model"] == "opus"
    assert row["session_id"] == "sess-1"
    assert row["record_source"] == "cli"
    assert row["inserted_at"] is not None


def test_record_delegation_deterministic_key(db: AgentStateDB) -> None:
    """Same inputs + same recorded_at produce the same surrogate key."""
    ts = datetime(2026, 7, 5, 12, 0, 0)
    kwargs = dict(
        task_summary="convert csv to parquet",
        model_name="sonnet",
        outcome=DelegationOutcome.ACCEPTED,
        session_id="sess-2",
        recorded_at=ts,
    )
    key1 = record_delegation(db, **kwargs)
    key2 = record_delegation(db, **kwargs)
    assert key1 == key2
    # Append-only with a deterministic PK: the duplicate is skipped, not doubled.
    rows = db.fetchall_dicts(
        "SELECT * FROM fact_delegation WHERE delegation_key = ?", [key1]
    )
    assert len(rows) == 1


def test_record_delegation_accepts_plain_string_outcome(db: AgentStateDB) -> None:
    key = record_delegation(
        db,
        task_summary="write boilerplate tests",
        model_name="haiku",
        outcome="redone",
    )
    rows = db.fetchall_dicts(
        "SELECT outcome FROM fact_delegation WHERE delegation_key = ?", [key]
    )
    assert rows[0]["outcome"] == "redone"


def test_record_delegation_rejects_unknown_outcome(db: AgentStateDB) -> None:
    with pytest.raises(ValueError, match="outcome"):
        record_delegation(
            db,
            task_summary="anything",
            model_name="haiku",
            outcome="great",
        )


def test_delegation_stats_aggregates(db: AgentStateDB) -> None:
    for i, outcome in enumerate(
        [
            DelegationOutcome.ACCEPTED,
            DelegationOutcome.ACCEPTED,
            DelegationOutcome.REDONE,
        ]
    ):
        record_delegation(
            db,
            task_summary=f"task {i}",
            model_name="haiku",
            outcome=outcome,
            task_domain="coding",
            recorded_at=datetime(2026, 7, 5, 12, 0, i),
        )
    record_delegation(
        db,
        task_summary="sonnet task",
        model_name="sonnet",
        outcome=DelegationOutcome.ACCEPTED,
        task_domain="data",
        recorded_at=datetime(2026, 7, 5, 12, 1, 0),
    )

    stats = get_delegation_stats(db)
    by_model = {(s["model_name"], s["task_domain"]): s for s in stats}
    haiku = by_model[("haiku", "coding")]
    assert haiku["delegations"] == 3
    assert haiku["accepted"] == 2
    assert haiku["redone"] == 1
    assert haiku["acceptance_rate"] == pytest.approx(0.667, abs=0.001)
    assert by_model[("sonnet", "data")]["acceptance_rate"] == 1.0


def test_delegation_stats_filter_by_model(db: AgentStateDB) -> None:
    record_delegation(
        db, task_summary="a", model_name="haiku", outcome=DelegationOutcome.ACCEPTED
    )
    record_delegation(
        db, task_summary="b", model_name="sonnet", outcome=DelegationOutcome.ACCEPTED
    )
    stats = get_delegation_stats(db, model_name="haiku")
    assert len(stats) == 1
    assert stats[0]["model_name"] == "haiku"


def test_schema_version_is_3(db: AgentStateDB) -> None:
    assert db.schema_version() == 3
