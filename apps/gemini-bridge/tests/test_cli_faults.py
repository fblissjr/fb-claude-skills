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
    assert read_ledger(project)[0]["allow_prompt_secrets"] is True


def test_ordinary_calls_record_the_bypass_as_false(project, monkeypatch):
    """False, not absent -- a filter for risky runs must not depend on a key
    that only exists on the risky ones."""
    assert run_ask(project, monkeypatch) == 0
    assert read_ledger(project)[0]["allow_prompt_secrets"] is False


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


def test_ledger_write_failure_is_swallowed(project, monkeypatch, tmp_path):
    """Logging must never be the reason a call fails.

    `ledger.record` opens a file and deliberately catches OSError: a read-only
    directory should cost you the record, not the answer.
    """
    read_only = tmp_path / "ro"
    read_only.mkdir()
    read_only.chmod(0o500)
    try:
        path = ledger.record(
            read_only, run_id="r", recipe="demo", model="m", status="completed",
            usage={}, attachments=[], duration_ms=1, stateful=False,
            service_tier=None, thinking_level=None, credential_kind="env:X",
        )
        assert not path.exists(), "nothing written, but no exception either"
    finally:
        read_only.chmod(0o700)


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
