"""The minting half of the spend gate, driven as the shell script it is.

Nothing watched this file. Every other arm in the suite exercised the CLI's
*enforcement* against a token the test wrote itself, in the shape the test
believed the hook used -- which is precisely the arrangement that let
`session_id()` read an environment variable Claude Code does not export and
still pass every test in the suite. The tests agreed with the code and said
nothing about the world.

So the arm that matters most here is the round trip: run the real script,
then hand what it wrote to the real `peek()` and require an approval. Nothing
in between is mocked. If either half changes its mind about the filename, the
directory, the payload keys, the provenance string, or the session variable,
that arm goes red -- and no amount of agreement between a test and one side
of the pair can save it.

The rest pin the direction of failure, which for a mint is "write nothing":
a wrong command, a wrong event, an unusable session id, a state root someone
else could control, a ceiling that would be refused on arrival.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import orjson
import pytest

from gemini_bridge import authorization

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "gemini-authorize.sh"

pytestmark = pytest.mark.skipif(
    not shutil.which("jq"), reason="the hook is a no-op without jq, by design"
)


def run_hook(tmpdir: Path, **payload) -> subprocess.CompletedProcess:
    """Invoke the script exactly as hooks.json does: bash, payload on stdin."""
    body = {
        "command_name": "gemini-bridge:gemini-authorize",
        "expansion_type": "slash_command",
        "session_id": "s-hook",
        "command_args": "",
        **payload,
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        input=orjson.dumps(body),
        capture_output=True,
        env={**os.environ, "TMPDIR": str(tmpdir)},
        check=False,
    )


def token_for(tmpdir: Path, sid: str = "s-hook") -> Path:
    return tmpdir / authorization.STATE_ROOT_NAME / sid / authorization.AUTH_FILENAME


# -- the pair, checked against each other -----------------------------------


def test_what_the_hook_writes_is_what_the_cli_accepts(tmp_path, monkeypatch):
    """The one arm that could have caught the shipped no-op.

    Both halves are real here. A rename on either side -- the env var, the
    filename, the directory layout, the `origin` string -- breaks this and
    nothing else in the suite.
    """
    result = run_hook(tmp_path)
    assert result.returncode == 0
    assert result.stdout == b"", "a UserPromptExpansion hook must emit nothing"

    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s-hook")
    decision = authorization.peek(estimated_tokens=50_000, ttl_seconds=600)
    assert decision.allowed, decision.reason
    assert decision.tier == "expensive-authorized"


def test_the_authorization_is_not_readable_by_other_accounts(tmp_path):
    """The TMPDIR fallback is a shared /tmp on Linux and this file is what
    stands between another local account and spending on this API key."""
    run_hook(tmp_path)
    assert token_for(tmp_path).stat().st_mode & 0o077 == 0
    assert token_for(tmp_path).parent.stat().st_mode & 0o077 == 0


# -- only a user-typed command mints ----------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"expansion_type": "at_mention"},   # not a slash command
        {"expansion_type": ""},             # unknown event shape
        {"command_name": "something-else"},  # a misconfigured matcher
        {"session_id": ""},                 # nothing to key the token on
    ],
)
def test_nothing_else_mints(tmp_path, payload):
    assert run_hook(tmp_path, **payload).returncode == 0
    assert not token_for(tmp_path).exists()
    assert not token_for(tmp_path, payload.get("session_id", "s-hook")).exists()


def test_an_empty_payload_is_survivable(tmp_path):
    result = subprocess.run(
        ["bash", str(HOOK)], input=b"", capture_output=True,
        env={**os.environ, "TMPDIR": str(tmp_path)}, check=False,
    )
    assert result.returncode == 0, "a prompt is never rejected by this hook"


# -- the ceiling the approval carries ---------------------------------------


def test_the_default_ceiling_is_bounded(tmp_path):
    run_hook(tmp_path)
    assert orjson.loads(token_for(tmp_path).read_bytes())["max_tokens"] == 200000


def test_an_explicit_ceiling_is_honoured(tmp_path):
    run_hook(tmp_path, command_args="--max-tokens 12345")
    assert orjson.loads(token_for(tmp_path).read_bytes())["max_tokens"] == 12345


@pytest.mark.parametrize("args", ["--max-tokens 0", "--max-tokens abc",
                                  "--max-tokens", "--max-tokens -5"])
def test_an_unusable_ceiling_becomes_the_default(tmp_path, args):
    """Zero most of all. `if ceiling and ...` on the reading side made 0 -- the
    value that reads as "allow nothing" -- the one value that bounded nothing,
    and it is four keystrokes away from an ordinary approval. Both sides now
    refuse it; this arm pins the minting side."""
    run_hook(tmp_path, command_args=args)
    assert orjson.loads(token_for(tmp_path).read_bytes())["max_tokens"] == 200000


def test_a_glob_in_the_arguments_is_not_expanded(tmp_path, monkeypatch):
    """`set -f` guards the unquoted split. Without it the typed value is
    replaced by whatever the working directory happens to contain."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "--max-tokens").touch()
    run_hook(tmp_path, command_args="* --max-tokens 4242")
    assert orjson.loads(token_for(tmp_path).read_bytes())["max_tokens"] == 4242


# -- refusing to mint somewhere we do not control ---------------------------


@pytest.mark.parametrize("sid", ["../escape", "a/b", "..", ".", "with space"])
def test_a_session_id_that_is_not_a_plain_identifier_mints_nothing(tmp_path, sid):
    """The id is interpolated into a path on both sides. The CLI rejects these
    when reading, so minting for one would only produce a token nothing can
    find -- and a traversal-shaped id would write outside the state root."""
    run_hook(tmp_path, session_id=sid)
    # Searched from TMPDIR, not from the state root: `../escape` resolves
    # *outside* it, so an assertion scoped to the state root would pass while
    # the token sat one directory up.
    assert not list(tmp_path.rglob(authorization.AUTH_FILENAME))


def test_a_symlinked_state_root_mints_nothing(tmp_path):
    """`mkdir -p` succeeds against anything already there, whoever owns it. On
    a shared /tmp that is another account's directory, and the old `chmod ...
    || true` swallowed the failure and wrote the token in anyway."""
    elsewhere = tmp_path / "attacker"
    elsewhere.mkdir()
    (tmp_path / authorization.STATE_ROOT_NAME).symlink_to(elsewhere)
    assert run_hook(tmp_path).returncode == 0
    assert not list(elsewhere.rglob("*.json")), "minted into a path we do not own"


@pytest.mark.parametrize(
    "sid",
    [
        "0199aa11-bb22-cc33-dd44-ee55ff667788",  # the real shape
        "s-hook", "A", "a.b_c-d", "9lives",
        "", ".", "..", "../escape", "a/b", "with space", "-lead", "_lead",
        ".lead", "x" * 128, "x" * 129,
    ],
)
def test_the_hook_and_the_cli_agree_on_which_ids_are_usable(tmp_path, sid):
    """The comment above the hook's check claims parity with the CLI's regex,
    and it did not have it: ids starting with `.`, `-` or `_`, and ids over 128
    characters, were minted for and then always refused on read -- an
    approval the user typed that could never be spent, with `doctor` as the
    only place saying so. A claim of parity between two implementations is a
    thing to test, not to write in a comment."""
    run_hook(tmp_path, session_id=sid)
    minted = bool(list(tmp_path.rglob(authorization.AUTH_FILENAME)))
    usable = bool(authorization.SESSION_ID_RE.match(sid))
    assert minted == usable, (
        f"hook minted={minted} but the CLI would accept={usable} for {sid!r}"
    )
