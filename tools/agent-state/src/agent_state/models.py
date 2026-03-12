"""Dataclasses for agent-state records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class RunType(str, Enum):
    PIPELINE = "pipeline"
    AGENT_SDK = "agent_sdk"
    CLAUDE_CODE = "claude_code"


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class SkillStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class MessageLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class RunRecord:
    run_id: str
    run_type: str
    run_name: str
    started_at: datetime
    status: str = RunStatus.RUNNING
    parent_run_id: str | None = None
    correlation_id: str | None = None
    source_key: str | None = None
    run_description: str | None = None
    source_type: str | None = None
    source_identifier: str | None = None
    destination_type: str | None = None
    destination_identifier: str | None = None
    consumes_skill_version_id: int | None = None
    produces_skill_version_id: int | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    extract_count: int = 0
    insert_count: int = 0
    update_count: int = 0
    delete_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    total_cost_usd: float | None = None
    num_turns: int | None = None
    model_name: str | None = None
    cdc_type: str | None = None
    cdc_column: str | None = None
    cdc_low_watermark: str | None = None
    cdc_high_watermark: str | None = None
    is_restartable: bool = True
    restart_from_run_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class RunMessage:
    run_id: str
    level: str
    message: str
    message_id: int | None = None
    logged_at: datetime | None = None
    category: str | None = None
    detail: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class WatermarkRecord:
    watermark_source_key: str
    current_value: str
    changed: bool = False
    watermark_id: int | None = None
    run_id: str | None = None
    checked_at: datetime | None = None
    watermark_type: str | None = None
    previous_value: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class SkillVersion:
    skill_name: str
    version_hash: str
    skill_version_id: int | None = None
    skill_path: str | None = None
    repo_root: str | None = None
    token_count: int | None = None
    is_valid: bool | None = None
    created_at: datetime | None = None
    created_by_run_id: str | None = None
    domain: str | None = None
    task_type: str | None = None
    status: str | None = "active"
    metadata: dict[str, Any] | None = None


@dataclass
class StagedWatermark:
    """Watermark staged during a run, committed only on success."""
    source_key: str
    source_type: str
    identifier: str
    display_name: str | None
    watermark_type: str
    new_value: str
    metadata: dict[str, Any] | None = None
