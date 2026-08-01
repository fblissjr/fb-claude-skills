"""Recipes: analytical stance as data, not code.

A recipe is YAML frontmatter (parameters) plus a markdown body (the
`system_instruction`). Keeping the stance in a versioned file rather than
composing it fresh each session is what makes results reproducible -- combined
with `seed`, a rerun that disagrees with the last one is a real difference
rather than sampling noise.

Only fields the Interactions API actually accepts are passed through. The valid
`generation_config` keys were verified against the generated SDK types; note
that `temperature` is NOT among them, and that `service_tier`, `store`, and
`system_instruction` sit at the top level of the request, not inside
`generation_config`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Verified against google/genai/_gaos/types/interactions/generationconfig.py
GENERATION_CONFIG_KEYS = frozenset(
    {
        "max_output_tokens",
        "seed",
        "stop_sequences",
        "thinking_level",
        "thinking_summaries",
        "tool_choice",
        "transcription_config",
    }
)

THINKING_LEVELS = frozenset({"minimal", "low", "medium", "high"})
RESOLUTIONS = frozenset({"low", "medium", "high", "ultra_high"})
SERVICE_TIERS = frozenset({"flex", "standard", "priority"})

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class Recipe:
    name: str
    system_instruction: str
    model: str = "gemini-3.6-flash"
    thinking_level: str | None = None
    seed: int | None = None
    max_output_tokens: int | None = None
    resolution: str | None = None
    context_resolution: str | None = None
    service_tier: str | None = None
    stateful: bool = False
    background: bool = False
    schema: dict[str, Any] | None = None
    labels: dict[str, str] = field(default_factory=dict)
    path: Path | None = None

    def generation_config(self) -> dict[str, Any]:
        # Thinking runs by DEFAULT -- a bare call returns a 'thought' step and
        # bills those tokens at the output rate. Probed: 195 thought tokens for
        # "17 * 23" at `high` versus 0 at `minimal`. So an unset thinking_level
        # is the expensive path, not the cheap one, and recipes that do not care
        # must say `minimal` out loud.
        cfg = {
            "thinking_level": self.thinking_level or "minimal",
            "seed": self.seed,
            "max_output_tokens": self.max_output_tokens,
        }
        return {k: v for k, v in cfg.items() if v is not None}

    def response_format(self) -> dict[str, Any] | None:
        if not self.schema:
            return None
        return {
            "type": "text",
            "mime_type": "application/json",
            "schema": self.schema,
        }


def _validate(data: dict[str, Any], name: str) -> None:
    level = data.get("thinking_level")
    if level is not None and level not in THINKING_LEVELS:
        raise RecipeError(
            f"{name}: thinking_level {level!r} not in {sorted(THINKING_LEVELS)}"
        )
    for key in ("resolution", "context_resolution"):
        res = data.get(key)
        if res is not None and res not in RESOLUTIONS:
            raise RecipeError(f"{name}: {key} {res!r} not in {sorted(RESOLUTIONS)}")
    tier = data.get("service_tier")
    if tier is not None and tier not in SERVICE_TIERS:
        raise RecipeError(
            f"{name}: service_tier {tier!r} not in {sorted(SERVICE_TIERS)}"
        )
    # The constraint graph: background execution requires server-side storage,
    # and storage is what `stateful` turns on. Catch it here rather than
    # letting the API return a 400.
    if data.get("background") and not data.get("stateful"):
        raise RecipeError(
            f"{name}: background=true requires stateful=true "
            "(background execution needs store=true)"
        )
    if "temperature" in data:
        # Probed 2026-08-01: the API accepts temperature and silently ignores
        # it. At temperature 0.0 the same prompt still returns varying answers,
        # and 0.0 vs 2.0 produce identical answer sets. Reject it here rather
        # than let a recipe imply control it does not have.
        raise RecipeError(
            f"{name}: the Interactions API accepts temperature but ignores it "
            "(verified by probe). Use seed for reproducibility."
        )


def parse(text: str, name: str, path: Path | None = None) -> Recipe:
    match = _FRONTMATTER.match(text)
    if not match:
        raise RecipeError(f"{name}: missing YAML frontmatter delimited by ---")
    raw, body = match.groups()
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise RecipeError(f"{name}: frontmatter must be a mapping")

    body = body.strip()
    if not body:
        raise RecipeError(f"{name}: body is empty (it becomes system_instruction)")

    _validate(data, name)

    known = {f for f in Recipe.__dataclass_fields__ if f not in {"path", "name"}}
    unknown = set(data) - known - {"name", "description"}
    if unknown:
        raise RecipeError(f"{name}: unknown keys {sorted(unknown)}")

    kwargs = {k: v for k, v in data.items() if k in known}
    return Recipe(
        name=data.get("name", name),
        system_instruction=body,
        path=path,
        **kwargs,
    )


def load(name_or_path: str, search_dirs: list[Path]) -> Recipe:
    candidate = Path(name_or_path)
    if candidate.suffix and candidate.exists():
        return parse(candidate.read_text(), candidate.stem, candidate)

    for directory in search_dirs:
        hit = directory / f"{name_or_path}.md"
        if hit.exists():
            return parse(hit.read_text(), name_or_path, hit)

    available = sorted(
        p.stem for d in search_dirs if d.is_dir() for p in d.glob("*.md")
    )
    raise RecipeError(
        f"recipe {name_or_path!r} not found. Available: {available or 'none'}"
    )
