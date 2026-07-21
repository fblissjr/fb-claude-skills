"""Whole-tree path audit.

path-privacy: skip-file -- this file is fixtures for the leak check itself, so it
contains deliberately leak-shaped paths. Without this marker the plugin's own
scanner hard-blocks any commit that stages it.

The pre-commit hook scans the diff, so a leak introduced before it existed --
or in a file since touched only elsewhere -- survives indefinitely. Five
absolute paths carrying a username sat in a tracked doc for 157 days that way.
These tests pin both directions: it must fire on a real leak, and stay silent
on the placeholder and system paths that legitimately appear in this repo.
"""

import subprocess
from pathlib import Path

from skill_maintainer.tests import check_path_privacy


def _repo(tmp_path: Path, name: str, content: str) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return tmp_path


def _failed(results):
    return [r for r in results if not r.passed]


def test_real_username_path_is_caught(tmp_path):
    r = _repo(tmp_path, "doc.md", "see /Users/realpersonname/notes/thing.md\n")
    assert _failed(check_path_privacy(r)), "a real home path must fail the check"


def test_home_variant_is_caught(tmp_path):
    r = _repo(tmp_path, "doc.md", "path: /home/realpersonname/work/x\n")
    assert _failed(check_path_privacy(r))


def test_placeholder_is_not_a_leak(tmp_path):
    r = _repo(tmp_path, "doc.md", "use /Users/<name>/thing and /home/$USER/x\n")
    assert not _failed(check_path_privacy(r))


def test_macos_shared_is_not_a_leak(tmp_path):
    r = _repo(tmp_path, "doc.md", "system path /Users/Shared/data/x\n")
    assert not _failed(check_path_privacy(r))


def test_skip_file_marker_is_honoured(tmp_path):
    r = _repo(tmp_path, "scanner.sh",
              "# path-privacy: skip-file\nmatch /Users/realpersonname/x\n")
    assert not _failed(check_path_privacy(r))


def test_ignore_marker_is_honoured(tmp_path):
    r = _repo(tmp_path, "doc.md",
              "regex source /Users/realpersonname/x  path-privacy: ignore\n")
    assert not _failed(check_path_privacy(r))


def test_binary_files_do_not_crash(tmp_path):
    r = _repo(tmp_path, "blob.bin", "")
    (r / "blob.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    check_path_privacy(r)   # must not raise


def test_bare_home_path_without_trailing_slash_is_caught(tmp_path):
    """`cd /Users/janedoe` at end of line carries a username just as much."""
    r = _repo(tmp_path, "doc.md", "cd /Users/realpersonname\n")
    assert _failed(check_path_privacy(r))


def test_sanctioned_tilde_form_is_not_a_leak(tmp_path):
    """`<HOME>/.claude/...` is the repo's own approved replacement, used 143x.

    Adding ~ and $HOME to the pattern flagged the approved form as the thing it
    replaces. This check is about USERNAME exposure; the scanner's rule is about
    resolution outside the root. Different rules, deliberately.
    """
    r = _repo(tmp_path, "doc.md", "state lives in ~/.claude/agent_state.duckdb\n")
    assert not _failed(check_path_privacy(r))


def test_marker_quoted_deep_in_a_file_does_not_exempt_it(tmp_path):
    """Matching the marker anywhere let any file that merely mentions it opt out.

    Six tracked files including CHANGELOG.md were wholly exempt that way.
    """
    body = "\n".join(["filler"] * 40 + ["path-privacy: skip-file is the marker"])
    r = _repo(tmp_path, "doc.md", "leak /Users/realpersonname/x\n" + body + "\n")
    assert _failed(check_path_privacy(r))


def test_system_account_names_are_not_leaks(tmp_path):
    r = _repo(tmp_path, "doc.md", "brew lives at /home/linuxbrew/.linuxbrew\n")
    assert not _failed(check_path_privacy(r))
