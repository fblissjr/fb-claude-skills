"""Read-only query helpers for run trees, flywheel, and restartable failures."""

from __future__ import annotations

from typing import Any

from agent_state.database import AgentStateDB


def get_recent_runs(
    db: AgentStateDB,
    limit: int = 20,
    run_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Get recent runs with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []
    if run_type:
        conditions.append("run_type = ?")
        params.append(run_type)
    if status:
        conditions.append("status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    return db.fetchall_dicts(
        f"""
        SELECT run_id, run_type, run_name, status, started_at, ended_at,
               duration_ms, extract_count, insert_count, update_count,
               error_count, skip_count
        FROM fact_run
        {where}
        ORDER BY started_at DESC
        LIMIT ?
        """,
        params,
    )


def get_run_detail(db: AgentStateDB, run_id: str) -> dict[str, Any] | None:
    """Get full detail for a single run."""
    rows = db.fetchall_dicts(
        "SELECT * FROM fact_run WHERE run_id = ?", [run_id]
    )
    return rows[0] if rows else None


def get_run_messages(
    db: AgentStateDB, run_id: str, level: str | None = None
) -> list[dict[str, Any]]:
    """Get messages for a run."""
    if level:
        return db.fetchall_dicts(
            "SELECT * FROM fact_run_message WHERE run_id = ? AND level = ? ORDER BY message_id",
            [run_id, level],
        )
    return db.fetchall_dicts(
        "SELECT * FROM fact_run_message WHERE run_id = ? ORDER BY message_id",
        [run_id],
    )


def get_run_tree(db: AgentStateDB, root_run_id: str | None = None) -> list[dict[str, Any]]:
    """Get hierarchical run tree. If root_run_id given, show that subtree only."""
    if root_run_id:
        return db.fetchall_dicts(
            """
            WITH RECURSIVE tree AS (
                SELECT run_id, parent_run_id, correlation_id,
                       run_type, run_name, status, started_at, ended_at, duration_ms,
                       0 AS depth
                FROM fact_run WHERE run_id = ?
                UNION ALL
                SELECT r.run_id, r.parent_run_id, r.correlation_id,
                       r.run_type, r.run_name, r.status, r.started_at, r.ended_at, r.duration_ms,
                       t.depth + 1
                FROM fact_run r JOIN tree t ON r.parent_run_id = t.run_id
            )
            SELECT * FROM tree ORDER BY started_at
            """,
            [root_run_id],
        )
    return db.fetchall_dicts("SELECT * FROM v_run_tree")


def get_flywheel(db: AgentStateDB, skill_name: str | None = None) -> list[dict[str, Any]]:
    """Get flywheel view: producer -> skill version -> consumer."""
    if skill_name:
        return db.fetchall_dicts(
            "SELECT * FROM v_flywheel WHERE skill_name = ? ORDER BY produced_at DESC NULLS LAST",
            [skill_name],
        )
    return db.fetchall_dicts(
        "SELECT * FROM v_flywheel ORDER BY produced_at DESC NULLS LAST"
    )


def get_restartable_failures(db: AgentStateDB) -> list[dict[str, Any]]:
    """Get failed runs eligible for retry."""
    return db.fetchall_dicts("SELECT * FROM v_restartable_failures ORDER BY started_at DESC")


def get_run_stats(db: AgentStateDB) -> dict[str, Any]:
    """Summary statistics for the database."""
    total = db.fetchone("SELECT COUNT(*) FROM fact_run")
    by_status = db.fetchall(
        "SELECT status, COUNT(*) FROM fact_run GROUP BY status ORDER BY COUNT(*) DESC"
    )
    by_type = db.fetchall(
        "SELECT run_type, COUNT(*) FROM fact_run GROUP BY run_type ORDER BY COUNT(*) DESC"
    )
    watermarks = db.fetchone("SELECT COUNT(*) FROM v_latest_watermark")
    skills = db.fetchone("SELECT COUNT(DISTINCT skill_name) FROM dim_skill_version")
    messages = db.fetchone("SELECT COUNT(*) FROM fact_run_message")
    return {
        "total_runs": total[0] if total else 0,
        "by_status": {row[0]: row[1] for row in by_status},
        "by_type": {row[0]: row[1] for row in by_type},
        "active_watermarks": watermarks[0] if watermarks else 0,
        "tracked_skills": skills[0] if skills else 0,
        "total_messages": messages[0] if messages else 0,
    }
