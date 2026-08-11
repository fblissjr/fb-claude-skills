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
import re
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson

STATE_ROOT_NAME = "claude-gemini-bridge"
AUTH_FILENAME = "authorization.json"
SPEND_FILENAME = "spend.json"
REQUIRED_ORIGIN = "user_typed_command"

# The one tier a refusal may be recorded under. It used to be the bare string
# "expensive", which describes the *call* rather than the gate's verdict and is
# not one of the values the README's table lists -- so an audit filtering the
# documented values dropped exactly the refusals it was run to count. The CLI
# papered over that on the peek path with a hard-coded string; the consume
# path, which is the one a parallel-call race takes, kept the bare value.
# Naming it here means both paths get it from the same place.
TIER_REFUSED = "expensive-refused"

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


# Read in order. `CLAUDE_CODE_SESSION_ID` is the one Claude Code actually
# exports to Bash subprocesses; `CLAUDE_SESSION_ID` is kept because ledger.py
# has always read it and some versions may still set it.
#
# The first shipped version of this gate read ONLY `CLAUDE_SESSION_ID`, which
# is not exported. `session_id()` returned None on every agent call, the gate
# concluded "not an agent session" and stood down, and it was a no-op for
# precisely the calls it exists to stop. It failed OPEN and silently. Every
# test passed because every test set the variable itself, which proved the
# tests agreed with the code and nothing about the world.
SESSION_ENV_VARS = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")

# Independent evidence that we are inside an agent, used to decide the
# direction of failure when no session id can be found. Without this, renaming
# the variable again rebuilds the same silent no-op.
AGENT_MARKER_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_VERSION")

# The id is interpolated straight into a filesystem path by `state_dir`, on
# both sides of the gate. Anything carrying a separator, or spelled `.` or
# `..`, resolves somewhere neither half intended -- so it is not a session id
# this module can act on, and "cannot verify" already has an answer here.
# Requiring a leading alphanumeric is what rejects the dot forms without a
# second check.
SESSION_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def raw_session_id() -> str | None:
    """Whatever the environment says the session is, unvalidated.

    For the ledger, which wants attribution and not a decision. `ledger.py`
    read `CLAUDE_SESSION_ID` alone -- the variable this module documents as
    *not* exported -- so every row written on an agent call recorded a null
    session, including the `run_id: "(refused)"` rows added so an audit could
    see an agent repeatedly trying to spend more than it may. An audit trail
    that cannot attribute its rows to a session cannot show a pattern.

    Deliberately not `session_id()`: a value too odd for the gate to act on is
    still the best answer available to the question "which session was this?",
    and dropping it would trade a real attribution for a null.
    """
    for var in SESSION_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def session_id() -> str | None:
    """The session id the gate may act on, or None if it cannot be used as one."""
    value = raw_session_id()
    if value and SESSION_ID_RE.match(value):
        return value
    return None


def in_agent_session() -> bool:
    """Whether this looks like an agent, independent of the session id.

    Load-bearing: "no session id" and "no agent" are different conclusions
    with opposite safe answers. A human at a shell should not be gated; an
    agent whose session id we cannot read must be, because the alternative is
    the gate quietly not existing.
    """
    return any(os.environ.get(v) for v in (*AGENT_MARKER_VARS, *SESSION_ENV_VARS))


def state_root() -> Path:
    # `os.environ.get("TMPDIR", "/tmp")` returns "" for an exported-but-empty
    # TMPDIR, while the hook's `${TMPDIR:-/tmp}` yields /tmp -- mint and
    # enforce would look in different directories. The ONE place this
    # derivation lives: it was copied inline twice, and a third copy in the
    # spend counter would have let writer and reader silently diverge.
    return Path(os.environ.get("TMPDIR") or "/tmp") / STATE_ROOT_NAME


def state_dir(sid: str) -> Path:
    return state_root() / sid


def _owned(path: Path, *, directory: bool = False) -> bool:
    """Whether `path` is a file (or directory) owned by this user.

    The `TMPDIR` fallback is a shared `/tmp` on Linux, and the minting hook's
    own comment calls this file the thing standing between another local
    account and spending on this API key. Nothing checked it: whatever sat at
    the path was trusted on its contents alone. An account that creates
    `/tmp/claude-gemini-bridge` first owns that path, and the hook's `chmod
    700` on an existing directory fails into a `|| true`.

    `lstat`, not `stat`: a symlink pointing at a file we do own would
    otherwise pass while the attacker still controls what the name resolves
    to. Regular-file-only for the same reason -- a fifo or a device is not an
    authorization.
    """
    if not hasattr(os, "getuid"):  # not a platform this plugin's hook runs on
        return True
    try:
        st = path.lstat()
    except OSError:
        return False
    right_type = stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)
    return right_type and st.st_uid == os.getuid()


def mint_target_ok() -> bool:
    """Whether the hook can mint into the state root at all.

    Mirrors the hook's own refusal so `doctor` can report it. Without this the
    failure is the worst shape there is: the user types the command, it appears
    to work, the call is refused again, and nothing anywhere says why.
    """
    base = state_root()
    if not base.exists():
        return True  # the hook creates it, and then owns it
    return _owned(base, directory=True)


def _read(path: Path) -> dict[str, Any] | None:
    if not _owned(path):
        return None
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
    max_output_tokens: int | None = None,
    session_spent_tokens: int = 0,
    max_session_tokens: int | None = None,
) -> tuple[str, str]:
    """(tier, why). Cost and irreversibility, not modality.

    Deliberately not "video is expensive": a five-second clip is a few hundred
    tokens, and gating it would train people to switch the gate off, which
    costs more than it saves. What earns a gate is a call that is large, or one
    that cannot be taken back.

    `estimated_tokens` is the whole input -- attachments *and* the text that
    travels with them. Counting attachments alone left a multi-megabyte
    `--prompt-file` reporting "not gated" at roughly a million tokens, which
    is the same spend arriving by the one route nobody was measuring.
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
    # Raised thinking is gated because output billing runs away. Asking for the
    # output directly is the same spend by a plainer route, so it meets the
    # same threshold -- output tokens cost several times what input does, which
    # makes this the conservative side of the comparison rather than the
    # generous one.
    if max_output_tokens and max_output_tokens > max_unauthorized_tokens:
        return "expensive", (
            f"max_output_tokens={max_output_tokens:,} is over the "
            f"{max_unauthorized_tokens:,} limit, and output bills at several "
            "times the input rate"
        )
    if estimated_tokens > max_unauthorized_tokens:
        return "expensive", (
            f"~{estimated_tokens:,} estimated input tokens, over the "
            f"{max_unauthorized_tokens:,} limit for an unauthorized call"
        )
    # The cumulative arm. Per-call gating alone lets "the same cheap call,
    # forever" spend without a ceiling: a hundred calls at 15k tokens each
    # never trip a 20k per-call limit. Crossing the cap does not stop the
    # session -- it makes the next call expensive, which routes through the
    # same human keystroke everything else expensive needs. `None` disables
    # the cap; zero deliberately does NOT read as disabled, because "the value
    # that reads as allow-nothing" being the one that allows everything is the
    # exact bug the per-call ceiling shipped with. Spent comes from
    # `session_spent_tokens()` below -- session state, not the project
    # ledger, for the reason that docstring gives.
    if (max_session_tokens is not None
            and session_spent_tokens + estimated_tokens > max_session_tokens):
        return "expensive", (
            f"this session has already spent ~{session_spent_tokens:,} "
            f"recorded tokens; with this call's ~{estimated_tokens:,} "
            f"estimated input it crosses the {max_session_tokens:,} "
            "session cap for unauthorized spend"
        )
    return "cheap", ""


def session_spent_tokens() -> int:
    """What this session has spent unauthorized -- all token classes.

    Read by the spend gate's session cap. It lives HERE, in the session state
    directory beside the authorization token, with the same ownership rules --
    and not in the project ledger it was first summed from, because the
    ledger's location is chosen by the gated party: `--project-root
    /tmp/fresh` gave a refused agent an empty ledger and a restarted count,
    with no user keystroke. The ledger stays the audit record; this is gate
    state, and gate state must live somewhere the gated party does not name
    on the command line. (TMPDIR is part of the key, so overriding it does
    reset the counter -- the same documented honest limit as clearing the
    agent-marker variables, and a deliberate act where `--project-root` is
    an ordinary argument.)

    Keyed by the VALIDATED session id, like the token. The first version
    summed ledger rows keyed by the raw id, while minting and consuming used
    the validated one -- so a session whose id failed validation accrued
    spend it could never authorize away, a permanent refusal no command
    could clear.

    Degrades to zero: unreadable, unowned, corrupt, or absent state must not
    fail a call, and the per-call tier stands regardless.
    """
    sid = session_id()
    if not sid:
        return 0
    return _spend_value(_read(state_dir(sid) / SPEND_FILENAME))


def _spend_value(data: dict[str, Any] | None) -> int:
    """The counter a spend file holds, degraded to zero on any bad shape."""
    if not data:
        return 0
    try:
        return max(0, int(data.get("tokens") or 0))
    except (TypeError, ValueError):
        return 0


def accrue_call_spend(usage: dict[str, Any], authorization_tier: str) -> None:
    """The accrual policy, in one place instead of at a call site.

    Two invariants any recording path must honour together: ALL token
    classes count (output bills highest -- a counter of input alone leaves
    the expensive axis uncapped), and only UNAUTHORIZED spend counts (tokens
    a user explicitly approved must not later gate unrelated cheap calls
    under a message that says "unauthorized spend").
    """
    if authorization_tier == "expensive-authorized":
        return
    add_session_spend(
        (usage.get("total_input_tokens") or 0)
        + (usage.get("total_output_tokens") or 0)
        + (usage.get("total_thought_tokens") or 0)
    )


def add_session_spend(tokens: int) -> None:
    """Accrue recorded usage against the session cap. Never raises.

    Called after the ledger row is written, with what the API actually
    reported -- input, output, and thinking alike, since output is the axis
    that bills highest and a cap counting input alone leaves the expensive
    axis uncapped. The caller skips authorized calls: tokens a user
    explicitly approved must not later gate unrelated cheap calls under a
    message that says "unauthorized spend".

    Written via tmp-file-and-replace, like consume() claims by rename: a
    truncate-in-place write let a concurrent reader catch the file empty,
    read the counter as zero, and write back `0 + its tokens` -- resetting
    the whole accumulated count, which is worse than the race this accepts.
    What remains accepted: two parallel calls can still interleave
    read-modify-write and lose ONE update. The cap is an order-of-magnitude
    control, and under-counting by one call's usage does not change which
    side of it a runaway session lands on -- unlike the single-use token,
    where the same race funds a double spend.
    """
    if tokens <= 0:
        return
    sid = session_id()
    if not sid:
        return
    target = state_dir(sid)  # the one place the path derivation lives
    try:
        for d in (target.parent, target):
            d.mkdir(mode=0o700, exist_ok=True)
            # _owned lstats, so a symlinked directory fails the type check
            # rather than being followed. An unowned root is the shared-/tmp
            # squat the minting hook refuses; the counter refuses it too, by
            # declining to write. doctor already reports the condition.
            if not _owned(d, directory=True):
                return
        path = target / SPEND_FILENAME
        # _read directly rather than session_spent_tokens(), which would
        # re-resolve the session and rebuild the path just validated above.
        current = _spend_value(_read(path))
        tmp = target / f"{SPEND_FILENAME}.{os.getpid()}.tmp"
        tmp.write_bytes(orjson.dumps({"tokens": current + tokens}))
        tmp.chmod(0o600)
        os.replace(tmp, path)
    except OSError:
        return


def _no_session_decision() -> Decision:
    """What to do when no session id can be resolved.

    Two opposite answers depending on who is asking, which is the whole reason
    `in_agent_session` exists. A human typing into their own shell *is* the
    authorization and must not be gated. An agent whose session we cannot
    identify must be, because "cannot verify" has to mean no -- the
    alternative is the silent no-op this gate shipped with.
    """
    if not in_agent_session():
        return Decision(
            allowed=True, tier="expensive-ungated",
            reason="no agent session; treated as a direct human invocation",
        )
    return Decision(
        allowed=False, tier=TIER_REFUSED,
        reason=(
            "this looks like an agent session but no usable session id could "
            f"be read from {' or '.join(SESSION_ENV_VARS)} -- it is missing, "
            "or not a plain identifier -- so the authorization cannot be "
            "located. Refusing rather than allowing an unverified call. If the "
            "variable was renamed upstream, that is a bug in this plugin -- "
            "report it rather than working around it."
        ),
    )


def _validate(
    token, *, estimated_tokens: int, ttl_seconds: int, now: float
) -> Decision:
    """Shared by peek and consume so the two can never disagree."""
    if token is None:
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason="the authorization file could not be read, parsed, or is "
                   "not owned by this user. Ask the user to run "
                   f"{AUTHORIZE_COMMAND} again.",
        )

    if token.get("origin") != REQUIRED_ORIGIN:
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason="the authorization lacks user-typed provenance. Only the "
                   f"user running {AUTHORIZE_COMMAND} can authorize a call of "
                   "this size.",
        )

    try:
        age = now - float(token.get("ts") or 0)
        ceiling = int(token.get("max_tokens") or 0)
    except (TypeError, ValueError):
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason="the authorization is malformed. Ask the user to run "
                   f"{AUTHORIZE_COMMAND} again.",
        )

    if age > ttl_seconds:
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason=f"the authorization expired ({int(age)}s old, limit "
                   f"{ttl_seconds}s). An approval from earlier in the session "
                   "should not silently fund a call the user has stopped "
                   "thinking about.",
        )

    # The token carries a ceiling, so "approve a clip, send the feature film"
    # is not one edit away. Without it the approval is a blank cheque and the
    # user's control over spend is nominal.
    #
    # A ceiling of zero or one that is missing entirely is refused, not treated
    # as absent. The guard here used to read `if ceiling and ...`, which made 0
    # -- the value that reads as "allow nothing" -- the single value that
    # allowed everything, reachable by typing `--max-tokens 0` because the hook
    # accepts it as all digits.
    if ceiling <= 0:
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason="the authorization carries no usable token ceiling, so "
                   "there is nothing bounding what it would approve. Ask the "
                   f"user to run {AUTHORIZE_COMMAND} again.",
        )

    if estimated_tokens > ceiling:
        return Decision(
            allowed=False, tier=TIER_REFUSED,
            reason=f"this call is ~{estimated_tokens:,} estimated input tokens "
                   f"but the authorization covers {ceiling:,}. Ask the user for "
                   f"a larger one: {AUTHORIZE_COMMAND} "
                   f"--max-tokens {estimated_tokens}",
        )

    return Decision(allowed=True, tier="expensive-authorized")


def peek(
    *, estimated_tokens: int, ttl_seconds: int, now: float | None = None
) -> Decision:
    """Would this call be authorized? Reads only; consumes nothing.

    Exists so the refusal can happen early -- before credentials are resolved,
    a client is built, or a run directory is created -- while the token itself
    is spent late. `consume` is the authoritative check; this only avoids
    doing pointless work on a call that is going to be refused anyway.
    """
    now = time.time() if now is None else now
    sid = session_id()
    if sid is None:
        return _no_session_decision()

    path = state_dir(sid) / AUTH_FILENAME
    if not path.is_file():
        return Decision(allowed=False, tier=TIER_REFUSED, reason=_missing_message())
    return _validate(
        _read(path), estimated_tokens=estimated_tokens,
        ttl_seconds=ttl_seconds, now=now,
    )


def consume(
    *, estimated_tokens: int, ttl_seconds: int, now: float | None = None
) -> Decision:
    """Spend the authorization, immediately before the first irreversible step.

    Placement is a bug class, not a style point: the first version consumed the
    token before credentials were resolved, so a key command that prompted for
    an unlock and timed out burned the user's approval on a call that sent
    nothing -- and they had to type the command again to retry.

    Single-use, claimed by rename *before* validation. Parallel tool calls are
    a supported pattern, so two expensive calls in one turn could otherwise
    both read the same still-present token and both proceed -- one approval
    funding two sends. Only the process that wins the rename continues.
    """
    now = time.time() if now is None else now
    sid = session_id()
    if sid is None:
        return _no_session_decision()

    auth_path = state_dir(sid) / AUTH_FILENAME
    claimed = auth_path.with_suffix(f".claimed.{os.getpid()}")
    try:
        os.rename(auth_path, claimed)
    except OSError:
        return Decision(allowed=False, tier=TIER_REFUSED, reason=_missing_message())

    try:
        return _validate(
            _read(claimed), estimated_tokens=estimated_tokens,
            ttl_seconds=ttl_seconds, now=now,
        )
    finally:
        # Whatever happened, this claim is spent. A rejected token must not sit
        # there for a retry loop to keep testing against.
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
