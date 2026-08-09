"""The spend gate: expensive calls need something a user typed.

The claim: a cheap call is untouched, an expensive one is refused unless a
user-typed slash command minted an authorization, and every way of failing to
verify one is a refusal rather than a pass.

That last part is the arm that matters most. The gate's failure mode is not a
crash, it is a **silent no-op** -- and this repo has already shipped that bug
once, in advisor's own hook, where a `command -v jq || exit 0` copied from a
fail-open hook turned the whole check off on any machine without jq. Nothing
was broken, nothing was logged, and the gate simply stopped existing. Several
arms below exist only to pin the direction of failure.

What is deliberately NOT claimed: that a token cannot be forged. It is a local
file and anything with Bash or Write can write one. The gate stops the normal
helpful path from spending at scale; it does not stop a determined agent, and
a test asserting otherwise would be testing a promise the design does not make.
"""

from __future__ import annotations

import orjson
import pytest

from gemini_bridge import authorization


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-test")
    return authorization.state_dir("s-test")


def mint(session, *, ts=1000.0, origin="user_typed_command", max_tokens=200000):
    """What the UserPromptExpansion hook writes. Kept in this shape on purpose:
    if the hook's payload changes, these arms should stop agreeing with it."""
    session.mkdir(parents=True, exist_ok=True)
    (session / authorization.AUTH_FILENAME).write_bytes(
        orjson.dumps({"ts": ts, "origin": origin, "max_tokens": max_tokens})
    )


# -- tiering ----------------------------------------------------------------


def test_ordinary_calls_are_not_gated():
    """A screenshot and a question must not need a slash command. Gating the
    common path is how a gate gets switched off."""
    tier, _ = authorization.classify(
        estimated_tokens=1120, thinking_level="minimal", stateful=False,
        max_unauthorized_tokens=20_000,
    )
    assert tier == "cheap"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"estimated_tokens": 50_000},
        {"thinking_level": "high"},
        {"thinking_level": "medium"},
        {"stateful": True},
    ],
)
def test_cost_or_irreversibility_triggers_the_gate(kwargs):
    """Three independent triggers: size, unbounded output-rate spend, and
    storage that the API cannot delete."""
    base = {
        "estimated_tokens": 100, "thinking_level": "minimal", "stateful": False,
        "max_unauthorized_tokens": 20_000,
    }
    tier, why = authorization.classify(**{**base, **kwargs})
    assert tier == "expensive"
    assert why, "a refusal has to be able to say which trigger fired"


def test_a_short_video_is_not_expensive_by_virtue_of_being_video():
    """Modality is not the criterion. A five-second clip is a few hundred
    tokens, and gating it would train people to disable the gate."""
    tier, _ = authorization.classify(
        estimated_tokens=350, thinking_level="minimal", stateful=False,
        max_unauthorized_tokens=20_000,
    )
    assert tier == "cheap"


# -- claiming ---------------------------------------------------------------


def test_a_minted_authorization_allows_one_call(session):
    mint(session)
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert d.allowed and d.tier == "expensive-authorized"


def test_an_authorization_is_single_use(session):
    """One approval funds one call. Without this, a single yes is a standing
    licence for the rest of the session."""
    mint(session)
    assert authorization.claim(
        estimated_tokens=50_000, ttl_seconds=600, now=1100.0).allowed
    assert not authorization.claim(
        estimated_tokens=50_000, ttl_seconds=600, now=1100.0).allowed


def test_no_authorization_is_a_refusal(session):
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert not d.allowed
    assert authorization.AUTHORIZE_COMMAND in d.reason


def test_expiry_is_enforced(session):
    """An approval from earlier should not silently fund a call the user has
    stopped thinking about."""
    mint(session, ts=1000.0)
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=2000.0)
    assert not d.allowed and "expired" in d.reason


def test_a_token_without_user_provenance_is_refused(session):
    """The origin field is the whole mechanism. A token the agent wrote itself
    -- by running a script, or by copying the shape out of the docs -- carries
    something else here and must not pass."""
    mint(session, origin="script")
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert not d.allowed and "provenance" in d.reason


def test_the_ceiling_stops_approve_small_send_huge(session):
    """Without a ceiling the approval is a blank cheque and the user's control
    over spend is nominal."""
    mint(session, max_tokens=30_000)
    d = authorization.claim(estimated_tokens=500_000, ttl_seconds=600, now=1100.0)
    assert not d.allowed
    assert "--max-tokens" in d.reason, "the refusal must say how to proceed"


def test_a_corrupt_token_is_refused_not_ignored(session):
    """The direction of failure is the point. Unreadable must mean no, or the
    gate is one bad write away from not existing."""
    session.mkdir(parents=True, exist_ok=True)
    (session / authorization.AUTH_FILENAME).write_text("{not json")
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert not d.allowed


def test_a_refused_claim_still_consumes_the_token(session):
    """A rejected token must not sit there for the next attempt to retry
    against -- a loop that keeps trying would eventually find a valid one."""
    mint(session, origin="script")
    authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert not (session / authorization.AUTH_FILENAME).exists()


def test_outside_an_agent_session_the_gate_stands_down(tmp_path, monkeypatch):
    """Someone typing this into their own shell IS the authorization. Gating
    them would make the tool unusable outside an agent -- and this is the
    documented sidestep, not a hidden one."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    d = authorization.claim(estimated_tokens=999_999, ttl_seconds=600, now=1.0)
    assert d.allowed and d.tier == "expensive-ungated"


def test_the_refusal_never_tells_claude_to_fix_it_itself(session):
    """Phrasing is load-bearing. A refusal reading as "authorize this first" is
    an instruction the main loop will helpfully follow, and the surprise spend
    comes straight back. It has to terminate in a human."""
    d = authorization.claim(estimated_tokens=50_000, ttl_seconds=600, now=1100.0)
    assert "they will run" in d.reason
    assert "do not disable the gate" in d.reason.lower()
    assert "do not retry" in d.reason.lower()
