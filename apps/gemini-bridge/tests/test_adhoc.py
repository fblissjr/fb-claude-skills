"""Recipe-free calls and CLI parameter parity.

The claim under test: every parameter a recipe can set is settable from the
command line, and a call with no recipe at all is a first-class run -- labeled
`adhoc` in the run directory and the ledger, sending no system_instruction
unless one was given explicitly. Delete these tests and `-r` silently becomes
load-bearing again: the CLI flags could drop through to recipe defaults with
nothing noticing, and an ad-hoc run could go out mislabeled or with an empty
system_instruction block the API bills for.

Precedence pinned here: CLI flag > recipe value > built-in default.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import orjson
import pytest

from gemini_bridge import auth, cli, ledger, runs


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Same isolation as test_cli_faults: HOME redirected so the developer's
    real user config never leaks into captured output."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    (tmp_path / "home" / ".config").mkdir(parents=True)
    # These arms are about parameter plumbing, and several of them use --store
    # or raised thinking, which the spend gate now stops. Turning it off here
    # keeps them testing what they claim to; the gate has its own suite, and
    # test_video covers it end to end through the CLI.
    (tmp_path / ".gemini-bridge.toml").write_text(
        "[authorization]\nrequired = false\n"
    )
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "demo.md").write_text(
        "---\nmodel: recipe-model\nthinking_level: low\nseed: 7\n---\n\nBe terse.\n"
    )
    monkeypatch.setattr(cli, "_bundled_recipe_dirs", lambda: [recipes_dir])
    monkeypatch.setattr(
        auth, "resolve",
        lambda *a, **k: auth.Credentials(api_key="fake", kind="env:TEST"),
    )
    image = tmp_path / "a.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    return SimpleNamespace(root=tmp_path, image=image)


def install_fake_genai(monkeypatch, status="completed", text="fine",
                       interaction_id=None):
    class FakeInteractions:
        def create(self, **_kw):
            return SimpleNamespace(
                id=interaction_id, status=status, output_text=text,
                usage=SimpleNamespace(model_dump=lambda: {"total_input_tokens": 5}),
            )

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=lambda **_kw: SimpleNamespace(
            interactions=FakeInteractions()
        ))
    ))


def ask(project, *argv):
    return cli.main(["--project-root", str(project.root), "ask", *argv])


def recorded_request(project, label="adhoc"):
    run_dir = next((project.root / runs.RUNS_DIRNAME).glob(f"*-{label}*"))
    return orjson.loads((run_dir / "request.json").read_bytes())


# -- recipe-free calls ------------------------------------------------------


def test_ask_without_recipe_or_files_is_a_complete_run(project, monkeypatch):
    """A bare text question is a legitimate call: run dir, ledger row, no
    attachment or recipe required."""
    install_fake_genai(monkeypatch)
    assert ask(project, "what is the capital of France") == 0
    entries = ledger.read(project.root / runs.RUNS_DIRNAME)
    assert len(entries) == 1
    assert entries[0]["recipe"] == "adhoc"
    assert entries[0]["status"] == "completed"


def test_adhoc_call_sends_no_system_instruction(project, monkeypatch):
    """An empty system_instruction must be omitted, not sent as "". The field
    is interaction-scoped and billed; a blank one is pure waste and makes the
    recorded request lie about what shaped the answer."""
    install_fake_genai(monkeypatch)
    assert ask(project, "q") == 0
    assert "system_instruction" not in recorded_request(project)


def test_system_file_supplies_the_instruction(project, monkeypatch, tmp_path):
    install_fake_genai(monkeypatch)
    stance = tmp_path / "stance.md"
    stance.write_text("Answer in one word.\n")
    assert ask(project, "--system-file", str(stance), "q") == 0
    assert recorded_request(project)["system_instruction"] == "Answer in one word."


def test_system_flag_with_recipe_is_refused(project, monkeypatch, capsys):
    """The ledger records the recipe's name; swapping its stance under that
    name would mislabel the run. One or the other."""
    install_fake_genai(monkeypatch)
    assert ask(project, "-r", "demo", "--system", "other stance",
               "-f", str(project.image), "q") == 1
    assert "recipe" in capsys.readouterr().err


def test_missing_recipe_error_is_unchanged(project, monkeypatch, capsys):
    """-r going optional must not turn a typo'd recipe name into a silent
    ad-hoc call."""
    install_fake_genai(monkeypatch)
    assert ask(project, "-r", "nope", "q") == 1
    assert "not found" in capsys.readouterr().err


# -- parameter flags --------------------------------------------------------


def test_generation_flags_reach_the_request(project, monkeypatch):
    install_fake_genai(monkeypatch)
    assert ask(project, "--model", "m-x", "--thinking-level", "high",
               "--seed", "3", "--max-output-tokens", "99",
               "--service-tier", "flex", "q") == 0
    req = recorded_request(project)
    assert req["model"] == "m-x"
    assert req["generation_config"] == {
        "thinking_level": "high", "seed": 3, "max_output_tokens": 99,
    }
    assert req["service_tier"] == "flex"


def test_adhoc_thinking_defaults_to_minimal(project, monkeypatch):
    """Thinking runs by default server-side and bills at the output rate; the
    probed cost finding stands for ad-hoc calls too."""
    install_fake_genai(monkeypatch)
    assert ask(project, "q") == 0
    req = recorded_request(project)
    assert req["generation_config"]["thinking_level"] == "minimal"


def test_cli_flags_override_recipe_values(project, monkeypatch):
    """CLI > recipe > default. The demo recipe says low/7; the flags must win
    without disturbing the recipe field the CLI did not mention (seed)."""
    install_fake_genai(monkeypatch)
    assert ask(project, "-r", "demo", "-f", str(project.image),
               "--thinking-level", "high", "q") == 0
    req = recorded_request(project, label="demo")
    assert req["generation_config"]["thinking_level"] == "high"
    assert req["generation_config"]["seed"] == 7
    assert req["model"] == "recipe-model"


def test_store_flag_enables_continuation(project, monkeypatch):
    install_fake_genai(monkeypatch, interaction_id="v1_abc")
    assert ask(project, "--store", "q") == 0
    assert recorded_request(project)["store"] is True
    entry = ledger.read(project.root / runs.RUNS_DIRNAME)[0]
    assert entry["stateful"] is True


def test_continue_from_without_store_is_refused(project, monkeypatch, capsys):
    """previous_interaction_id requires store=true; an ad-hoc call must hit
    the same guard a stateless recipe does."""
    install_fake_genai(monkeypatch)
    assert ask(project, "--continue-from", "v1_abc", "q") == 1
    assert "store" in capsys.readouterr().err


def test_schema_file_requests_structured_output(project, monkeypatch, tmp_path):
    install_fake_genai(monkeypatch, text='{"ok": true}')
    schema = tmp_path / "schema.json"
    schema.write_bytes(orjson.dumps({"type": "object"}))
    assert ask(project, "--schema-file", str(schema), "q") == 0
    req = recorded_request(project)
    assert req["response_format"]["schema"] == {"type": "object"}


def test_invalid_schema_file_fails_before_any_call(project, monkeypatch, capsys):
    install_fake_genai(monkeypatch)
    bad = project.root / "bad.json"
    bad.write_text("{not json")
    assert ask(project, "--schema-file", str(bad), "q") == 1
    assert not ledger.read(project.root / runs.RUNS_DIRNAME), \
        "nothing may be sent on a config error"


def test_labels_parse_and_reach_the_request(project, monkeypatch):
    install_fake_genai(monkeypatch)
    assert ask(project, "--label", "team=viz", "--label", "run=ci", "q") == 0
    assert recorded_request(project)["labels"] == {"team": "viz", "run": "ci"}


def test_malformed_label_is_refused(project, monkeypatch, capsys):
    install_fake_genai(monkeypatch)
    assert ask(project, "--label", "no-equals-sign", "q") == 1
    assert "label" in capsys.readouterr().err


# -- scan coverage of the new channels --------------------------------------


def test_adhoc_system_text_is_scanned(project, monkeypatch, capsys, tmp_path):
    """--system-file is outgoing text exactly like a recipe body was; the 0.6.0
    lesson was that an unscanned channel stays unscanned until named."""
    install_fake_genai(monkeypatch)
    stance = tmp_path / "stance.md"
    stance.write_text("use key sk-" + "a" * 32)
    assert ask(project, "--system-file", str(stance), "q") == 1
    assert "refusing to send" in capsys.readouterr().err


def test_schema_content_is_scanned(project, monkeypatch, capsys, tmp_path):
    """Schema descriptions travel in the request too -- the follow-up gap
    recorded in the 2026-08-03 log, closed here."""
    install_fake_genai(monkeypatch)
    schema = tmp_path / "schema.json"
    schema.write_bytes(orjson.dumps({
        "type": "object",
        "description": "authenticate with sk-" + "b" * 32,
    }))
    assert ask(project, "--schema-file", str(schema), "q") == 1
    assert "refusing to send" in capsys.readouterr().err


def test_label_values_are_scanned(project, monkeypatch, capsys):
    install_fake_genai(monkeypatch)
    assert ask(project, "--label", "token=sk-" + "c" * 32, "q") == 1
    assert "refusing to send" in capsys.readouterr().err


def test_dry_run_without_recipe_calls_nothing(project, monkeypatch, capsys):
    """--dry-run's promise is that nothing leaves the machine; it must hold
    on the recipe-free path and show the effective parameters."""
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=lambda **_kw: (_ for _ in ()).throw(
            AssertionError("dry-run must not construct a client")
        ))
    ))
    assert ask(project, "--dry-run", "--thinking-level", "medium", "q") == 0
    out = capsys.readouterr().out
    assert "adhoc" in out
    assert "medium" in out
