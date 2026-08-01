"""Tests for credential resolution.

The key must never reach disk, a log, or a traceback, and the tool must not
require any particular secret manager. Both properties are load-bearing and
neither was covered.
"""

from __future__ import annotations

import pytest

from gemini_bridge import auth


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in (auth.KEY_COMMAND_ENV, *auth.API_KEY_ENVS):
        monkeypatch.delenv(var, raising=False)


# -- precedence -------------------------------------------------------------


def test_argument_beats_everything(monkeypatch):
    monkeypatch.setenv(auth.KEY_COMMAND_ENV, "echo from-env-command")
    monkeypatch.setenv("GEMINI_API_KEY", "from-env-key")
    creds = auth.resolve("echo from-argument", config_key_command="echo from-config")
    assert creds.api_key == "from-argument"


def test_env_command_beats_config(monkeypatch):
    monkeypatch.setenv(auth.KEY_COMMAND_ENV, "echo from-env-command")
    assert auth.resolve(config_key_command="echo from-config").api_key == "from-env-command"


def test_config_beats_plain_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env-key")
    assert auth.resolve(config_key_command="echo from-config").api_key == "from-config"


def test_plain_key_is_the_zero_setup_fallback(monkeypatch):
    # No secret manager required. This is the path for someone who just wants
    # to export a variable and go.
    monkeypatch.setenv("GEMINI_API_KEY", "plain")
    creds = auth.resolve()
    assert creds.api_key == "plain"
    assert creds.kind == "env:GEMINI_API_KEY"


def test_google_api_key_is_also_accepted(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "plain")
    assert auth.resolve().kind == "env:GOOGLE_API_KEY"


def test_no_credentials_names_every_option():
    with pytest.raises(auth.AuthError) as exc:
        auth.resolve()
    message = str(exc.value)
    assert auth.KEY_COMMAND_ENV in message
    assert "GEMINI_API_KEY" in message


# -- the key must not escape ------------------------------------------------


def test_repr_redacts_the_key():
    creds = auth.Credentials(api_key="super-secret-value", kind="key-command")
    assert "super-secret-value" not in repr(creds)
    assert "<redacted>" in repr(creds)


def test_provenance_is_coarse_for_commands():
    # A key command names a vault and an item, and this label is written to
    # disk in the ledger. It must not carry the command itself.
    creds = auth.resolve(key_command="echo x")
    assert creds.kind == "key-command"


def test_failure_message_does_not_echo_the_command():
    # stderr routinely repeats the secret reference back.
    with pytest.raises(auth.AuthError) as exc:
        auth.resolve(key_command="false vault-name-that-should-not-appear")
    assert "vault-name-that-should-not-appear" not in str(exc.value)


# -- command handling -------------------------------------------------------


def test_output_is_stripped():
    assert auth.resolve(key_command="echo   padded  ").api_key == "padded"


def test_quoted_arguments_survive():
    assert auth.resolve(key_command="echo 'two words'").api_key == "two words"


def test_missing_binary_is_named():
    with pytest.raises(auth.AuthError, match="not found on PATH"):
        auth.resolve(key_command="definitely-not-a-real-binary-xyz")


def test_unparseable_command():
    with pytest.raises(auth.AuthError, match="not parseable"):
        auth.resolve(key_command="unbalanced 'quote")


def test_empty_output_is_rejected():
    with pytest.raises(auth.AuthError, match="no output"):
        auth.resolve(key_command="true")


def test_multiword_failure_hints_at_quoting():
    # The commonest real cause: an item name containing a space, split into
    # separate arguments because inner quotes were omitted.
    with pytest.raises(auth.AuthError, match="quote it inside"):
        auth.resolve(key_command="false one two three")


@pytest.mark.parametrize(
    "command,expected",
    [
        # Passed to execve as literal argv, never to a shell. The separator
        # and the substitution syntax come back as text, which proves no
        # second command ran and no expansion happened.
        ("echo safe; echo pwned", "safe; echo pwned"),
        ("echo $(whoami)", "$(whoami)"),
        ("echo a|b", "a|b"),
    ],
)
def test_shell_metacharacters_are_not_interpreted(command, expected):
    assert auth.resolve(key_command=command).api_key == expected
