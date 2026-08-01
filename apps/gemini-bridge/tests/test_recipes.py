from __future__ import annotations

import pytest

from gemini_bridge import recipes

MINIMAL = """\
---
model: gemini-3.6-flash
---

Compare things.
"""


def parse(text: str, name: str = "t"):
    return recipes.parse(text, name)


def test_body_becomes_system_instruction():
    r = parse(MINIMAL)
    assert r.system_instruction == "Compare things."
    assert r.model == "gemini-3.6-flash"


def test_empty_body_rejected():
    with pytest.raises(recipes.RecipeError, match="body is empty"):
        parse("---\nmodel: x\n---\n\n   \n")


def test_missing_frontmatter_rejected():
    with pytest.raises(recipes.RecipeError, match="frontmatter"):
        parse("just a body")


def test_temperature_rejected_because_api_ignores_it():
    # Probed live: the API accepts temperature and silently does nothing with
    # it. A recipe implying control it does not have is worse than an error.
    with pytest.raises(recipes.RecipeError, match="ignores it"):
        parse("---\ntemperature: 0.2\n---\n\nbody\n")


def test_thinking_defaults_to_minimal_not_unset():
    # Thinking runs by default server-side and bills at the OUTPUT rate, so an
    # unset level is the expensive path. Recipes must opt in, not out.
    assert parse(MINIMAL).generation_config()["thinking_level"] == "minimal"


def test_explicit_thinking_level_survives():
    r = parse("---\nmodel: m\nthinking_level: high\n---\n\nbody\n")
    assert r.generation_config()["thinking_level"] == "high"


def test_invalid_thinking_level_rejected():
    with pytest.raises(recipes.RecipeError, match="thinking_level"):
        parse("---\nthinking_level: maximum\n---\n\nbody\n")


def test_invalid_resolution_rejected():
    with pytest.raises(recipes.RecipeError, match="resolution"):
        parse("---\nresolution: enormous\n---\n\nbody\n")


@pytest.mark.parametrize("stateful", ["true", "false"])
def test_background_rejected_entirely(stateful):
    # `background` was accepted and validated but never sent, so setting it
    # passed validation and changed nothing. Rejected outright until the call
    # path implements it, rather than left as an inert promise.
    with pytest.raises(recipes.RecipeError, match="not implemented"):
        parse(f"---\nbackground: true\nstateful: {stateful}\n---\n\nbody\n")


def test_unknown_key_rejected():
    with pytest.raises(recipes.RecipeError, match="unknown keys"):
        parse("---\nwidth: 4\n---\n\nbody\n")


def test_response_format_shape():
    r = parse("---\nschema:\n  type: object\n---\n\nbody\n")
    fmt = r.response_format()
    assert fmt == {
        "type": "text",
        "mime_type": "application/json",
        "schema": {"type": "object"},
    }


def test_no_schema_means_no_response_format():
    assert parse(MINIMAL).response_format() is None


def test_shipped_recipe_is_valid():
    from pathlib import Path

    shipped = (
        Path(__file__).resolve().parents[1]
        / "skills/gemini-multimodal/references/recipes/perceptual-diff.md"
    )
    r = recipes.parse(shipped.read_text(), shipped.stem, shipped)
    assert r.stateful is False, "storage cannot be undone: delete returns 501"
    assert r.resolution == "low", "validated as sufficient by the control harness"
    assert r.response_format() is not None
