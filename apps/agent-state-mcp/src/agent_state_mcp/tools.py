"""Tool implementation functions.

Thin wrappers over ``agent_state.query``, ``agent_state.watermarks``, and
``agent_state.skill_versions``. Each function:

- opens the DuckDB read-only if possible, falls back to read-write if the DB
  is missing (DuckDB creates on open);
- returns a dict with ``rows`` (list of dicts) or scalar ``data``, plus a
  ``_meta`` envelope (row count, duration_ms, schema_version, optional
  ``hint``);
- serializes non-JSON-native values (datetime, Decimal) via ``orjson`` so
  callers get deterministic output.

SQL injection is prevented by using parameterized queries throughout -- every
user-supplied value is bound as a ``?`` parameter, never string-concatenated.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import orjson

from agent_state.database import DEFAULT_DB_PATH, SCHEMA_VERSION, AgentStateDB
from agent_state.query import (
    get_flywheel,
    get_recent_runs,
    get_restartable_failures,
    get_run_detail,
    get_run_messages,
    get_run_stats,
    get_run_tree,
)
from agent_state.skill_versions import (
    get_active_skill,
    get_skill_version_by_hash,
    get_skill_versions,
    get_skills_by_domain,
)
from agent_state.watermarks import (
    get_all_watermarks,
    get_changed_watermarks,
    get_latest_watermark,
    get_watermark_history,
)


# --- helpers -----------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    """Coerce a value to something orjson will emit cleanly.

    orjson handles datetime, UUID, Decimal, and dataclasses natively, but we
    round-trip through it here to normalise exotic DuckDB types (e.g. HUGEINT)
    into ints/strings before they reach the MCP transport.
    """
    return orjson.loads(orjson.dumps(value, default=str))


_UNSET: Any = object()


def _envelope(
    rows: list[dict[str, Any]] | None = None,
    data: Any = _UNSET,
    *,
    started: float,
    schema_version: int | None = None,
    hint: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a uniform response envelope.

    Pass ``rows`` for list-shaped tools; pass ``data`` (including ``None``)
    for single-row tools so the key is always present in the JSON output.
    """
    meta: dict[str, Any] = {
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "schema_version": schema_version if schema_version is not None else SCHEMA_VERSION,
    }
    if rows is not None:
        meta["row_count"] = len(rows)
    elif data is not _UNSET:
        meta["row_count"] = 0 if data is None else 1
    if hint:
        meta["hint"] = hint
    if extra_meta:
        meta.update(extra_meta)

    payload: dict[str, Any] = {"_meta": meta}
    if rows is not None:
        payload["rows"] = _jsonable(rows)
    if data is not _UNSET:
        payload["data"] = None if data is None else _jsonable(data)
    return payload


def _db_exists(db_path: Path | None) -> bool:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    return path.exists()


def _empty_with_hint(started: float, hint: str) -> dict[str, Any]:
    """Missing-DB response for list-shaped tools."""
    return _envelope(
        rows=[],
        started=started,
        schema_version=0,
        hint=hint,
    )


def _missing_db_data(started: float, hint: str = "") -> dict[str, Any]:
    """Missing-DB response for single-row tools (data=null)."""
    return _envelope(
        data=None,
        started=started,
        schema_version=0,
        hint=hint or MISSING_DB_HINT,
    )


# --- connection cache --------------------------------------------------------
#
# FastMCP stdio servers are long-running; opening ``AgentStateDB`` per tool
# call re-executes the full schema DDL (via ``_init_schema``) every invocation.
# Cache one instance per db_path for the life of the server; close on shutdown
# via ``close_all_dbs`` (registered as an ``atexit`` hook in ``server.main``).

_db_cache: dict[str, AgentStateDB] = {}


def _cache_key(db_path: Path | None) -> str:
    return str(Path(db_path) if db_path else DEFAULT_DB_PATH)


@contextmanager
def _open_db(db_path: Path | None):
    """Yield the cached ``AgentStateDB`` for this path. Does not close."""
    key = _cache_key(db_path)
    db = _db_cache.get(key)
    if db is None:
        db = AgentStateDB(db_path) if db_path else AgentStateDB()
        _db_cache[key] = db
    yield db


def close_all_dbs() -> None:
    """Close every cached DuckDB connection. Safe to call multiple times."""
    for db in list(_db_cache.values()):
        try:
            db.close()
        except Exception:
            pass
    _db_cache.clear()


MISSING_DB_HINT = (
    "agent_state.duckdb does not exist. Run `agent-state init` via Bash to "
    "create it, or invoke a pipeline that uses RunContext."
)


# --- tool functions ----------------------------------------------------------


def list_recent_runs(
    limit: int = 20,
    run_type: str | None = None,
    status: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return the N most recent runs, newest first."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    limit = max(1, min(int(limit), 500))
    with _open_db(db_path) as db:
        rows = get_recent_runs(db, limit=limit, run_type=run_type, status=status)
    return _envelope(rows=rows, started=started)


def get_run(run_id: str, db_path: Path | None = None) -> dict[str, Any]:
    """Full detail for a single run (all columns from fact_run)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _missing_db_data(started)

    with _open_db(db_path) as db:
        row = get_run_detail(db, run_id)
    if row is None:
        return _envelope(
            data=None,
            started=started,
            hint=f"no run found with run_id={run_id}",
        )
    return _envelope(data=row, started=started)


def get_run_tree_tool(
    run_id: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Recursive run tree. If run_id given, the subtree rooted there."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = get_run_tree(db, run_id)
    return _envelope(rows=rows, started=started)


def get_run_messages_tool(
    run_id: str,
    level: str | None = None,
    limit: int = 500,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """All log messages for a run, in insertion order (capped at ``limit``)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    limit = max(1, min(int(limit), 5000))
    with _open_db(db_path) as db:
        rows = get_run_messages(db, run_id, level=level)
    truncated = len(rows) > limit
    rows = rows[:limit]
    extra = {"truncated": True, "total_unbounded": "unknown"} if truncated else None
    return _envelope(rows=rows, started=started, extra_meta=extra)


def find_failed_runs(
    since_days: int = 7,
    skill_name: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Failed runs within the last N days, optionally filtered by skill."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    since_days = max(1, min(int(since_days), 3650))
    limit = max(1, min(int(limit), 500))

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
    with _open_db(db_path) as db:
        rows = db.fetchall_dicts(sql, params)
    return _envelope(rows=rows, started=started)


def list_restartable_failures(db_path: Path | None = None) -> dict[str, Any]:
    """Failed runs flagged as restartable (v_restartable_failures view)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = get_restartable_failures(db)
    return _envelope(rows=rows, started=started)


def get_database_status(db_path: Path | None = None) -> dict[str, Any]:
    """Summary stats: total runs, by status, by type, watermarks, skills."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _envelope(
            data={
                "total_runs": 0,
                "by_status": {},
                "by_type": {},
                "active_watermarks": 0,
                "tracked_skills": 0,
                "total_messages": 0,
            },
            started=started,
            schema_version=0,
            hint=MISSING_DB_HINT,
        )

    with _open_db(db_path) as db:
        stats = get_run_stats(db)
        resolved_path = str(db.db_path)
        schema_version = db.schema_version()
    stats["database_path"] = resolved_path
    return _envelope(
        data=stats,
        started=started,
        schema_version=schema_version,
    )


def get_watermark_status(
    source_key: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Current watermark state, sorted by last-checked."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        if source_key:
            one = get_latest_watermark(db, source_key)
            rows = [one] if one else []
        else:
            rows = get_all_watermarks(db)
    return _envelope(rows=rows, started=started)


def get_watermark_history_tool(
    source_key: str,
    limit: int = 20,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Historical values for a watermark source, newest first."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    limit = max(1, min(int(limit), 500))
    with _open_db(db_path) as db:
        rows = get_watermark_history(db, source_key, limit=limit)
    return _envelope(rows=rows, started=started)


def get_run_watermark_changes(
    run_id: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Watermarks that changed during a specific run."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = get_changed_watermarks(db, run_id)
    return _envelope(rows=rows, started=started)


def list_skills_by_domain(
    domain: str,
    task_type: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Active skills in a routing domain (uses dim_skill_version)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = get_skills_by_domain(db, domain, task_type=task_type)
    return _envelope(rows=rows, started=started)


def list_skill_versions(
    skill_name: str,
    limit: int = 20,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Version history for a skill (newest first)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    limit = max(1, min(int(limit), 500))
    with _open_db(db_path) as db:
        rows = get_skill_versions(db, skill_name, limit=limit)
    return _envelope(rows=rows, started=started)


def get_active_skill_version(
    skill_name: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """The current active version row for a skill, or null."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _missing_db_data(started)

    with _open_db(db_path) as db:
        row = get_active_skill(db, skill_name)
    if row is None:
        return _envelope(
            data=None,
            started=started,
            hint=f"no active version for skill={skill_name}",
        )
    return _envelope(data=row, started=started)


def resolve_skill_version_by_hash(
    version_hash: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Look up a skill version by its content hash."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _missing_db_data(started)

    with _open_db(db_path) as db:
        row = get_skill_version_by_hash(db, version_hash)
    if row is None:
        return _envelope(
            data=None,
            started=started,
            hint=f"no skill version with hash={version_hash[:12]}...",
        )
    return _envelope(data=row, started=started)


def list_tracked_domains(db_path: Path | None = None) -> dict[str, Any]:
    """Distinct routing domains with skill counts (active only)."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = db.fetchall_dicts(
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
    return _envelope(rows=rows, started=started)


def get_flywheel_metrics(
    skill_name: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Flywheel view: producer run -> skill version -> consumer run."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = get_flywheel(db, skill_name=skill_name)
    return _envelope(rows=rows, started=started)


def list_run_sources(db_path: Path | None = None) -> dict[str, Any]:
    """Dim_run_source rows: where runs originate."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = db.fetchall_dicts(
            """
            SELECT drs.*, COUNT(fr.run_id) AS run_count
            FROM dim_run_source drs
            LEFT JOIN fact_run fr ON fr.source_key = drs.source_key
            GROUP BY drs.source_key, drs.source_type, drs.identifier,
                     drs.display_name, drs.metadata
            ORDER BY run_count DESC
            """
        )
    return _envelope(rows=rows, started=started)


def list_watermark_sources(db_path: Path | None = None) -> dict[str, Any]:
    """Dim_watermark_source rows: what we track watermarks for."""
    started = time.perf_counter()
    if not _db_exists(db_path):
        return _empty_with_hint(started, MISSING_DB_HINT)

    with _open_db(db_path) as db:
        rows = db.fetchall_dicts(
            "SELECT * FROM dim_watermark_source ORDER BY watermark_source_key"
        )
    return _envelope(rows=rows, started=started)
