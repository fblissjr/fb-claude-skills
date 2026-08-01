"""The call path.

Everything here was verified against live API behaviour on 2026-08-01, not
against documentation -- the docs, the OpenAPI spec, and the generated SDK types
each turned out to be wrong about something material. See
docs/internals/gemini_bridge_design.md.

Load-bearing findings encoded below:

- `temperature` is accepted and silently ignored, so it is never sent.
- Thinking runs by DEFAULT and bills at the output rate. An unset
  `thinking_level` is the expensive path; recipes default to `minimal`.
- `status: "incomplete"` means truncated at max_output_tokens. It is a terminal
  state distinct from failure and must not read as success.
- `system_instruction` and `generation_config` are interaction-scoped: a
  follow-up that omits them silently runs with neither.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import orjson

from .media import Attachment, to_content_block
from .recipes import Recipe

# Terminal states, from the API's own status enum.
TERMINAL_OK = "completed"
TERMINAL_TRUNCATED = "incomplete"


class CallError(RuntimeError):
    pass


class TruncatedError(CallError):
    """Model hit max_output_tokens. Output exists but is cut off."""


@dataclass
class Result:
    text: str
    status: str
    usage: dict[str, Any]
    interaction_id: str | None
    request: dict[str, Any]
    duration_ms: int
    structured: Any | None = None
    warnings: list[str] = field(default_factory=list)


def _usage_dict(interaction: Any) -> dict[str, Any]:
    u = getattr(interaction, "usage", None)
    if u is None:
        return {}
    if hasattr(u, "model_dump"):
        return {k: v for k, v in u.model_dump().items() if v is not None}
    try:
        return dict(u)
    except TypeError:
        return {}


def build_request(
    recipe: Recipe,
    question: str,
    attachments: list[Attachment],
    *,
    previous_interaction_id: str | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    """Assemble the create() kwargs.

    Media first, then the question: the prompt reads as instructions about
    material already presented, which is how the doc examples order it.
    """
    content: list[dict[str, Any]] = [to_content_block(a) for a in attachments]
    content.append({"type": "text", "text": question})

    request: dict[str, Any] = {
        "model": model_override or recipe.model,
        "input": content,
        "system_instruction": recipe.system_instruction,
        # Storage is the only privacy lever that exists: interactions.delete
        # returns 501 Not Implemented, so anything stored is stored for the
        # full project retention window and cannot be purged.
        "store": recipe.stateful,
    }

    generation_config = recipe.generation_config()
    if generation_config:
        request["generation_config"] = generation_config

    response_format = recipe.response_format()
    if response_format:
        request["response_format"] = response_format

    if recipe.service_tier:
        request["service_tier"] = recipe.service_tier
    if recipe.labels:
        request["labels"] = recipe.labels

    if previous_interaction_id:
        if not recipe.stateful:
            raise CallError(
                "cannot continue an interaction with a stateless recipe: "
                "previous_interaction_id requires store=true"
            )
        request["previous_interaction_id"] = previous_interaction_id

    return request


def redact_for_record(request: dict[str, Any], attachments: list[Attachment]) -> dict[str, Any]:
    """The request as written to request.json -- manifest, never payloads.

    Base64 media would make the record enormous and would duplicate files that
    already exist on disk at known paths.
    """
    record = {k: v for k, v in request.items() if k != "input"}
    record["input"] = {
        "attachments": [a.manifest_entry() for a in attachments],
        "text_blocks": [
            b.get("text") for b in request["input"] if b.get("type") == "text"
        ],
    }
    return record


def call(client: Any, request: dict[str, Any]) -> Result:
    started = time.monotonic()
    interaction = client.interactions.create(**request)
    duration_ms = int((time.monotonic() - started) * 1000)

    status = str(getattr(interaction, "status", "") or TERMINAL_OK)
    text = getattr(interaction, "output_text", None) or ""
    warnings: list[str] = []

    if status == TERMINAL_TRUNCATED:
        warnings.append(
            "response was truncated at max_output_tokens (status=incomplete); "
            "structured output may be unparseable and any verdict is partial"
        )

    structured = None
    if request.get("response_format"):
        try:
            structured = orjson.loads(text)
        except orjson.JSONDecodeError as exc:
            if status == TERMINAL_TRUNCATED:
                raise TruncatedError(
                    "structured output is incomplete: the model hit "
                    "max_output_tokens before closing the JSON. Raise "
                    "max_output_tokens or simplify the schema."
                ) from exc
            raise CallError(
                f"response_format was requested but the reply is not valid JSON: {exc}"
            ) from exc

    return Result(
        text=text,
        status=status,
        usage=_usage_dict(interaction),
        interaction_id=getattr(interaction, "id", None) if request.get("store") else None,
        request=request,
        duration_ms=duration_ms,
        structured=structured,
        warnings=warnings,
    )


def count_input_tokens(client: Any, model: str, attachments: list[Attachment], question: str) -> int | None:
    """Pre-flight estimate for --dry-run.

    Uses a DIFFERENT API surface than the real call: count_tokens lives on
    client.models and takes `contents=`, while the call is
    client.interactions.create(input=). Probed as exact for text; unverified for
    media, so a None return means "unknown", never "zero".
    """
    try:
        contents: list[Any] = []
        for a in attachments:
            block = to_content_block(a)
            contents.append(
                {"inline_data": {"mime_type": block["mime_type"], "data": block["data"]}}
            )
        contents.append(question)
        counted = client.models.count_tokens(model=model, contents=contents)
        return getattr(counted, "total_tokens", None)
    except Exception:  # noqa: BLE001 - an estimate must never block the real call
        return None
