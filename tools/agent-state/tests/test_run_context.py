"""Tests for RunContext lifecycle and restartability."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_state.database import AgentStateDB
from agent_state.models import RunType
from agent_state.run_context import RunContext


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    return AgentStateDB(tmp_path / "test.duckdb")


def test_successful_run(db: AgentStateDB) -> None:
    """A completed run has status=success and duration."""
    with RunContext(db, run_name="test_run", run_type=RunType.PIPELINE) as run:
        run.log("INFO", "Hello")
        run.complete(extract_count=5, insert_count=3)

    row = db.fetchall_dicts("SELECT * FROM fact_run WHERE run_id = ?", [run.run_id])[0]
    assert row["status"] == "success"
    assert row["extract_count"] == 5
    assert row["insert_count"] == 3
    assert row["duration_ms"] is not None
    assert row["duration_ms"] >= 0


def test_failed_run_on_exception(db: AgentStateDB) -> None:
    """An unhandled exception marks the run as failed."""
    try:
        with RunContext(db, run_name="failing_run", run_type="pipeline") as run:
            run.log("INFO", "About to fail")
            raise ValueError("something broke")
    except ValueError:
        pass

    row = db.fetchall_dicts("SELECT * FROM fact_run WHERE run_id = ?", [run.run_id])[0]
    assert row["status"] == "failure"

    # Check error message was logged
    messages = db.fetchall_dicts(
        "SELECT * FROM fact_run_message WHERE run_id = ? AND level = 'ERROR'",
        [run.run_id],
    )
    assert len(messages) >= 1
    assert "Run failed" in messages[-1]["message"]


def test_explicit_fail(db: AgentStateDB) -> None:
    """Calling fail() explicitly marks the run as failed."""
    with RunContext(db, run_name="explicit_fail", run_type="pipeline") as run:
        run.fail(error_detail="manual abort")

    row = db.fetchall_dicts("SELECT * FROM fact_run WHERE run_id = ?", [run.run_id])[0]
    assert row["status"] == "failure"


def test_run_messages(db: AgentStateDB) -> None:
    """Messages are logged with correct levels."""
    with RunContext(db, run_name="message_test", run_type="pipeline") as run:
        run.log("INFO", "step 1")
        run.log("WARNING", "something odd", category="validation")
        run.log("DEBUG", "details", detail="extra info")
        run.complete()

    messages = db.fetchall_dicts(
        "SELECT * FROM fact_run_message WHERE run_id = ? ORDER BY message_id",
        [run.run_id],
    )
    # 3 explicit + 1 lifecycle "Run completed" = 4
    assert len(messages) == 4
    assert messages[0]["level"] == "INFO"
    assert messages[0]["message"] == "step 1"
    assert messages[1]["level"] == "WARNING"
    assert messages[1]["category"] == "validation"
    assert messages[2]["detail"] == "extra info"


def test_parent_child_runs(db: AgentStateDB) -> None:
    """Child run references parent."""
    with RunContext(db, run_name="parent", run_type="pipeline") as parent:
        with RunContext(db, run_name="child", run_type="pipeline",
                        parent_run_id=parent.run_id, correlation_id=parent.correlation_id) as child:
            child.complete()
        parent.complete()

    child_row = db.fetchall_dicts("SELECT * FROM fact_run WHERE run_id = ?", [child.run_id])[0]
    assert child_row["parent_run_id"] == parent.run_id
    assert child_row["correlation_id"] == parent.correlation_id


def test_dim_run_source_created(db: AgentStateDB) -> None:
    """RunContext creates dim_run_source entry."""
    with RunContext(db, run_name="source_test", run_type="pipeline", source_version="1.0") as run:
        run.complete()

    sources = db.fetchall_dicts("SELECT * FROM dim_run_source")
    assert len(sources) >= 1
    source = sources[-1]
    assert source["source_type"] == "pipeline"
    assert source["source_name"] == "source_test"


def test_correlation_id_defaults_to_run_id(db: AgentStateDB) -> None:
    """Without explicit correlation_id, it defaults to run_id."""
    with RunContext(db, run_name="corr_test", run_type="pipeline") as run:
        run.complete()

    assert run.correlation_id == run.run_id


def test_restart_from_run_id(db: AgentStateDB) -> None:
    """Retry run references the failed run."""
    with RunContext(db, run_name="original", run_type="pipeline") as original:
        original.fail(error_detail="first attempt failed")

    with RunContext(db, run_name="retry", run_type="pipeline",
                    restart_from_run_id=original.run_id) as retry:
        retry.complete()

    retry_row = db.fetchall_dicts("SELECT * FROM fact_run WHERE run_id = ?", [retry.run_id])[0]
    assert retry_row["restart_from_run_id"] == original.run_id
    assert retry_row["status"] == "success"
