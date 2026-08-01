"""Tests for the call path.

These exist because two critical bugs lived here and neither was covered:
`call()` raised after a successful API call, discarding the interaction id, and
only two of the eight real status values were handled.

A fake interaction is enough. The contract under test is entirely about what
`call()` does with what the SDK hands back, so no network is involved.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from gemini_bridge import client as call_mod
from gemini_bridge.recipes import Recipe

SCHEMA_REQUEST = {
    "model": "m",
    "input": [{"type": "text", "text": "q"}],
    "store": True,
    "response_format": {"type": "text", "mime_type": "application/json"},
}


class FakeInteractions:
    def __init__(self, interaction):
        self._interaction = interaction

    def create(self, **_kwargs):
        return self._interaction


def fake_client(*, status="completed", text="{}", interaction_id="v1_abc"):
    return SimpleNamespace(
        interactions=FakeInteractions(
            SimpleNamespace(
                id=interaction_id,
                status=status,
                output_text=text,
                usage=SimpleNamespace(
                    model_dump=lambda: {"total_input_tokens": 7, "total_thought_tokens": 0}
                ),
            )
        )
    )


# -- the critical invariant -------------------------------------------------


@pytest.mark.parametrize(
    "status,text",
    [
        ("incomplete", '{"identical": tru'),  # truncated mid-JSON
        ("failed", ""),
        ("cancelled", ""),
        ("budget_exceeded", ""),
        ("completed", "not json at all"),
        ("in_progress", ""),
        ("some_future_status", ""),
    ],
)
def test_never_raises_after_the_api_responded(status, text):
    """The id must survive every bad response.

    Once `create` returns, the interaction is billed and possibly stored, and
    stored interactions cannot be deleted. Raising here discarded the only
    handle that would ever exist for it.
    """
    result = call_mod.call(fake_client(status=status, text=text), SCHEMA_REQUEST)
    assert result.interaction_id == "v1_abc"
    assert result.usage["total_input_tokens"] == 7
    assert result.ok is False


def test_id_kept_even_when_store_was_not_requested():
    # If the server stored it anyway, that is precisely the case we must not
    # lose track of.
    request = dict(SCHEMA_REQUEST, store=False)
    result = call_mod.call(fake_client(), request)
    assert result.interaction_id == "v1_abc"


# -- status handling --------------------------------------------------------


def test_success_is_clean():
    result = call_mod.call(fake_client(text='{"identical": true}'), SCHEMA_REQUEST)
    assert result.ok
    assert result.structured == {"identical": True}
    assert result.warnings == []
    assert result.parse_error is None


def test_api_failure_is_not_reported_as_a_parser_problem():
    """A failed interaction returns empty output.

    Parsing that and reporting "not valid JSON" blamed the parser for an
    API-side failure and buried the status, which was the only explanation.
    """
    result = call_mod.call(fake_client(status="failed", text=""), SCHEMA_REQUEST)
    assert "status=failed" in result.parse_error
    assert any("status=failed" in w for w in result.warnings)


def test_truncation_says_what_to_do_about_it():
    result = call_mod.call(
        fake_client(status="incomplete", text='{"a": 1'), SCHEMA_REQUEST
    )
    assert "max_output_tokens" in result.parse_error
    assert any("truncated" in w for w in result.warnings)


def test_non_terminal_status_warns_that_no_polling_happens():
    result = call_mod.call(fake_client(status="queued", text=""), SCHEMA_REQUEST)
    assert any("does not poll" in w for w in result.warnings)


def test_no_schema_means_no_parse_error():
    request = {k: v for k, v in SCHEMA_REQUEST.items() if k != "response_format"}
    result = call_mod.call(fake_client(text="free prose"), request)
    assert result.ok
    assert result.parse_error is None
    assert result.structured is None


# -- request assembly -------------------------------------------------------


def recipe(**kw):
    return Recipe(name="r", system_instruction="do the thing", **kw)


def test_stateless_recipe_refuses_to_continue_an_interaction():
    with pytest.raises(call_mod.CallError, match="requires store=true"):
        call_mod.build_request(
            recipe(stateful=False), "q", [], previous_interaction_id="v1_x"
        )


def test_stateful_recipe_carries_the_previous_id():
    request = call_mod.build_request(
        recipe(stateful=True), "q", [], previous_interaction_id="v1_x"
    )
    assert request["previous_interaction_id"] == "v1_x"
    assert request["store"] is True


def test_store_follows_stateful():
    assert call_mod.build_request(recipe(stateful=False), "q", [])["store"] is False


def test_temperature_is_never_sent():
    request = call_mod.build_request(recipe(seed=1), "q", [])
    assert "temperature" not in request.get("generation_config", {})


def test_thinking_defaults_to_minimal_in_the_request():
    request = call_mod.build_request(recipe(), "q", [])
    assert request["generation_config"]["thinking_level"] == "minimal"


def test_model_override_wins():
    request = call_mod.build_request(recipe(), "q", [], model_override="other")
    assert request["model"] == "other"


def test_record_strips_payloads_but_keeps_the_question():
    request = call_mod.build_request(recipe(), "the question", [])
    record = call_mod.redact_for_record(request, [])
    assert record["input"]["text_blocks"] == ["the question"]
    assert "data" not in str(record)
