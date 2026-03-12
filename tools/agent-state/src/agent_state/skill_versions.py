"""Skill version lineage tracking."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import orjson

from agent_state.database import AgentStateDB


def compute_skill_hash(skill_path: str | Path) -> str:
    """Compute SHA-256 content hash of a SKILL.md file."""
    content = Path(skill_path).read_bytes()
    return hashlib.sha256(content).hexdigest()


def get_or_create_skill_version(
    db: AgentStateDB,
    skill_name: str,
    version_hash: str,
    *,
    skill_path: str | None = None,
    repo_root: str | None = None,
    token_count: int | None = None,
    is_valid: bool | None = None,
    created_by_run_id: str | None = None,
    domain: str | None = None,
    task_type: str | None = None,
    status: str | None = "active",
    metadata: dict[str, Any] | None = None,
) -> int:
    """Get existing skill version by hash, or create a new one. Returns skill_version_id."""
    existing = db.fetchone(
        "SELECT skill_version_id FROM dim_skill_version WHERE skill_name = ? AND version_hash = ?",
        [skill_name, version_hash],
    )
    if existing:
        return existing[0]

    metadata_json = orjson.dumps(metadata).decode() if metadata else None
    result = db.fetchone(
        """
        INSERT INTO dim_skill_version (
            skill_name, skill_path, version_hash, repo_root,
            token_count, is_valid, created_by_run_id,
            domain, task_type, status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING skill_version_id
        """,
        [skill_name, skill_path, version_hash, repo_root,
         token_count, is_valid, created_by_run_id,
         domain, task_type, status, metadata_json],
    )
    return result[0]


def get_skill_versions(
    db: AgentStateDB, skill_name: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Get version history for a skill."""
    return db.fetchall_dicts(
        """
        SELECT sv.*, fr.run_name AS created_by_run_name
        FROM dim_skill_version sv
        LEFT JOIN fact_run fr ON sv.created_by_run_id = fr.run_id
        WHERE sv.skill_name = ?
        ORDER BY sv.skill_version_id DESC
        LIMIT ?
        """,
        [skill_name, limit],
    )


def get_skill_version_by_hash(
    db: AgentStateDB, version_hash: str
) -> dict[str, Any] | None:
    """Look up a skill version by its content hash."""
    rows = db.fetchall_dicts(
        "SELECT * FROM dim_skill_version WHERE version_hash = ?",
        [version_hash],
    )
    return rows[0] if rows else None


def get_active_skill(
    db: AgentStateDB, skill_name: str
) -> dict[str, Any] | None:
    """Get the latest active version of a skill."""
    rows = db.fetchall_dicts(
        """
        SELECT * FROM dim_skill_version
        WHERE skill_name = ? AND status = 'active'
        ORDER BY skill_version_id DESC
        LIMIT 1
        """,
        [skill_name],
    )
    return rows[0] if rows else None


def deprecate_skill_version(db: AgentStateDB, skill_version_id: int) -> None:
    """Mark a skill version as deprecated."""
    db.execute(
        "UPDATE dim_skill_version SET status = 'deprecated' WHERE skill_version_id = ?",
        [skill_version_id],
    )


def get_skills_by_domain(
    db: AgentStateDB, domain: str, task_type: str | None = None
) -> list[dict[str, Any]]:
    """Find active skills by domain and optional task_type."""
    if task_type:
        return db.fetchall_dicts(
            """
            SELECT * FROM dim_skill_version
            WHERE domain = ? AND task_type = ? AND status = 'active'
            ORDER BY skill_version_id DESC
            """,
            [domain, task_type],
        )
    return db.fetchall_dicts(
        """
        SELECT * FROM dim_skill_version
        WHERE domain = ? AND status = 'active'
        ORDER BY skill_version_id DESC
        """,
        [domain],
    )
