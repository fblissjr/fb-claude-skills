"""The spend gate: expensive calls need something a user typed.

The ordinary protection on this CLI is Claude Code's Bash permission prompt.
That is a real gate, but it is one a user can allowlist away or click through,
and it does not distinguish "look at this screenshot" from "upload forty
minutes of video". This module adds a second tier for the calls where being
wrong costs money or cannot be undone.

**The split matters.** Minting happens in a `UserPromptExpansion` hook, which
only a user-typed slash command can reach -- the main loop cannot fire that
event. Enforcement happens *here*, in the CLI, rather than in a `PreToolUse`
hook, for two reasons the design record already argued: the CLI is the
narrower chokepoint (it also covers manual, scripted, and subagent callers, on
machines where the hook is not installed at all), and a hook would have to
recognise an expensive call by parsing a bash command line, which quoting and
env prefixes make unreliable. The tier decision needs the resolved
attachments, and only the CLI has those.

**Fails closed.** If the tier is expensive and the authorization cannot be
verified for any reason -- missing, expired, malformed, unreadable -- the call
is refused. The mistake to avoid is the one advisor's own hook made once: a
convenience-shaped `except: pass` at the top turns the whole gate into a no-op
under an ops condition nobody notices.

**Honest limit, stated because a security control that oversells itself is
worse than none.** The authorization is a local file. Anything holding Bash or
Write can fabricate one, and a caller can drop `CLAUDE_SESSION_ID` to look like
a human at a terminal. This does not stop a determined agent and is not trying
to. What it guarantees is that nothing on the *normal, helpful* path spends
money at scale: an eager agent that would happily upload the whole recording
now has to be told to, by a human, in a way it cannot arrange for itself. That
is the actual failure mode.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

STATE_ROOT_NAME = "claude-gemini-bridge"
AUTH_FILENAME = "authorization.json"
REQUIRED_ORIGIN = "user_typed_command"

# The slash command a human types. Named in every refusal, because a refusal
# that does not say how to proceed just gets worked around.
AUTHORIZE_COMMAND = "/gemini-bridge:gemini-authorize"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""
    # What the gate concluded, for the ledger. Distinguishing "cheap, never
    # gated" from "expensive and authorized" is the difference between an audit
    # trail and a column of the same word.
    tier: str = "cheap"


def session_id() -> str | None:
    """The Claude Code session, or None when not running under one.

    Absence is treated as a direct human invocation and is not gated: someone
    typing this into their own shell *is* the authorization, and gating them
    would make the feature unusable outside an agent. That also means the gate
    can be sidestepped by unsetting the variable -- see the module docstring on
    what this does and does not defend against.
    """
    return os.environ.get("CLAUDE_SESSION_ID") or None


def state_dir(sid: str) -> Path:
    base = Path(os.environ.get("TMPDIR", "/tmp"))
    return base / STATE_ROOT_NAME / sid


def _read(path: Path) -> dict[str, Any] | None:
    try:
        data = orjson.loads(path.read_bytes())
    except (OSError, orjson.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def classify(
    *,
    estimated_tokens: int,
    thinking_level: str | None,
    stateful: bool,
    max_unauthorized_tokens: int,
) -> tuple[str, str]:
    """(tier, why). Cost and irreversibility, not modality.

    Deliberately not "video is expensive": a five-second clip is a few hundred
    tokens, and gating it would train people to switch the gate off, which
    costs more than it saves. What earns a gate is a call that is large, or one
    that cannot be taken back.
    """
    if stateful:
        return "expensive", (
            "--store keeps the interaction server-side, and "
            "interactions.delete returns 501 -- it cannot be undone"
        )
    if thinking_level in {"medium", "high"}:
        return "expensive", (
            f"thinking_level={thinking_level} bills at the output rate with no "
            "ceiling on how much of it the model uses"
        )
    if estimated_tokens > max_unauthorized_tokens:
        return "expensive", (
            f"~{estimated_tokens:,} estimated input tokens, over the "
            f"{max_unauthorized_tokens:,} limit for an unauthorized call"
        )
    return "cheap", ""


def claim(
    *,
    estimated_tokens: int,
    ttl_seconds: int,
    now: float | None = None,
) -> Decision:
    """Spend the session's authorization, or explain why the call is refused.

    Single-use, claimed by rename before validation. Parallel tool calls are a
    supported pattern, so two expensive calls in one turn could otherwise both
    read the same still-present token and both proceed -- one approval funding
    two sends. Only the process that wins the rename continues.
    """
    now = time.time() if now is None else now
    sid = session_id()
    if sid is None:
        return Decision(
            allowed=True, tier="expensive-ungated",
            reason="no agent session; treated as a direct human invocation",
        )

    auth_path = state_dir(sid) / AUTH_FILENAME
    claimed = auth_path.with_suffix(f".claimed.{os.getpid()}")
    try:
        os.rename(auth_path, claimed)
    except OSError:
        return Decision(allowed=False, tier="expensive", reason=_missing_message())

    try:
        token = _read(claimed)
        if token is None:
            return Decision(
                allowed=False, tier="expensive",
                reason="the authorization file could not be read or parsed. "
                       f"Ask the user to run {AUTHORIZE_COMMAND} again.",
            )

        if token.get("origin") != REQUIRED_ORIGIN:
            return Decision(
                allowed=False, tier="expensive",
                reason="the authorization lacks user-typed provenance. Only "
                       f"the user running {AUTHORIZE_COMMAND} can authorize a "
                       "call of this size.",
            )

        age = now - float(token.get("ts") or 0)
        if age > ttl_seconds:
            return Decision(
                allowed=False, tier="expensive",
                reason=f"the authorization expired ({int(age)}s old, limit "
                       f"{ttl_seconds}s). An approval from earlier in the "
                       "session should not silently fund a call the user has "
                       "stopped thinking about.",
            )

        # The token carries a ceiling, so "approve a clip, send the feature
        # film" is not one edit away. Without this the approval would be a
        # blank cheque and the user's control over spend would be nominal.
        ceiling = int(token.get("max_tokens") or 0)
        if ceiling and estimated_tokens > ceiling:
            return Decision(
                allowed=False, tier="expensive",
                reason=f"this call is ~{estimated_tokens:,} estimated input "
                       f"tokens but the authorization covers {ceiling:,}. Ask "
                       f"the user for a larger one: {AUTHORIZE_COMMAND} "
                       f"--max-tokens {estimated_tokens}",
            )

        return Decision(allowed=True, tier="expensive-authorized")
    finally:
        # Whatever happened, this claim is spent. One approval, one call.
        try:
            claimed.unlink()
        except OSError:
            pass


def _missing_message() -> str:
    """Terminates in a decision only a human can make.

    Phrasing is load-bearing. A refusal that reads as "authorize this first"
    is an instruction the main loop will helpfully follow, and the surprise
    spend comes straight back. It has to end with the user, not with a next
    step the agent can take.
    """
    return (
        "this call was not authorized.\n\n"
        "  It is large enough, or irreversible enough, that it spends real\n"
        "  money on the user's account. Nothing in this session can authorize\n"
        "  it on their behalf, including this turn.\n\n"
        "  Do not retry, do not split it into smaller calls to get under the\n"
        "  limit, and do not disable the gate in config. Tell the user what\n"
        "  you wanted to send, what it would cost, and what you expect to\n"
        "  learn. If they want it, they will run:\n\n"
        f"      {AUTHORIZE_COMMAND}\n\n"
        "  A cheaper call -- a trimmed clip, fewer files, a lower resolution\n"
        "  -- needs no authorization and may answer the question anyway."
    )
