"""Delegation outcome recording and stats (fact_delegation)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import orjson

from agent_state.database import AgentStateDB
from agent_state.models import DelegationOutcome


def record_delegation(
    db: AgentStateDB,
    *,
    task_summary: str,
    model_name: str,
    outcome: DelegationOutcome | str,
    task_domain: str | None = None,
    verification: str | None = None,
    orchestrator_model: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    recorded_at: datetime | None = None,
    record_source: str = "cli",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record one delegated subagent task outcome. Returns the delegation key.

    Append-only with a deterministic surrogate key: re-recording identical
    inputs (same recorded_at) is a no-op, not a duplicate row.
    """
    try:
        outcome_value = DelegationOutcome(outcome).value
    except ValueError:
        valid = ", ".join(o.value for o in DelegationOutcome)
        raise ValueError(f"Unknown outcome {outcome!r}; expected one of: {valid}") from None

    recorded_at = recorded_at or datetime.now()
    key_material = "|".join(
        [task_summary, model_name, outcome_value, session_id or "", recorded_at.isoformat()]
    )
    delegation_key = hashlib.md5(key_material.encode()).hexdigest()

    db.execute(
        """
        INSERT INTO fact_delegation (
            delegation_key, run_id, session_id, task_summary, task_domain,
            model_name, orchestrator_model, outcome, verification,
            recorded_at, record_source, metadata
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_delegation WHERE delegation_key = ?
        )
        """,
        [
            delegation_key, run_id, session_id, task_summary, task_domain,
            model_name, orchestrator_model, outcome_value, verification,
            recorded_at, record_source,
            orjson.dumps(metadata).decode() if metadata else None,
            delegation_key,
        ],
    )
    return delegation_key


def get_delegation_stats(
    db: AgentStateDB,
    model_name: str | None = None,
    task_domain: str | None = None,
) -> list[dict[str, Any]]:
    """Acceptance-rate stats per (model, domain), optionally filtered."""
    clauses, params = [], []
    if model_name:
        clauses.append("model_name = ?")
        params.append(model_name)
    if task_domain:
        clauses.append("task_domain = ?")
        params.append(task_domain)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return db.fetchall_dicts(
        f"SELECT * FROM v_delegation_stats {where} ORDER BY model_name, task_domain",
        params,
    )


def get_recent_delegations(
    db: AgentStateDB, limit: int = 20
) -> list[dict[str, Any]]:
    """Most recent delegation records."""
    return db.fetchall_dicts(
        "SELECT * FROM fact_delegation ORDER BY recorded_at DESC LIMIT ?",
        [limit],
    )
