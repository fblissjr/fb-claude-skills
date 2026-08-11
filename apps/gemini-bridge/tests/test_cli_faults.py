"""Fault injection for the CLI's post-call path.

This code exists to handle failures that have never actually happened -- the
reviewer's point was that findings 1 and 2 were both paths that looked fine and
had never executed. Untriggered error handling is a guess until something
triggers it.

The invariant under test: once the API has responded, the call is billed and
possibly stored. Nothing after that point may lose the answer, the usage record,
or the interaction id silently.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from gemini_bridge import auth, cli, ledger, runs


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project directory with a recipe and working fake credentials.

    HOME and XDG_CONFIG_HOME are redirected first. Without that, Config.load()
    reads the developer's real user config during the run -- harmless while
    auth is mocked over, but it would put their absolute config path into
    captured output the moment a test exercises `doctor`.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    (tmp_path / "home" / ".config").mkdir(parents=True)
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "demo.md").write_text(
        "---\nmodel: m\nschema:\n  type: object\n---\n\nBe terse.\n"
    )
    monkeypatch.setattr(cli, "_bundled_recipe_dirs", lambda: [recipes])
    monkeypatch.setattr(
        auth, "resolve",
        lambda *a, **k: auth.Credentials(api_key="fake", kind="env:TEST"),
    )
    image = tmp_path / "a.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    return SimpleNamespace(root=tmp_path, image=image)


def fake_genai(status="completed", text='{"ok": true}', interaction_id="v1_abc"):
    class FakeInteractions:
        def create(self, **_kw):
            return SimpleNamespace(
                id=interaction_id, status=status, output_text=text,
                usage=SimpleNamespace(model_dump=lambda: {"total_input_tokens": 5}),
            )

    return SimpleNamespace(Client=lambda **_kw: SimpleNamespace(
        interactions=FakeInteractions()
    ))


def run_ask(project, monkeypatch, extra=None, question="compare these", **genai_kw):
    import sys
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai(**genai_kw)))
    return cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), *(extra or []), question,
    ])


def read_ledger(project):
    return ledger.read(project.root / runs.RUNS_DIRNAME)


# -- the happy path, as a baseline -----------------------------------------


def test_success_writes_everything_and_logs(project, monkeypatch):
    assert run_ask(project, monkeypatch) == 0
    entries = read_ledger(project)
    assert len(entries) == 1
    assert entries[0]["status"] == "completed"
    run_dir = next((project.root / runs.RUNS_DIRNAME).glob("*-demo"))
    assert (run_dir / "response.md").is_file()
    assert (run_dir / "response.json").is_file()
    assert (run_dir / "interaction.id").read_text().strip() == "v1_abc"


def test_ledger_keeps_the_interaction_id(project, monkeypatch):
    """The ledger must survive deletion of the run directory.

    `stored` reads `interaction.id` out of run dirs, and the API has no `list`
    to rebuild that set and no working `delete` to act on it. So pruning run
    dirs without this field would silently blind the only disclosure surface a
    user has -- and the handle would be gone for good.
    """
    assert run_ask(project, monkeypatch, interaction_id="v1_keepme") == 0
    assert read_ledger(project)[0]["interaction_id"] == "v1_keepme"


def test_ledger_records_a_null_id_when_nothing_was_stored(project, monkeypatch):
    """Present-and-null, not absent: a query for stored interactions must not
    have to distinguish 'no id' from 'this row predates the field'."""
    assert run_ask(project, monkeypatch, interaction_id=None) == 0
    entry = read_ledger(project)[0]
    assert "interaction_id" in entry and entry["interaction_id"] is None


def test_scan_bypass_is_recorded_in_the_ledger(project, monkeypatch):
    """Run dirs written under the bypass are the ones worth finding later.

    The override skips the scan entirely, so the outgoing text was never
    checked -- and the run directory keeps it in plaintext locally while the
    interaction at Google cannot be deleted. Without this field the only way to
    locate those runs is grepping every prompt.md, which means reading the very
    content the flag was used to send.
    """
    secret = "ghp_" + "a" * 36
    assert run_ask(
        project, monkeypatch,
        extra=["--allow-prompt-secrets"], question=f"is {secret} visible here",
    ) == 0
    entry = read_ledger(project)[0]
    assert entry["allow_prompt_secrets"] is True
    assert entry["prompt_scanned"] is False


def test_ordinary_calls_record_the_bypass_as_false(project, monkeypatch):
    """False, not absent -- a filter for risky runs must not depend on a key
    that only exists on the risky ones."""
    assert run_ask(project, monkeypatch) == 0
    entry = read_ledger(project)[0]
    assert entry["allow_prompt_secrets"] is False
    assert entry["prompt_scanned"] is True


def test_config_disabled_scan_is_recorded_as_unscanned(project, monkeypatch):
    """scan_prompt = false in project config must not masquerade as scanned.

    The flag field records only the CLI route. Before prompt_scanned existed,
    a project config with the scan off produced ledger rows saying
    allow_prompt_secrets: false -- and the README pointed auditors at exactly
    that field as the only way to find unscanned runs. The audit trail was
    positively reassuring about the runs it existed to expose.
    """
    (project.root / ".gemini-bridge.toml").write_text(
        "[privacy]\nscan_prompt = false\n"
    )
    secret = "ghp_" + "b" * 36
    assert run_ask(project, monkeypatch, question=f"is {secret} visible") == 0
    entry = read_ledger(project)[0]
    assert entry["prompt_scanned"] is False
    assert entry["allow_prompt_secrets"] is False


def test_bypass_is_recorded_even_when_the_call_fails(project, monkeypatch):
    """The failure path is where it matters most: the prompt still reached
    Google, and the run directory still holds it."""
    import sys

    class Boom:
        def create(self, **_kw):
            raise RuntimeError("upstream exploded")

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=lambda **_kw: SimpleNamespace(interactions=Boom()))
    ))
    cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "--allow-prompt-secrets", "q",
    ])
    entries = read_ledger(project)
    assert entries and entries[0]["status"] == "failed"
    assert entries[0]["allow_prompt_secrets"] is True
    assert entries[0]["prompt_scanned"] is False


# -- write failures ---------------------------------------------------------


def test_response_write_failure_still_logs_and_surfaces_the_answer(
    project, monkeypatch, capsys
):
    """The failure that used to lose a paid answer entirely."""
    def boom(self, text):
        raise OSError("No space left on device")

    monkeypatch.setattr(runs.RunDir, "write_response", boom)
    code = run_ask(project, monkeypatch, text='{"verdict": "important"}')

    assert code == 3, "a lost answer must not exit 0"
    err = capsys.readouterr().err
    assert "could not write response.md" in err
    assert "important" in err, "the answer must reach the user somehow"
    assert read_ledger(project), "the call must be recorded even when writes fail"


def test_interaction_id_is_written_before_the_other_files(project, monkeypatch):
    """The id is the only thing a re-run cannot regenerate.

    If everything after it fails, the id must still be on disk -- it is the sole
    handle on a stored interaction, and stored interactions cannot be deleted
    through the API.
    """
    for method in ("write_response", "write_usage", "write_structured"):
        monkeypatch.setattr(
            runs.RunDir, method,
            lambda self, *a, **k: (_ for _ in ()).throw(OSError("disk full")),
        )
    run_ask(project, monkeypatch)
    run_dir = next((project.root / runs.RUNS_DIRNAME).glob("*-demo"))
    assert (run_dir / "interaction.id").read_text().strip() == "v1_abc"


def test_ledger_write_failure_is_swallowed(monkeypatch, tmp_path):
    """Logging must never be the reason a call fails.

    `ledger.record` opens a file and deliberately catches OSError: an
    unwritable destination should cost you the record, not the answer.

    The failure is injected rather than staged with a 0o500 directory, because
    **root ignores permission bits**. Under the container this suite often runs
    in, the staged write simply succeeded, the except branch never executed,
    and the arm failed for a reason that had nothing to do with the code -- so
    deleting the error handling would not have turned it red. A test that
    cannot fail for its stated reason is decoration; this one works at any uid.
    """
    target = tmp_path / "logs"
    target.mkdir()
    real_open = Path.open

    def refuse(self, *args, **kwargs):
        if self.name == ledger.LEDGER_NAME:
            raise OSError("No space left on device")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse)
    path = ledger.record(
        target, run_id="r", recipe="demo", model="m", status="completed",
        usage={}, attachments=[], duration_ms=1, stateful=False,
        service_tier=None, thinking_level=None, credential_kind="env:X",
    )
    assert not path.exists(), "nothing written, but no exception either"


# -- config failures ---------------------------------------------------------


@pytest.mark.parametrize(
    "toml",
    [
        "[privacy\n",                                    # malformed TOML
        '[authorization]\nmax_unauthorized_tokens = "lots"\n',  # wrong type
        '[auth]\nkey_command = "pass show x"\n',         # section refused by design
    ],
    ids=["malformed", "non-numeric-threshold", "auth-in-project-config"],
)
def test_a_bad_project_config_is_an_error_not_a_traceback(
    project, monkeypatch, capsys, toml
):
    """Config.load raised straight through every command -- tomllib on a typo,
    ValueError on a non-numeric gate threshold, ConfigError for [auth]. All
    three failed closed, but as tracebacks, and every other refusal in this
    CLI terminates in a sentence a person can act on."""
    (project.root / ".gemini-bridge.toml").write_text(toml)
    code = cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "q",
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


# -- API-side failures ------------------------------------------------------


@pytest.mark.parametrize("status", ["failed", "cancelled", "incomplete"])
def test_bad_status_is_recorded_not_swallowed(project, monkeypatch, status, capsys):
    code = run_ask(project, monkeypatch, status=status, text="")
    assert code == 2, "a non-success must not exit 0"
    entries = read_ledger(project)
    assert entries[0]["status"] == status
    assert status in capsys.readouterr().err


def test_stored_interaction_is_disclosed_to_the_user(project, monkeypatch, capsys):
    run_ask(project, monkeypatch)
    out = capsys.readouterr().out
    assert "cannot be deleted" in out


# -- the guards -------------------------------------------------------------


def test_secret_in_the_prompt_is_refused(project, monkeypatch, capsys):
    import sys
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai()))
    code = cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "here is my key sk-" + "a" * 32,
    ])
    assert code == 1
    assert "refusing to send" in capsys.readouterr().err
    assert not read_ledger(project), "nothing should have been sent"


def test_default_patterns_block_a_key_file_with_no_config(project, monkeypatch, capsys):
    """The guard used to default to empty, protecting nobody."""
    key = project.root / "id_rsa"
    key.write_bytes(b"\x89PNG\r\n\x1a\n")
    code = cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(key), "look",
    ])
    assert code == 1
    assert "sensitive path pattern" in capsys.readouterr().err


def test_override_flag_allows_a_flagged_prompt(project, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai()))
    assert cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "--allow-prompt-secrets",
        "key sk-" + "a" * 32,
    ]) == 0


def test_bypass_still_prints_what_it_found(project, monkeypatch, capsys):
    """--allow-prompt-secrets means "send anyway", not "don't look".

    The flag exists for false positives, but it used to skip the scan
    entirely -- so a real secret sent under it produced no output at all, and
    the one moment the user could still stop (the finding on screen, the call
    not yet made) was silently removed. Findings must print; only the block
    is waived.
    """
    import sys
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai()))
    code = cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "--allow-prompt-secrets",
        "key sk-" + "a" * 32,
    ])
    assert code == 0, "the bypass must still send"
    err = capsys.readouterr().err
    assert "looks like a" in err, "the finding must still be shown"
    assert "sending despite" in err, "the waiver itself must be stated"


def test_config_off_scan_stays_off(project, monkeypatch, capsys):
    """scan_prompt = false is the standing opt-out; it prints nothing.

    Distinct from the flag: the config route says "this project does not
    scan", the flag says "this finding is a false positive". Only the second
    implies there is something to show."""
    import sys
    (project.root / ".gemini-bridge.toml").write_text(
        "[privacy]\nscan_prompt = false\n"
    )
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai()))
    assert cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "key sk-" + "a" * 32,
    ]) == 0
    assert "looks like a" not in capsys.readouterr().err


def test_ledger_file_is_owner_only(project, monkeypatch):
    """The ledger carries the same provenance class as the run files.

    Run directories and their contents are chmod 0o600/0o700; the ledger
    beside them records model, recipe, session id, and interaction ids, and
    was left at default umask -- sweepable into any backup the run files were
    protected from."""
    assert run_ask(project, monkeypatch) == 0
    ledger_path = project.root / runs.RUNS_DIRNAME / ledger.LEDGER_NAME
    assert ledger_path.stat().st_mode & 0o777 == 0o600


# -- the ledger as a read surface -------------------------------------------


def test_ledger_read_survives_unreadable_files_and_junk_lines(tmp_path):
    """read() feeds stats, uploads, and doctor -- paths that must not crash.

    An unreadable file reads as empty, matching record()'s own OSError
    swallow: the two directions must agree that the ledger is never the
    reason something fails. And a valid-JSON line that is not an object is
    skipped like a corrupt one, instead of surfacing an AttributeError from
    whoever indexes the row."""
    p = tmp_path / ledger.LEDGER_NAME
    p.write_bytes(b'42\n{"run_id": "ok"}\n')
    assert ledger.read(tmp_path) == [{"run_id": "ok"}]
    p.chmod(0o000)
    try:
        assert ledger.read(tmp_path) == []
    finally:
        p.chmod(0o600)


# -- session-cap config validation -------------------------------------------


def test_session_cap_config_rejects_nonsense_cleanly(project, monkeypatch, capsys):
    """`true` and negatives must die as one clean ConfigError.

    The first version raised the bool complaint inside a try whose own
    except re-wrapped it into a self-contradicting composite ("must be
    integers ... or false to disable"), and int() accepted -1 -- the common
    'unlimited' idiom -- as a live cap that gates every call, the opposite of
    what the user meant."""
    (project.root / ".gemini-bridge.toml").write_text(
        "[authorization]\nmax_session_tokens = true\n"
    )
    assert run_ask(project, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "max_session_tokens" in err
    assert "must be integers:" not in err, "the garbled composite is back"

    (project.root / ".gemini-bridge.toml").write_text(
        "[authorization]\nmax_session_tokens = -1\n"
    )
    assert run_ask(project, monkeypatch) == 1
    assert "max_session_tokens" in capsys.readouterr().err


# -- doctor's degradation reporting ------------------------------------------


def test_doctor_reports_missing_ffprobe_even_with_the_gate_off(
    project, monkeypatch, capsys
):
    """`required = false` is exactly the configuration where the manifest
    estimate is the only cost signal left, so the degradation notice must not
    live inside the gate's else-branch -- which is where it first shipped,
    printing nothing for the projects that needed it most."""
    (project.root / ".gemini-bridge.toml").write_text(
        "[authorization]\nrequired = false\n"
    )
    monkeypatch.setattr(
        cli.shutil, "which",
        lambda name: None if name == "ffprobe" else f"/usr/bin/{name}",
    )
    assert cli.main(["--project-root", str(project.root), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "spend gate     : OFF" in out
    assert "ffprobe" in out


# -- the secret-scan refusal's stance ---------------------------------------


def test_secret_refusal_terminates_in_a_user_decision(project, monkeypatch, capsys):
    """The refusal must end with the user, like the spend gate's does.

    The old message said "pass --allow-prompt-secrets if these are false
    positives" -- an instruction the main loop will helpfully follow, which is
    the exact failure authorization._missing_message documents and avoids. The
    flag stays discoverable; the refusal itself hands the decision to the user
    instead of naming the workaround as the caller's next step.
    """
    secret = "ghp_" + "a" * 36
    assert run_ask(project, monkeypatch, question=f"is {secret} ok") == 1
    err = capsys.readouterr().err
    assert "pass --allow-prompt-secrets" not in err
    assert "Do not add --allow-prompt-secrets yourself" in err
    assert "tell the user" in err.lower()


# -- SDK error redaction -----------------------------------------------------


def test_a_call_error_echoing_a_key_is_scrubbed_everywhere(project, monkeypatch, capsys):
    """The one path where the constructor's type-name-only discipline was not
    applied: `interactions.create` failures surfaced str(exc) raw, into
    stderr, error.txt, and the ledger's error field at once. An SDK error that
    echoes request details must not relocate a key into all three."""
    key = "AIza" + "B" * 35

    class Boom:
        def create(self, **_kw):
            raise RuntimeError(f"401 for key {key}")

    import sys as _sys
    monkeypatch.setitem(_sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=lambda **_kw: SimpleNamespace(
            interactions=Boom()
        ))
    ))
    assert cli.main([
        "--project-root", str(project.root), "ask", "-r", "demo",
        "-f", str(project.image), "what is this",
    ]) == 1
    out = capsys.readouterr()
    assert key not in out.err and key not in out.out
    run_dir = next((project.root / runs.RUNS_DIRNAME).glob("*-demo*"))
    assert key not in (run_dir / "error.txt").read_text()
    assert key not in (read_ledger(project)[0]["error"] or "")
