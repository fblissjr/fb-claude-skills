"""Tests for migration from changes.jsonl and upstream_hashes.json."""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest

from agent_state.database import AgentStateDB
from agent_state.migration import migrate_from_jsonl
from agent_state.watermarks import get_all_watermarks


@pytest.fixture
def db(tmp_path: Path) -> AgentStateDB:
    return AgentStateDB(tmp_path / "test.duckdb")


def _create_state_dir(repo_dir: Path) -> Path:
    state_dir = repo_dir / ".skill-maintainer" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def test_migrate_empty_dir(db: AgentStateDB, tmp_path: Path) -> None:
    """Migration on a directory with no state files is a no-op."""
    counts = migrate_from_jsonl(db, tmp_path)
    assert counts == {"runs": 0, "watermarks": 0, "skipped": 0}


def test_migrate_changes_jsonl(db: AgentStateDB, tmp_path: Path) -> None:
    """Import changes.jsonl events as fact_run rows."""
    state_dir = _create_state_dir(tmp_path)
    events = [
        {"type": "upstream_check", "timestamp": "2026-03-01T10:00:00", "pages_checked": 9},
        {"type": "quality_report", "timestamp": "2026-03-01T10:05:00", "skills_checked": 10},
        {"type": "source_pull", "timestamp": "2026-03-02T08:00:00", "repos_pulled": 5},
    ]
    with open(state_dir / "changes.jsonl", "wb") as f:
        for event in events:
            f.write(orjson.dumps(event) + b"\n")

    counts = migrate_from_jsonl(db, tmp_path)
    assert counts["runs"] == 3
    assert counts["skipped"] == 0

    # Verify fact_run rows exist (3 events + 1 migration run itself)
    runs = db.fetchall_dicts("SELECT * FROM fact_run ORDER BY started_at")
    imported = [r for r in runs if r.get("run_name") != "migrate_jsonl"]
    assert len(imported) == 3
    assert imported[0]["run_name"] == "upstream_check"
    assert imported[1]["run_name"] == "quality_report"
    assert imported[2]["run_name"] == "source_pull"


def test_migrate_upstream_hashes(db: AgentStateDB, tmp_path: Path) -> None:
    """Import upstream_hashes.json as watermark baselines."""
    state_dir = _create_state_dir(tmp_path)
    hashes = {
        "https://code.claude.com/docs/en/skills": "abc123",
        "https://code.claude.com/docs/en/plugins": "def456",
        "local_repos": {
            "/Users/test/repo1": "sha_aaa",
            "/Users/test/repo2": "sha_bbb",
        },
    }
    (state_dir / "upstream_hashes.json").write_bytes(
        orjson.dumps(hashes, option=orjson.OPT_INDENT_2)
    )

    counts = migrate_from_jsonl(db, tmp_path)
    assert counts["watermarks"] == 4  # 2 URLs + 2 repos

    watermarks = get_all_watermarks(db)
    assert len(watermarks) == 4
    values = {wm["current_value"] for wm in watermarks}
    assert values == {"abc123", "def456", "sha_aaa", "sha_bbb"}


def test_migrate_handles_blank_lines(db: AgentStateDB, tmp_path: Path) -> None:
    """Blank lines in changes.jsonl are skipped."""
    state_dir = _create_state_dir(tmp_path)
    content = (
        orjson.dumps({"type": "upstream_check", "timestamp": "2026-03-01T10:00:00"})
        + b"\n\n"
        + orjson.dumps({"type": "quality_report", "timestamp": "2026-03-01T11:00:00"})
        + b"\n"
    )
    (state_dir / "changes.jsonl").write_bytes(content)

    counts = migrate_from_jsonl(db, tmp_path)
    assert counts["runs"] == 2


def test_migrate_dry_run(db: AgentStateDB, tmp_path: Path) -> None:
    """Dry run counts items without writing."""
    state_dir = _create_state_dir(tmp_path)
    events = [
        {"type": "upstream_check", "timestamp": "2026-03-01T10:00:00"},
    ]
    with open(state_dir / "changes.jsonl", "wb") as f:
        for event in events:
            f.write(orjson.dumps(event) + b"\n")

    hashes = {"https://example.com": "hash123"}
    (state_dir / "upstream_hashes.json").write_bytes(orjson.dumps(hashes))

    counts = migrate_from_jsonl(db, tmp_path, dry_run=True)
    assert counts["runs"] == 1
    assert counts["watermarks"] == 1

    # Nothing actually written (except the migration wrapper runs)
    # But since dry_run skips _import_event and stage_watermark, only migration
    # wrapper runs exist. The dry_run still calls RunContext.complete() for the
    # wrapper runs, so we check for no *imported* runs.
    all_runs = db.fetchall_dicts("SELECT * FROM fact_run")
    imported = [r for r in all_runs if r["run_name"] not in ("migrate_jsonl", "migrate_hashes")]
    assert len(imported) == 0


def test_migrate_both_files(db: AgentStateDB, tmp_path: Path) -> None:
    """Migration processes both files in one call."""
    state_dir = _create_state_dir(tmp_path)

    with open(state_dir / "changes.jsonl", "wb") as f:
        f.write(orjson.dumps({"type": "validation", "timestamp": "2026-03-01T10:00:00"}) + b"\n")

    (state_dir / "upstream_hashes.json").write_bytes(
        orjson.dumps({"https://example.com": "hash_xyz"})
    )

    counts = migrate_from_jsonl(db, tmp_path)
    assert counts["runs"] == 1
    assert counts["watermarks"] == 1
