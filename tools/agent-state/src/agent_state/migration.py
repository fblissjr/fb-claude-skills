"""Migration from skill-maintainer's changes.jsonl and upstream_hashes.json."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import orjson

from agent_state.database import AgentStateDB
from agent_state.run_context import RunContext

logger = logging.getLogger(__name__)


def migrate_from_jsonl(
    db: AgentStateDB,
    repo_dir: str | Path,
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Import changes.jsonl events as fact_run rows and upstream_hashes.json as watermarks.

    Returns counts of imported items.
    """
    repo_dir = Path(repo_dir)
    state_dir = repo_dir / ".skill-maintainer" / "state"
    counts: dict[str, int] = {"runs": 0, "watermarks": 0, "skipped": 0}

    # Import changes.jsonl
    changes_path = state_dir / "changes.jsonl"
    if changes_path.exists():
        with RunContext(db, run_name="migrate_jsonl", run_type="pipeline",
                        run_description="One-time import from changes.jsonl") as run:
            run.log("INFO", f"Reading {changes_path}")
            for line_bytes in changes_path.read_bytes().splitlines():
                if not line_bytes.strip():
                    continue
                try:
                    event = orjson.loads(line_bytes)
                except orjson.JSONDecodeError:
                    counts["skipped"] += 1
                    continue

                if dry_run:
                    counts["runs"] += 1
                    continue

                _import_event(db, event, run.run_id)
                counts["runs"] += 1

            run.complete(
                extract_count=counts["runs"] + counts["skipped"],
                insert_count=counts["runs"],
                skip_count=counts["skipped"],
            )
    else:
        logger.info("No changes.jsonl found at %s", changes_path)

    # Import upstream_hashes.json as watermark baseline
    hashes_path = state_dir / "upstream_hashes.json"
    if hashes_path.exists():
        hashes = orjson.loads(hashes_path.read_bytes())

        with RunContext(db, run_name="migrate_hashes", run_type="pipeline",
                        run_description="One-time import from upstream_hashes.json") as run:
            run.log("INFO", f"Reading {hashes_path}")

            # Import page hashes (URL -> content hash)
            for key, value in hashes.items():
                if key.startswith("_") or key == "local_repos":
                    continue
                if isinstance(value, str):
                    # Simple URL -> hash mapping
                    if not dry_run:
                        run.stage_watermark(
                            "url", key, value,
                            display_name=key,
                            watermark_type="content_hash",
                        )
                    counts["watermarks"] += 1

            # Import local_repos section
            local_repos = hashes.get("local_repos", {})
            for repo_path, sha in local_repos.items():
                if isinstance(sha, str):
                    if not dry_run:
                        run.stage_watermark(
                            "git_repo", repo_path, sha,
                            display_name=repo_path.split("/")[-1] if "/" in repo_path else repo_path,
                            watermark_type="git_sha",
                        )
                    counts["watermarks"] += 1

            run.complete(
                extract_count=counts["watermarks"],
                insert_count=counts["watermarks"],
            )
    else:
        logger.info("No upstream_hashes.json found at %s", hashes_path)

    return counts


def _import_event(db: AgentStateDB, event: dict[str, Any], migration_run_id: str) -> None:
    """Import a single changes.jsonl event as a fact_run row."""
    import uuid

    event_type = event.get("type", event.get("event", "unknown"))
    # Real data uses "date" (YYYY-MM-DD), fallback to "timestamp" or "ts"
    raw_ts = event.get("date", event.get("timestamp", event.get("ts", "")))
    # Normalize date-only strings to full timestamp
    if raw_ts and len(raw_ts) == 10:
        raw_ts = f"{raw_ts}T00:00:00"
    timestamp = raw_ts or "1970-01-01T00:00:00"

    run_id = uuid.uuid4().hex
    skip_keys = {"type", "event", "timestamp", "ts", "date"}
    metadata = {k: v for k, v in event.items() if k not in skip_keys}
    metadata["migrated_from"] = "changes.jsonl"
    metadata["migration_run_id"] = migration_run_id
    metadata_json = orjson.dumps(metadata).decode()

    run_name = _map_event_type(event_type)

    db.execute(
        """
        INSERT INTO fact_run (
            run_id, run_type, run_name, started_at, ended_at, status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [run_id, "pipeline", run_name, timestamp, timestamp, "success", metadata_json],
    )


def _map_event_type(event_type: str) -> str:
    """Map changes.jsonl event types to human-readable run names."""
    mapping = {
        "upstream_check": "upstream_check",
        "quality_report": "quality_report",
        "source_pull": "source_pull",
        "validation": "validation",
        "freshness_check": "freshness_check",
        "measure": "measure_tokens",
    }
    return mapping.get(event_type, event_type)
