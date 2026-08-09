"""What the two guards and the spend gate actually cover -- and did not.

Every arm here was a real hole found by reading the code against its own
documentation. They share one shape: a protection that is described as
covering "what gets sent" but was wired to a subset of the ways something
gets sent, so the uncovered route looked protected and was not.

- The sensitive-path guard ran on `-f`/`-c` only. `--prompt-file`,
  `--system-file` and `--schema-file` also read a local file and put its
  contents in the request, and none of them were checked. `-f .env` was
  refused while `--prompt-file .env` sent the same bytes as the question.
- The spend gate estimated attachments only, so a multi-megabyte
  `--prompt-file` reported "gate none" at roughly a million tokens, and
  `--max-output-tokens` -- billed at the output rate, which is the stated
  reason `thinking_level` is gated -- was not a trigger at all.
- The gate's own audit column had a fourth, undocumented value on the
  consume path, which is the path a parallel-call race takes.

The content scanner is not a substitute for the path guard and these arms
say so: it matches key *shapes*, so `DB_PASSWORD=hunter2` sails through it.
"""

from __future__ import annotations

from types import SimpleNamespace

import orjson
import pytest

from gemini_bridge import auth, cli, ledger, runs

# Everything `authorization_tier` is allowed to be. Kept as a literal set
# rather than imported from the code so that adding a value to the code
# cannot quietly satisfy the arm -- the README table has to move too.
DOCUMENTED_TIERS = {
    "cheap",
    "expensive-authorized",
    "expensive-refused",
    "expensive-gate-disabled",
    "expensive-ungated",
    "unknown",
}


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    (tmp_path / "home" / ".config").mkdir(parents=True)
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s-guard")
    monkeypatch.setattr(
        auth, "resolve",
        lambda *a, **k: auth.Credentials(api_key="fake", kind="env:TEST"),
    )
    image = tmp_path / "a.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    secret = tmp_path / ".env"
    # Deliberately not key-shaped: the content scanner cannot see this, which
    # is the whole reason the path guard has to.
    secret.write_text("DB_PASSWORD=hunter2\nINTERNAL_HOST=vault.corp\n")
    return SimpleNamespace(root=tmp_path, image=image, secret=secret)


def fake_genai():
    class FakeInteractions:
        def create(self, **_kw):
            return SimpleNamespace(
                id=None, status="completed", output_text="ok",
                usage=SimpleNamespace(model_dump=lambda: {"total_input_tokens": 5}),
            )

    return SimpleNamespace(Client=lambda **_kw: SimpleNamespace(
        interactions=FakeInteractions()
    ))


def ask(project, monkeypatch, *args):
    import sys
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai()))
    return cli.main(["--project-root", str(project.root), "ask", *args])


# -- the path guard covers every route that reads a local file --------------


@pytest.mark.parametrize(
    "flag,extra",
    [
        ("--prompt-file", []),
        ("--system-file", ["a question"]),
        ("--schema-file", ["a question"]),
    ],
)
def test_a_sensitive_file_is_refused_whatever_flag_names_it(
    project, monkeypatch, capsys, flag, extra
):
    """`-f .env` was refused and `--prompt-file .env` was not, though both put
    the same bytes in the same request. A guard that depends on which flag was
    typed protects the flag, not the file."""
    assert ask(project, monkeypatch, flag, str(project.secret), *extra) == 1
    err = capsys.readouterr().err
    assert "sensitive path pattern" in err
    assert "hunter2" not in err, "a refusal must not echo what it refused"


def test_the_guard_runs_before_the_file_is_opened(project, monkeypatch):
    """Ordering, not just coverage. Reading first and checking second means the
    bytes are already in the process -- and in any traceback it raises."""
    opened: list[str] = []
    real = type(project.secret).read_text

    def spy(self, *a, **k):
        opened.append(str(self))
        return real(self, *a, **k)

    monkeypatch.setattr(type(project.secret), "read_text", spy)
    assert ask(project, monkeypatch, "--prompt-file", str(project.secret)) == 1
    assert str(project.secret) not in opened


def test_a_missing_prompt_file_is_an_error_not_a_traceback(
    project, monkeypatch, capsys
):
    """--system-file and --schema-file both report cleanly; --prompt-file was
    the one unguarded read and raised FileNotFoundError at the user."""
    assert ask(project, monkeypatch, "--prompt-file", str(project.root / "no.txt")) == 1
    out = capsys.readouterr()
    assert out.err.startswith("error:")
    assert "Traceback" not in out.err


# -- the gate sees everything that is billed --------------------------------


def test_a_huge_text_prompt_is_gated(project, monkeypatch, capsys):
    """budget.total summed attachments only, so a 4MB --prompt-file printed
    "gate none" at roughly a million input tokens. Text is billed too."""
    big = project.root / "big.txt"
    big.write_text("lorem ipsum dolor sit amet " * 40_000)
    assert ask(project, monkeypatch, "--prompt-file", str(big)) == 1
    assert "gemini-authorize" in capsys.readouterr().err


def test_a_large_max_output_tokens_is_gated(project, monkeypatch, capsys):
    """thinking_level is gated because output billing has no ceiling. Asking
    for the output directly is the same spend by a plainer route."""
    assert ask(
        project, monkeypatch, "--max-output-tokens", "200000", "a question"
    ) == 1
    assert "gemini-authorize" in capsys.readouterr().err


def test_an_ordinary_question_is_still_ungated(project, monkeypatch):
    """The counterweight to the two arms above. If counting the prompt drags
    a normal call over the line, the gate gets switched off."""
    assert ask(project, monkeypatch, "-f", str(project.image), "what is this") == 0
    entry = ledger.read(project.root / runs.RUNS_DIRNAME)[0]
    assert entry["authorization_tier"] == "cheap"


# -- the audit column has no undocumented values ----------------------------


def test_a_consume_stage_refusal_records_a_documented_tier(project, monkeypatch):
    """peek() passes, then the token is gone before consume().

    The real cause is the race consume()'s own docstring exists for: two
    expensive calls in one turn, both peek clean, one wins the rename. Or the
    TTL lapsing while a key command waits on a biometric prompt. Simulated by
    dropping the token inside auth.resolve, which is exactly that window.

    The peek path was hard-coded to "expensive-refused"; this path passed
    through decision.tier, which was the bare "expensive" -- a fourth value
    the README does not list, on a refusal, which is what an audit is looking
    for in the first place.
    """
    import time

    from gemini_bridge import authorization

    d = authorization.state_dir("s-guard")
    d.mkdir(parents=True, exist_ok=True)
    token = d / authorization.AUTH_FILENAME
    token.write_bytes(orjson.dumps(
        {"ts": time.time(), "max_tokens": 200_000, "origin": "user_typed_command"}
    ))

    real_resolve = auth.resolve

    def racing_resolve(*a, **k):
        token.unlink()  # the other call won the rename
        return real_resolve(*a, **k)

    monkeypatch.setattr(auth, "resolve", racing_resolve)
    assert ask(project, monkeypatch, "--store", "a question") == 1
    entry = ledger.read(project.root / runs.RUNS_DIRNAME)[0]
    assert entry["status"] == "unauthorized"
    assert entry["authorization_tier"] in DOCUMENTED_TIERS


# -- what the CLI says about its own state ----------------------------------


def test_the_empty_uploads_message_does_not_describe_the_old_bug(
    project, monkeypatch, capsys
):
    """`live()` was made margin-free precisely so a near-expiry handle stops
    vanishing from the listing. The empty-list message still told the user it
    prunes at 30 minutes -- documenting the bug as if it were the design."""
    assert cli.main(["--project-root", str(project.root), "uploads"]) == 0
    assert "30 minutes" not in capsys.readouterr().out


def test_the_warning_names_a_lever_the_caller_actually_has(
    project, monkeypatch, capsys
):
    """A text-only call has no --resolution to lower and no -c to move files
    to. Advice that names them is advice nobody can act on -- which is the one
    thing budget.advice exists to avoid. Reachable only since the estimate
    started counting text, so it arrived with that change."""
    big = project.root / "big.txt"
    big.write_text("lorem ipsum dolor sit amet " * 40_000)
    ask(project, monkeypatch, "--prompt-file", str(big))
    err = capsys.readouterr().err
    assert "prompt text" in err
    assert "--resolution" not in err


# -- the gate and the scanner must agree on what "outgoing text" means -------


@pytest.mark.parametrize("channel", ["prompt", "system", "schema", "labels"])
def test_every_outgoing_text_channel_counts_toward_the_gate(
    project, monkeypatch, capsys, channel
):
    """The estimator and the secret scanner each built their own list.

    The scanner has enumerated four channels since 0.6.x -- question, system
    instruction, schema, labels -- and its comment says a channel left out of
    that list stays unscanned until someone names it. The estimator counted
    two. A 3MB `--schema-file` printed `text ~1 input tokens` and
    `gate none`, which is the same hole `--prompt-file` had, on the sibling
    flag the same release added to the path guard. Two lists that must agree
    are one list; this arm holds each channel to the same standard.
    """
    import orjson as _oj

    big = "lorem ipsum dolor sit amet " * 40_000
    if channel == "prompt":
        f = project.root / "p.txt"; f.write_text(big)
        args = ["--prompt-file", str(f)]
    elif channel == "system":
        f = project.root / "s.txt"; f.write_text(big)
        args = ["--system-file", str(f), "q"]
    elif channel == "schema":
        f = project.root / "s.json"
        f.write_bytes(_oj.dumps({"type": "object", "description": big}))
        args = ["--schema-file", str(f), "q"]
    else:
        args = ["--label", f"note={big}", "q"]

    assert ask(project, monkeypatch, *args) == 1
    assert "gemini-authorize" in capsys.readouterr().err


# -- resolution is a cost lever, so every value must be priced --------------


@pytest.mark.parametrize("resolution", ["low", "medium", "high", "ultra_high"])
def test_no_video_resolution_estimates_below_the_default(resolution):
    """`ultra_high` fell through to the 70 tok/s branch because the rate was
    chosen by `== "high"`. It is an accepted value for video -- argparse
    offers it, recipes validate it, and the content block carries it -- so the
    single most expensive setting produced the cheapest estimate and slipped
    the gate that `high` triggers. A ladder selected by equality against one
    rung breaks the moment a rung is added."""
    from pathlib import Path

    from gemini_bridge import budget
    from gemini_bridge.media import Attachment

    att = Attachment(path=Path("v.mp4"), kind="video", mime_type="video/mp4",
                     size_bytes=10**7, resolution=resolution)
    base = budget.VIDEO_TOKENS_PER_SECOND
    rate = budget.VIDEO_TOKEN_RATES[resolution]
    assert rate >= base
    if resolution in {"high", "ultra_high"}:
        assert rate > base, "the expensive settings must estimate above default"
    assert budget.estimate(att).tokens > 0


def test_a_refusal_survives_a_project_root_it_cannot_write_to(
    project, monkeypatch, capsys
):
    """`ensure_runs_root` was evaluated as an argument to `ledger.record`,
    outside every guard, so a read-only project root turned the refusal into a
    PermissionError traceback. The refusal text is designed to terminate in a
    human decision; a traceback terminates in nothing. The audit row is the
    thing that may be lost here, never the refusal."""
    from gemini_bridge import runs

    def unwritable(_root):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(runs, "ensure_runs_root", unwritable)
    big = project.root / "p.txt"
    big.write_text("lorem ipsum dolor sit amet " * 40_000)
    assert ask(project, monkeypatch, "--prompt-file", str(big)) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "gemini-authorize" in err


def test_the_ledger_records_the_session_it_actually_ran_under(project, monkeypatch):
    """`ledger.py` read CLAUDE_SESSION_ID alone -- the variable
    `authorization.py` documents as not exported by Claude Code -- so every row
    written on an agent call recorded a null session, refusals included. The
    refused rows exist so an audit can see an agent repeatedly trying to spend
    more than it may; unattributable rows cannot show a pattern."""
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s-attributed")
    assert ask(project, monkeypatch, "-f", str(project.image), "q") == 0
    assert ledger.read(project.root / runs.RUNS_DIRNAME)[0]["session_id"] \
        == "s-attributed"
