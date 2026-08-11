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
        # These two are fixtures for the very shape the scanner exists to
        # notice, so they cannot be written as `<user>` placeholders without
        # testing something else. `somebody` is not a real account; the repo
        # audit's allowlist just does not know the word.
        "/Users/somebody/Desktop/shot.png",  # path-privacy: ignore
        "/home/somebody/project/file.txt",  # path-privacy: ignore
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


# -- regressions from the red-team pass -------------------------------------


@pytest.mark.parametrize(
    "sample",
    [
        # OpenAI's current dashboard formats. The original class excluded the
        # hyphen, so it missed every modern key of the type it was named for.
        "sk-proj-" + "a" * 40,
        "sk-svcacct-" + "b" * 40,
        "sk-admin-" + "c" * 40,
        # GitHub's recommended format since 2022.
        "github_pat_" + "d" * 55,
        # Underscore-separated shapes the hyphen-only class could not reach.
        "sk_live_" + "e" * 24,
        "rk_live_" + "f" * 24,
        "npm_" + "g" * 36,
        "SG." + "h" * 22 + "." + "i" * 22,
        # A connection string: the password is inline and people paste these
        # constantly while debugging.
        "postgres://user:Sup3rSecretPW@db.internal:5432/app",
    ],
)
def test_modern_secret_shapes_block(sample):
    assert content.blocking(content.scan(sample)), f"missed {sample[:16]}..."


@pytest.mark.parametrize("length", [13, 15, 20, 40, 200])
def test_redaction_never_reveals_more_than_a_third(length):
    """The old formula was a fixed head+tail and did not scale.

    On a 15-character match it showed 10 characters, leaving five to brute
    force. Redaction has to be a function of the input length.
    """
    secret = "x" * length
    excerpt = content._redact(secret)
    revealed = len(excerpt.replace("...", ""))
    assert revealed <= max(1, length // 3)
    assert revealed <= 10


# -- the scanner must not be the thing that breaks the call -----------------


def test_a_long_unbroken_run_does_not_blow_up_the_scan():
    """Catastrophic backtracking, found by running the real CLI on real input.

    Two patterns ended a greedy character class with a literal that the class
    excludes -- `[A-Za-z0-9._%+-]+@` and `[a-z][a-z0-9+.-]*://`. On text with
    no separator to break the run, each start position consumed to the end and
    backtracked one character at a time looking for a delimiter that is not
    there: quadratic, and measured at ~275s for a 400KB prompt. The tool sat
    there producing nothing, on the guard path, before anything was sent.

    The trigger is not exotic. A base64 blob, a minified bundle, a hex digest
    or a data: URI pasted into `--prompt-file` is exactly this shape.

    Timed rather than counted because Python exposes no backtracking counter.
    The margin is wide on purpose: this input measured ~7s before the fix and
    runs in single-digit milliseconds after it, so a one-second budget is far
    below the bug and far above any plausible scheduling noise.
    """
    import time

    start = time.perf_counter()
    content.scan("x" * 65536)
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize(
    "sample,name",
    [
        ("contact me at real.person@example.com please", "email address"),
        ("postgres://user:swordfish@db.internal:5432/app",
         "connection string with password"),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNH", "jwt"),
    ],
)
def test_the_patterns_still_match_after_being_made_possessive(sample, name):
    """The counterweight. Possessive quantifiers only remove backtracking that
    could never lead to a match -- the delimiter is excluded from the class in
    every case changed -- so every one of these must still fire. If a fix for
    the arm above silently narrowed what the scanner catches, this goes red."""
    assert name in {f.name for f in content.scan(sample)}


def test_redact_secrets_scrubs_key_material_and_keeps_the_context():
    """Error messages travel: stderr, error.txt, the ledger, bug reports.

    An SDK exception string can echo request details, and the call and upload
    paths surface `str(exc)` -- unlike the client-constructor path, which
    reduces to a type name precisely because a key-format error embeds the
    value. `redact_secrets` closes that asymmetry: blocking matches are
    replaced, the diagnostic context around them survives, because an error
    message with the useful part removed just gets the command re-run.
    """
    key = "AIza" + "A" * 35
    text = f"401 UNAUTHENTICATED for key {key} at /v1/interactions"
    scrubbed = content.redact_secrets(text)
    assert key not in scrubbed
    assert "401" in scrubbed and "/v1/interactions" in scrubbed
    assert "google api key" in scrubbed  # says WHAT was scrubbed, not the value


def test_redact_secrets_leaves_warn_level_matches_alone():
    """Emails and home paths are warn-level in the scanner because they are
    legitimate in prose -- and in an error message a path is usually the
    diagnostic. Only blocking shapes are scrubbed."""
    text = (
        "could not read /Users/someone/clip.mp4"  # path-privacy: ignore
        " (owner: dev@example.com)"
    )
    assert content.redact_secrets(text) == text
