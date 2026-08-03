"""Append-only call ledger.

Every call is recorded with **derived** facts only -- what the API actually
reported, never a self-assessment. This is the discipline argued for in
docs/internals/model_routing_flywheel.md: the reason that document says the
delegation feedback layer is a report rather than a loop is that its fields are
self-graded by the party being evaluated, and carry no cost data.

Deliberately NOT written into `fact_delegation` yet. That table requires an
`outcome` (accepted / revised / redone / escalated), which is unknowable at call
time, and it has no columns for tokens or dollars. Forcing rows in would
reproduce the "schema speaks a different language than the rule" flaw the
flywheel document identifies. The JSONL here carries the fields that matter and
replays cleanly into the table once its grain widens to routing decisions and it
grows cost columns.

`outcome` is left absent rather than guessed. A later `gemini-bridge judge`
step, or a human, can append a verdict row keyed by `run_id`.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

import orjson

LEDGER_NAME = "ledger.jsonl"


def _pricing_note() -> str:
    """Why no dollar figure is computed here.

    Prices change and are not knowable offline; a stale constant in code is
    worse than no number because it looks authoritative. Token counts are
    facts, so they are recorded and cost is derived later against a refreshed
    price table.
    """
    return "tokens recorded; cost derived downstream against current pricing"


def record(
    runs_root: Path,
    *,
    run_id: str,
    recipe: str,
    model: str,
    status: str,
    usage: dict[str, Any] | None,
    attachments: list[dict[str, Any]],
    duration_ms: int,
    stateful: bool,
    service_tier: str | None,
    thinking_level: str | None,
    credential_kind: str,
    error: str | None = None,
    allow_prompt_secrets: bool = False,
    prompt_scanned: bool = True,
    interaction_id: str | None = None,
) -> Path:
    """Append one call record. Never raises -- logging must not break the call."""
    path = runs_root / LEDGER_NAME
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": run_id,
        "recipe": recipe,
        "model": model,
        "status": status,
        "duration_ms": duration_ms,
        "stateful": stateful,
        "service_tier": service_tier,
        "thinking_level": thinking_level,
        # Provenance only. A key command names a vault and item, so the
        # reference itself never reaches disk.
        "credential_kind": credential_kind,
        # The handle to anything the server kept. Recorded here and not only in
        # the run directory because deleting a run directory would otherwise
        # destroy the only local record of a stored interaction -- and the API
        # offers no `list` to rebuild it and no working `delete` to act on it.
        # Without this, pruning run dirs silently blinds `stored`, which is the
        # only disclosure surface a user has. Not a secret: an opaque pointer to
        # data already sent, already on disk in the run dir's `interaction.id`.
        "interaction_id": interaction_id,
        # False means the outgoing text was NEVER CHECKED, whatever the route
        # -- the CLI flag or a project config with scan_prompt = false. This is
        # the field to filter on when hunting unscanned runs: the flag below
        # records only the CLI route, and for a release the config route
        # produced rows saying allow_prompt_secrets: false for runs that were
        # never scanned -- the audit field pointing away from the runs it
        # exists to find. False does not mean a secret was present; it means
        # nobody looked, the run dir holds the text in plaintext locally, and
        # the interaction at Google cannot be deleted.
        "prompt_scanned": prompt_scanned,
        # Which route: True when --allow-prompt-secrets was passed on this
        # call. Kept alongside prompt_scanned because a deliberate one-off
        # bypass and a standing config opt-out are different facts about a run.
        "allow_prompt_secrets": allow_prompt_secrets,
        "attachments": [
            {k: a.get(k) for k in ("kind", "mime_type", "size_bytes", "resolution")}
            for a in attachments
        ],
        "usage": usage or {},
        "pricing": _pricing_note(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID"),
        "error": error,
    }
    try:
        with path.open("ab") as fh:
            fh.write(orjson.dumps(entry) + b"\n")
    except OSError:
        pass  # a failed log must never fail a call
    return path


def read(runs_root: Path) -> list[dict[str, Any]]:
    path = runs_root / LEDGER_NAME
    if not path.is_file():
        return []
    out = []
    for line in path.read_bytes().splitlines():
        if line.strip():
            try:
                out.append(orjson.loads(line))
            except orjson.JSONDecodeError:
                continue  # a corrupt line should not hide the rest
    return out


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate for `gemini-bridge stats`. Counts and tokens, no invented dollars."""
    by_recipe: dict[str, dict[str, int]] = {}
    for e in entries:
        u = e.get("usage") or {}
        bucket = by_recipe.setdefault(
            e.get("recipe", "?"),
            {"calls": 0, "input": 0, "output": 0, "thought": 0, "errors": 0},
        )
        bucket["calls"] += 1
        bucket["input"] += u.get("total_input_tokens") or 0
        bucket["output"] += u.get("total_output_tokens") or 0
        bucket["thought"] += u.get("total_thought_tokens") or 0
        if e.get("status") != "completed":
            bucket["errors"] += 1
    return by_recipe
