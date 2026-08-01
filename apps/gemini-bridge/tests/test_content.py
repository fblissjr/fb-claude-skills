"""Tests for outgoing-content scanning.

This closes the largest hole the privacy audit left open: the path guard checks
which FILES are attached and says nothing about the prompt, which is composed by
Claude after it has been reading the user's files.
"""

from __future__ import annotations

import pytest

from gemini_bridge import content


@pytest.mark.parametrize(
    "name,sample",
    [
        ("openai-style key", "sk-" + "a" * 32),
        ("anthropic-style key", "sk-ant-" + "a" * 24),
        ("github token", "ghp_" + "b" * 36),
        ("slack token", "xoxb-" + "1" * 20),
        ("google api key", "AIza" + "c" * 35),
        ("aws access key", "AKIA" + "D" * 16),
        ("private key block", "-----BEGIN RSA PRIVATE KEY-----"),
        ("ssh fingerprint", "SHA256:" + "e" * 43),
        ("secret reference", "op:" + "//Vault/Item/field"),
    ],
)
def test_secret_shapes_block(name, sample):
    findings = content.scan(f"look at this: {sample} thanks")
    assert any(f.name == name for f in findings), f"{name} not detected"
    assert content.blocking(findings), f"{name} should block, not warn"


def test_jwt_blocks():
    token = "eyJ" + "a" * 12 + ".eyJ" + "b" * 12 + "." + "c" * 12
    assert content.blocking(content.scan(token))


@pytest.mark.parametrize(
    "sample",
    [
        "someone@example.com",
        "/Users/somebody/Desktop/shot.png",
        "/home/somebody/project/file.txt",
    ],
)
def test_lower_confidence_shapes_warn_but_do_not_block(sample):
    findings = content.scan(sample)
    assert findings, "should be noticed"
    assert not content.blocking(findings), "should warn, not block"


def test_ordinary_prompt_is_clean():
    text = (
        "Compare these two renders of the same 3D scene. The first is BEFORE a "
        "change to the lighting rig, the second is AFTER. Report what a person "
        "would notice."
    )
    assert content.scan(text) == []


def test_findings_are_redacted():
    """A message naming what it found must not reproduce it.

    Printing the whole match relocates the secret into a terminal, a session
    transcript, and possibly a bug report.
    """
    secret = "sk-" + "z" * 40
    findings = content.scan(secret)
    assert findings
    for f in findings:
        assert secret not in f.excerpt
        assert secret not in str(f)
        assert "..." in f.excerpt


def test_duplicates_are_reported_once():
    secret = "ghp_" + "a" * 36
    findings = content.scan(f"{secret} and again {secret}")
    assert len([f for f in findings if f.name == "github token"]) == 1


def test_distinct_secrets_of_one_kind_are_all_reported():
    a, b = "ghp_" + "a" * 36, "ghp_" + "b" * 36
    findings = content.scan(f"{a} {b}")
    assert len([f for f in findings if f.name == "github token"]) == 2


def test_short_match_redaction_does_not_leak():
    # The redactor keeps head and tail; for a short string that could be most
    # of it, so it degrades to nothing rather than nearly-everything.
    assert content._redact("abc123") == "..."
