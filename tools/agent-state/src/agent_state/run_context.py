"""RunContext -- the primary developer interface for tracking runs."""

from __future__ import annotations

import hashlib
import logging
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

import orjson

from agent_state.database import AgentStateDB
from agent_state.models import RunStatus, RunType, StagedWatermark

logger = logging.getLogger(__name__)


def _generate_source_key(source_type: str, source_name: str, source_version: str | None = None) -> str:
    """Deterministic hash for dim_run_source."""
    raw = f"{source_type}:{source_name}:{source_version or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


def _generate_watermark_source_key(source_type: str, identifier: str) -> str:
    """Deterministic hash for dim_watermark_source."""
    raw = f"{source_type}:{identifier}"
    return hashlib.md5(raw.encode()).hexdigest()


class RunContext:
    """Context manager for tracking a single run.

    Usage:
        with RunContext(db, run_name="upstream_check", run_type="pipeline") as run:
            run.log("INFO", "Checking 9 upstream pages")
            for page in pages:
                run.stage_watermark("url", page_url, page_url, new_hash)
            run.complete(extract_count=9, update_count=3)
        # On exception: run.fail() called automatically, watermarks NOT committed
    """

    def __init__(
        self,
        db: AgentStateDB,
        run_name: str,
        run_type: str | RunType = RunType.PIPELINE,
        *,
        parent_run_id: str | None = None,
        correlation_id: str | None = None,
        source_name: str | None = None,
        source_version: str | None = None,
        run_description: str | None = None,
        is_restartable: bool = True,
        restart_from_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.db = db
        self.run_id = uuid.uuid4().hex
        self.run_name = run_name
        self.run_type = run_type.value if isinstance(run_type, RunType) else run_type
        self.parent_run_id = parent_run_id
        self.correlation_id = correlation_id or self.run_id
        self.source_name = source_name or run_name
        self.source_version = source_version
        self.run_description = run_description
        self.is_restartable = is_restartable
        self.restart_from_run_id = restart_from_run_id
        self.metadata = metadata
        self.started_at: datetime | None = None
        self._staged_watermarks: list[StagedWatermark] = []
        self._completed = False

    def __enter__(self) -> RunContext:
        self.started_at = datetime.now(UTC)

        # Ensure dim_run_source exists
        source_key = _generate_source_key(self.run_type, self.source_name, self.source_version)
        metadata_json = orjson.dumps(self.metadata).decode() if self.metadata else None

        self.db.execute(
            """
            INSERT INTO dim_run_source (source_key, source_type, source_name, source_version, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (source_key) DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at,
                source_version = COALESCE(EXCLUDED.source_version, dim_run_source.source_version)
            """,
            [source_key, self.run_type, self.source_name, self.source_version,
             self.started_at.isoformat(), self.started_at.isoformat()],
        )

        # Insert fact_run
        self.db.execute(
            """
            INSERT INTO fact_run (
                run_id, parent_run_id, correlation_id, source_key,
                run_type, run_name, run_description,
                started_at, status, is_restartable, restart_from_run_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                self.run_id, self.parent_run_id, self.correlation_id, source_key,
                self.run_type, self.run_name, self.run_description,
                self.started_at.isoformat(), RunStatus.RUNNING,
                self.is_restartable, self.restart_from_run_id, metadata_json,
            ],
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None and not self._completed:
            tb = traceback.format_exception(exc_type, exc_val, exc_tb)
            self.fail(error_detail="".join(tb))
        elif not self._completed:
            self.fail(error_detail="RunContext exited without calling complete() or fail()")

    def log(self, level: str, message: str, *, category: str | None = None,
            detail: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        """Log a message for this run."""
        metadata_json = orjson.dumps(metadata).decode() if metadata else None
        self.db.execute(
            """
            INSERT INTO fact_run_message (run_id, logged_at, level, category, message, detail, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [self.run_id, datetime.now(UTC).isoformat(), level, category, message, detail, metadata_json],
        )

    def stage_watermark(
        self,
        source_type: str,
        identifier: str,
        new_value: str,
        *,
        display_name: str | None = None,
        watermark_type: str = "content_hash",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Stage a watermark update. Only committed on complete()."""
        source_key = _generate_watermark_source_key(source_type, identifier)
        self._staged_watermarks.append(StagedWatermark(
            source_key=source_key,
            source_type=source_type,
            identifier=identifier,
            display_name=display_name or identifier,
            watermark_type=watermark_type,
            new_value=new_value,
            metadata=metadata,
        ))

    def complete(self, **counts: Any) -> None:
        """Mark run as successful and commit staged watermarks."""
        self._completed = True
        ended_at = datetime.now(UTC)
        duration_ms = int((ended_at - self.started_at).total_seconds() * 1000) if self.started_at else 0

        # Commit staged watermarks
        now = ended_at.isoformat()
        for wm in self._staged_watermarks:
            # Ensure dim_watermark_source exists
            self.db.execute(
                """
                INSERT INTO dim_watermark_source (watermark_source_key, source_type, identifier, display_name, first_seen_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (watermark_source_key) DO NOTHING
                """,
                [wm.source_key, wm.source_type, wm.identifier, wm.display_name, now],
            )

            # Get previous value
            prev = self.db.fetchone(
                """
                SELECT current_value FROM fact_watermark
                WHERE watermark_source_key = ?
                ORDER BY watermark_id DESC LIMIT 1
                """,
                [wm.source_key],
            )
            previous_value = prev[0] if prev else None
            changed = previous_value != wm.new_value

            metadata_json = orjson.dumps(wm.metadata).decode() if wm.metadata else None
            self.db.execute(
                """
                INSERT INTO fact_watermark (
                    run_id, watermark_source_key, checked_at, watermark_type,
                    previous_value, current_value, changed, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self.run_id, wm.source_key, now, wm.watermark_type,
                 previous_value, wm.new_value, changed, metadata_json],
            )

        # Update fact_run
        metadata_json = orjson.dumps(self.metadata).decode() if self.metadata else None
        self.db.execute(
            """
            UPDATE fact_run SET
                status = ?, ended_at = ?, duration_ms = ?,
                extract_count = ?, insert_count = ?, update_count = ?,
                delete_count = ?, error_count = ?, skip_count = ?,
                input_tokens = ?, output_tokens = ?, cache_read_tokens = ?,
                total_cost_usd = ?, num_turns = ?, model_name = ?
            WHERE run_id = ?
            """,
            [
                RunStatus.SUCCESS, ended_at.isoformat(), duration_ms,
                counts.get("extract_count", 0), counts.get("insert_count", 0),
                counts.get("update_count", 0), counts.get("delete_count", 0),
                counts.get("error_count", 0), counts.get("skip_count", 0),
                counts.get("input_tokens"), counts.get("output_tokens"),
                counts.get("cache_read_tokens"), counts.get("total_cost_usd"),
                counts.get("num_turns"), counts.get("model_name"),
                self.run_id,
            ],
        )
        self.log("INFO", f"Run completed in {duration_ms}ms", category="lifecycle")

    def fail(self, *, error_detail: str | None = None, status: str = RunStatus.FAILURE) -> None:
        """Mark run as failed. Staged watermarks are NOT committed."""
        self._completed = True
        ended_at = datetime.now(UTC)
        duration_ms = int((ended_at - self.started_at).total_seconds() * 1000) if self.started_at else 0

        self.db.execute(
            """
            UPDATE fact_run SET
                status = ?, ended_at = ?, duration_ms = ?,
                error_count = COALESCE(error_count, 0) + 1
            WHERE run_id = ?
            """,
            [status, ended_at.isoformat(), duration_ms, self.run_id],
        )
        if error_detail:
            self.log("ERROR", "Run failed", detail=error_detail, category="lifecycle")
        else:
            self.log("ERROR", "Run failed", category="lifecycle")
        self._staged_watermarks.clear()
