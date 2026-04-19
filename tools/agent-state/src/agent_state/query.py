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
    """Summary statistics for the database.

    Consolidates four scalar counts into one query via scalar subqueries
    so the shared database status view requires 3 round-trips instead of
    6 (the two GROUP BYs remain separate because combining them would
    need a PIVOT or UNION-with-discriminator, both worse for readability).
    """
    scalars = db.fetchone(
        """
        SELECT
            (SELECT COUNT(*) FROM fact_run),
            (SELECT COUNT(*) FROM v_latest_watermark),
            (SELECT COUNT(DISTINCT skill_name) FROM dim_skill_version),
            (SELECT COUNT(*) FROM fact_run_message)
        """
    )
    by_status = db.fetchall(
        "SELECT status, COUNT(*) FROM fact_run GROUP BY status ORDER BY COUNT(*) DESC"
    )
    by_type = db.fetchall(
        "SELECT run_type, COUNT(*) FROM fact_run GROUP BY run_type ORDER BY COUNT(*) DESC"
    )
    total_runs, active_watermarks, tracked_skills, total_messages = (
        scalars if scalars else (0, 0, 0, 0)
    )
    return {
        "total_runs": total_runs or 0,
        "by_status": {row[0]: row[1] for row in by_status},
        "by_type": {row[0]: row[1] for row in by_type},
        "active_watermarks": active_watermarks or 0,
        "tracked_skills": tracked_skills or 0,
        "total_messages": total_messages or 0,
    }


def get_failed_runs(
    db: AgentStateDB,
    since_days: int = 7,
    skill_name: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Failed or partial runs within the last N days.

    When ``skill_name`` is supplied, matches either the run's ``run_name`` or
    any skill version it consumed/produced (joined through
    ``dim_skill_version``). All user values bind via ``?`` placeholders --
    never string-interpolated into SQL.
    """
    where: list[str] = [
        "fr.status IN ('failure', 'partial')",
        "fr.started_at >= CURRENT_TIMESTAMP - (? * INTERVAL 1 DAY)",
    ]
    params: list[Any] = [since_days]
    if skill_name:
        where.append(
            "(fr.run_name = ? "
            "OR fr.consumes_skill_version_id IN "
            "(SELECT skill_version_id FROM dim_skill_version WHERE skill_name = ?) "
            "OR fr.produces_skill_version_id IN "
            "(SELECT skill_version_id FROM dim_skill_version WHERE skill_name = ?))"
        )
        params.extend([skill_name, skill_name, skill_name])
    params.append(limit)

    sql = (
        "SELECT fr.run_id, fr.run_type, fr.run_name, fr.status, fr.started_at, "
        "fr.ended_at, fr.duration_ms, fr.error_count, "
        "fr.consumes_skill_version_id, fr.produces_skill_version_id, "
        "fr.is_restartable, fr.parent_run_id, fr.correlation_id "
        "FROM fact_run fr WHERE " + " AND ".join(where) + " "
        "ORDER BY fr.started_at DESC LIMIT ?"
    )
    return db.fetchall_dicts(sql, params)


def get_tracked_domains(db: AgentStateDB) -> list[dict[str, Any]]:
    """Distinct routing domains from dim_skill_version, active rows only.

    Returns one row per domain with ``skill_count`` (distinct skill names)
    and ``version_count`` (total active version rows).
    """
    return db.fetchall_dicts(
        """
        SELECT domain,
               COUNT(DISTINCT skill_name) AS skill_count,
               COUNT(*) AS version_count
        FROM dim_skill_version
        WHERE domain IS NOT NULL
          AND status = 'active'
        GROUP BY domain
        ORDER BY skill_count DESC
        """
    )


def get_run_sources(db: AgentStateDB) -> list[dict[str, Any]]:
    """dim_run_source rows joined with a run_count from fact_run.

    GROUP BY lists every non-aggregated column in dim_run_source
    (DuckDB requires all of them).
    """
    return db.fetchall_dicts(
        """
        SELECT drs.*, COUNT(fr.run_id) AS run_count
        FROM dim_run_source drs
        LEFT JOIN fact_run fr ON fr.source_key = drs.source_key
        GROUP BY drs.source_key, drs.source_type, drs.source_name,
                 drs.source_version, drs.config_hash,
                 drs.first_seen_at, drs.last_seen_at, drs.metadata
        ORDER BY run_count DESC
        """
    )


def get_watermark_sources(db: AgentStateDB) -> list[dict[str, Any]]:
    """dim_watermark_source rows -- everything we track a cursor for."""
    return db.fetchall_dicts(
        "SELECT * FROM dim_watermark_source ORDER BY watermark_source_key"
    )
