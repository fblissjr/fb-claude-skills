"""Watermark query helpers."""

from __future__ import annotations

from typing import Any

from agent_state.database import AgentStateDB


def get_latest_watermark(db: AgentStateDB, source_key: str) -> dict[str, Any] | None:
    """Get the latest watermark for a given source key."""
    rows = db.fetchall_dicts(
        "SELECT * FROM v_latest_watermark WHERE watermark_source_key = ?",
        [source_key],
    )
    return rows[0] if rows else None


def get_all_watermarks(db: AgentStateDB) -> list[dict[str, Any]]:
    """Get current watermarks for all sources."""
    return db.fetchall_dicts(
        "SELECT * FROM v_latest_watermark ORDER BY checked_at DESC"
    )


def get_watermark_history(
    db: AgentStateDB, source_key: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Get watermark change history for a source."""
    return db.fetchall_dicts(
        """
        SELECT fw.*, dws.identifier, dws.display_name
        FROM fact_watermark fw
        JOIN dim_watermark_source dws ON fw.watermark_source_key = dws.watermark_source_key
        WHERE fw.watermark_source_key = ?
        ORDER BY fw.watermark_id DESC
        LIMIT ?
        """,
        [source_key, limit],
    )


def get_changed_watermarks(db: AgentStateDB, run_id: str) -> list[dict[str, Any]]:
    """Get all watermarks that changed during a specific run."""
    return db.fetchall_dicts(
        """
        SELECT fw.*, dws.identifier, dws.display_name
        FROM fact_watermark fw
        JOIN dim_watermark_source dws ON fw.watermark_source_key = dws.watermark_source_key
        WHERE fw.run_id = ? AND fw.changed = TRUE
        ORDER BY fw.watermark_id
        """,
        [run_id],
    )
