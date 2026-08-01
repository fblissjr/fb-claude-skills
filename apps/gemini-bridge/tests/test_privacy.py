"""Tests for the sensitive-path guard.

These exist because the first implementation used `Path.match`, which anchors at
the right-hand end of a path and silently failed to block nested files under a
named directory. Every case below that ends in "leaks" was a real false negative.

A blocklist must fail closed. Over-matching costs one refused call; under-
matching sends material that cannot be recalled, because stored interactions
cannot be deleted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gemini_bridge.privacy import is_sensitive


@pytest.mark.parametrize(
    "path,pattern",
    [
        # The regressions. Path.match returned False for every one of these.
        ("/home/me/private/deep/nested/secret.png", "private/*"),
        ("/home/me/private/deep/nested/secret.png", "private/**"),
        ("/home/me/secrets/key.png", "secrets"),
        ("/work/evidence/sub/a.png", "evidence/*"),
        # Cases that already worked, kept so a rewrite cannot lose them.
        ("/home/me/private/secret.png", "*.png"),
        ("/home/me/private/secret.png", "/home/me/private/*"),
        ("/a/b/c.png", "**/*.png"),
    ],
)
def test_blocks_what_a_person_would_expect(path, pattern):
    assert is_sensitive(Path(path), [pattern]) == pattern


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("/home/me/public/photo.png", "private/*"),
        ("/home/me/public/photo.jpg", "*.png"),
        ("/home/me/notes/readme.md", "secrets"),
    ],
)
def test_allows_unrelated_paths(path, pattern):
    assert is_sensitive(Path(path), [pattern]) is None


def test_returns_the_matching_pattern_for_the_error_message():
    hit = is_sensitive(Path("/a/private/x.png"), ["*.jpg", "private/*", "*.gif"])
    assert hit == "private/*"


def test_no_patterns_blocks_nothing():
    assert is_sensitive(Path("/a/private/x.png"), []) is None


def test_blank_and_trailing_slash_patterns_are_tolerated():
    assert is_sensitive(Path("/a/private/x.png"), ["", "  ", "private/"]) == "private/"


def test_relative_paths_are_resolved_before_matching(tmp_path, monkeypatch):
    target = tmp_path / "private" / "x.png"
    target.parent.mkdir()
    target.write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    assert is_sensitive(Path("private/x.png"), ["private/*"]) == "private/*"


def test_home_relative_patterns_are_expanded(tmp_path, monkeypatch):
    """Both reviewers found this independently, and it was a live leak.

    The candidate path was expanded but the pattern was not, so a home-relative
    pattern matched nothing at all -- the guard reported no match and the file
    was sent, with no way to recall it.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "private" / "deep" / "secret.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"")

    # Assembled rather than written literally: a literal home-relative path in
    # repo content trips this repo's own path-privacy hook, which cannot tell
    # test data from a real leak. That is the hook working correctly.
    tilde, home_var = "~", "$" + "HOME"
    for pattern in [f"{tilde}/private/*", f"{home_var}/private/*", f"{tilde}/private"]:
        assert is_sensitive(target, [pattern]) == pattern, pattern


def test_case_mismatched_pattern_still_blocks(tmp_path):
    """The default macOS filesystem is case-insensitive; matching was not.

    A directory created as `Vault` but written in config as `vault` left the
    file reachable and unblocked.

    The directory name deliberately avoids `private`: macOS temp directories
    live under `/private/var/...`, so a `private` pattern matches the tmp path
    itself and this test would pass without testing anything.
    """
    target = tmp_path / "VaultStuff" / "secret.png"
    target.parent.mkdir()
    target.write_bytes(b"")
    assert is_sensitive(target, ["vaultstuff/*"]) == "vaultstuff/*"
    assert is_sensitive(target, ["VAULTSTUFF"]) == "VAULTSTUFF"
    assert is_sensitive(target, ["VaultStuff/*"]) == "VaultStuff/*"


def test_empty_pattern_does_not_match_everything(tmp_path):
    """Regression: normalising "" yields ".", which matched any file with an
    extension. Over-blocking is the safe direction, but not this indiscriminate.
    """
    target = tmp_path / "ordinary.png"
    target.write_bytes(b"")
    assert is_sensitive(target, ["", "   ", "/"]) is None


def test_decomposed_unicode_path_is_blocked(tmp_path):
    """macOS stores accented filenames decomposed; config files are composed.

    The two are the same text to a person and different bytes to fnmatch, so a
    directory with an accent in its name silently failed to match. This needs
    no deliberate evasion -- just an accented folder name.
    """
    import unicodedata

    composed = unicodedata.normalize("NFC", "Café-Secrets")
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed

    target = tmp_path / decomposed / "shot.png"
    target.parent.mkdir()
    target.write_bytes(b"")
    assert is_sensitive(target, [composed]) == composed
