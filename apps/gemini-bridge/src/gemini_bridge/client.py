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

# The full status set, taken from the SDK's InteractionStatus type rather than
# from the two values the docs happen to mention. Treating anything outside
# {completed, incomplete} as an unlabelled success was hiding real failures: a
# `failed` interaction returns empty output_text, and parsing that as JSON
# surfaced "the reply is not valid JSON", which blames the parser for an
# API-side failure and buries the one signal that explains it.
TERMINAL_OK = "completed"
TERMINAL_TRUNCATED = "incomplete"
TERMINAL_FAILED = frozenset({"failed", "cancelled", "budget_exceeded"})
NON_TERMINAL = frozenset({"in_progress", "queued", "requires_action"})


class CallError(RuntimeError):
    pass


# There is deliberately no TruncatedError. Truncation is reported on the Result
# as `parse_error`, not raised: raising after `interactions.create` returns
# discards the interaction id, and a stored interaction cannot be deleted.


@dataclass
class Result:
    """Always returned once the API call has happened, even on a bad response.

    `call()` deliberately does not raise after `interactions.create` returns.
    The interaction is billed by then, and if it was stored it cannot be
    deleted (the delete endpoint returns 501), so the id is the only handle
    that will ever exist for it. Raising discarded that id into a local
    variable and left an untracked, permanent, paid interaction with no record
    anywhere. Failures are reported in `parse_error` and `warnings`; the caller
    persists first and decides the exit code after.
    """

    text: str
    status: str
    usage: dict[str, Any]
    interaction_id: str | None
    duration_ms: int
    structured: Any | None = None
    warnings: list[str] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == TERMINAL_OK and self.parse_error is None


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
        # Storage is the only privacy lever that exists: interactions.delete
        # returns 501 Not Implemented, so anything stored is stored for the
        # full project retention window and cannot be purged.
        "store": recipe.stateful,
    }

    # Ad-hoc calls carry no stance. The field is interaction-scoped and its
    # tokens are billed, so an empty string is omitted rather than sent.
    if recipe.system_instruction:
        request["system_instruction"] = recipe.system_instruction

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


def redact_for_record(
    request: dict[str, Any],
    attachments: list[Attachment],
    project_root: Any = None,
) -> dict[str, Any]:
    """The request as written to request.json -- manifest, never payloads.

    Base64 media would make the record enormous and would duplicate files that
    already exist on disk at known paths.
    """
    record = {k: v for k, v in request.items() if k != "input"}
    record["input"] = {
        "attachments": [a.manifest_entry(project_root) for a in attachments],
        "text_blocks": [
            b.get("text") for b in request["input"] if b.get("type") == "text"
        ],
    }
    return record


def call(client: Any, request: dict[str, Any]) -> Result:
    """Make the call. Raises only if the call itself failed to happen.

    Once `create` returns, everything is reported through the Result. See the
    Result docstring for why nothing after this point may raise.
    """
    started = time.monotonic()
    interaction = client.interactions.create(**request)
    duration_ms = int((time.monotonic() - started) * 1000)

    # Capture the irreplaceable facts BEFORE anything that could go wrong.
    # The id is kept whenever the server returned one, not only when we asked
    # for storage: if `store` was misreported, an untracked stored interaction
    # is exactly what we must not lose.
    interaction_id = getattr(interaction, "id", None)
    usage = _usage_dict(interaction)
    status = str(getattr(interaction, "status", "") or TERMINAL_OK)
    text = getattr(interaction, "output_text", None) or ""

    warnings: list[str] = []
    if status == TERMINAL_TRUNCATED:
        warnings.append(
            "response was truncated at max_output_tokens (status=incomplete); "
            "structured output may be unparseable and any verdict is partial"
        )
    elif status in TERMINAL_FAILED:
        warnings.append(
            f"the API reported status={status}; output is likely empty and any "
            "verdict should be discarded"
        )
    elif status in NON_TERMINAL:
        warnings.append(
            f"the API returned status={status}, which is not a terminal state. "
            "This tool does not poll, so the eventual answer will not be "
            "retrieved. The interaction id is recorded."
        )
    elif status != TERMINAL_OK:
        warnings.append(f"unrecognised status={status}; treating as non-success")

    structured = None
    parse_error = None
    if request.get("response_format"):
        try:
            structured = orjson.loads(text)
        except orjson.JSONDecodeError as exc:
            if status == TERMINAL_TRUNCATED:
                parse_error = (
                    "structured output is incomplete: the model hit "
                    "max_output_tokens before closing the JSON. Raise "
                    "max_output_tokens or simplify the schema."
                )
            elif status != TERMINAL_OK:
                # Blaming the parser here would bury the real signal.
                parse_error = (
                    f"no parseable output because the API reported status={status}"
                )
            else:
                parse_error = (
                    f"response_format was requested but the reply is not valid "
                    f"JSON: {exc}"
                )

    return Result(
        text=text,
        status=status,
        usage=usage,
        interaction_id=interaction_id,
        duration_ms=duration_ms,
        structured=structured,
        warnings=warnings,
        parse_error=parse_error,
    )


# There is deliberately no pre-flight token estimator here.
#
# `client.models.count_tokens` was written and then removed: counting media
# requires UPLOADING it, so a `--dry-run` that called it would send exactly the
# files the flag exists to avoid sending. That is a worse failure than having no
# estimate, because the flag's whole purpose is to promise nothing left the
# machine.
#
# `--dry-run` is therefore local-only: it prints the manifest and parameters and
# opens no connection. Real token counts come from `usage` on the response,
# which is exact and costs nothing extra. Given a comparison runs about a tenth
# of a cent, a pre-flight estimate was solving a problem that does not exist.
