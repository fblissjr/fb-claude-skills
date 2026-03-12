"""Tests for watermark atomicity -- the core restartability guarantee."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_state.database import AgentStateDB
from agent_state.run_context import RunContext
from agent_state.watermarks import get_all_watermarks, get_latest_watermark, get_changed_watermarks
from agent_state.run_context import _generate_watermark_source_key


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    return AgentStateDB(tmp_path / "test.duckdb")


def test_watermarks_committed_on_success(db: AgentStateDB) -> None:
    """Staged watermarks are written to fact_watermark on complete()."""
    with RunContext(db, run_name="wm_success", run_type="pipeline") as run:
        run.stage_watermark("url", "https://example.com/page1", "hash_abc")
        run.stage_watermark("url", "https://example.com/page2", "hash_def")
        run.complete(extract_count=2)

    watermarks = get_all_watermarks(db)
    assert len(watermarks) == 2
    values = {wm["current_value"] for wm in watermarks}
    assert values == {"hash_abc", "hash_def"}


def test_watermarks_not_committed_on_failure(db: AgentStateDB) -> None:
    """Staged watermarks are NOT written when the run fails."""
    try:
        with RunContext(db, run_name="wm_fail", run_type="pipeline") as run:
            run.stage_watermark("url", "https://example.com/page1", "should_not_appear")
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass

    watermarks = get_all_watermarks(db)
    assert len(watermarks) == 0


def test_watermark_tracks_previous_value(db: AgentStateDB) -> None:
    """Second watermark commit records previous_value from first commit."""
    # First run sets initial value
    with RunContext(db, run_name="wm_v1", run_type="pipeline") as run1:
        run1.stage_watermark("url", "https://example.com/page", "hash_v1")
        run1.complete()

    # Second run updates the value
    with RunContext(db, run_name="wm_v2", run_type="pipeline") as run2:
        run2.stage_watermark("url", "https://example.com/page", "hash_v2")
        run2.complete()

    source_key = _generate_watermark_source_key("url", "https://example.com/page")
    latest = get_latest_watermark(db, source_key)
    assert latest is not None
    assert latest["current_value"] == "hash_v2"

    # Check the second watermark entry has previous_value
    history = db.fetchall_dicts(
        "SELECT * FROM fact_watermark WHERE watermark_source_key = ? ORDER BY watermark_id",
        [source_key],
    )
    assert len(history) == 2
    assert history[0]["previous_value"] is None
    assert history[0]["changed"] is True  # No previous = changed
    assert history[1]["previous_value"] == "hash_v1"
    assert history[1]["changed"] is True


def test_unchanged_watermark(db: AgentStateDB) -> None:
    """When value hasn't changed, changed=False."""
    with RunContext(db, run_name="wm_same1", run_type="pipeline") as run1:
        run1.stage_watermark("url", "https://example.com/page", "same_hash")
        run1.complete()

    with RunContext(db, run_name="wm_same2", run_type="pipeline") as run2:
        run2.stage_watermark("url", "https://example.com/page", "same_hash")
        run2.complete()

    source_key = _generate_watermark_source_key("url", "https://example.com/page")
    history = db.fetchall_dicts(
        "SELECT * FROM fact_watermark WHERE watermark_source_key = ? ORDER BY watermark_id",
        [source_key],
    )
    assert history[1]["changed"] is False


def test_restartability_watermarks_dont_advance(db: AgentStateDB) -> None:
    """Core restartability test: fail -> watermarks stay at pre-failure state -> retry succeeds."""
    # Step 1: Successful initial run
    with RunContext(db, run_name="initial", run_type="pipeline") as run1:
        run1.stage_watermark("url", "https://example.com/page", "hash_v1")
        run1.complete()

    source_key = _generate_watermark_source_key("url", "https://example.com/page")
    wm1 = get_latest_watermark(db, source_key)
    assert wm1["current_value"] == "hash_v1"

    # Step 2: Failed run stages hash_v2 but doesn't commit
    try:
        with RunContext(db, run_name="failed_update", run_type="pipeline") as run2:
            run2.stage_watermark("url", "https://example.com/page", "hash_v2")
            raise RuntimeError("crash during processing")
    except RuntimeError:
        pass

    # Watermark should still be hash_v1
    wm2 = get_latest_watermark(db, source_key)
    assert wm2["current_value"] == "hash_v1"

    # Step 3: Retry succeeds with hash_v2
    with RunContext(db, run_name="retry", run_type="pipeline",
                    restart_from_run_id=run2.run_id) as run3:
        run3.stage_watermark("url", "https://example.com/page", "hash_v2")
        run3.complete()

    wm3 = get_latest_watermark(db, source_key)
    assert wm3["current_value"] == "hash_v2"

    # The failed run should be in v_restartable_failures... but now retried successfully
    failures = db.fetchall_dicts("SELECT * FROM v_restartable_failures")
    # The failed run should NOT appear because a successful retry exists
    failed_ids = {f["run_id"] for f in failures}
    assert run2.run_id not in failed_ids


def test_get_changed_watermarks(db: AgentStateDB) -> None:
    """get_changed_watermarks returns only watermarks that changed during a run."""
    with RunContext(db, run_name="setup", run_type="pipeline") as run1:
        run1.stage_watermark("url", "https://example.com/a", "hash_a")
        run1.stage_watermark("url", "https://example.com/b", "hash_b")
        run1.complete()

    with RunContext(db, run_name="partial_change", run_type="pipeline") as run2:
        run2.stage_watermark("url", "https://example.com/a", "hash_a")  # unchanged
        run2.stage_watermark("url", "https://example.com/b", "hash_b_v2")  # changed
        run2.complete()

    changed = get_changed_watermarks(db, run2.run_id)
    assert len(changed) == 1
    assert changed[0]["current_value"] == "hash_b_v2"
