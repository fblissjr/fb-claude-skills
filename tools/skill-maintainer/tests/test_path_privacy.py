"""Whole-tree path audit.

path-privacy: skip-file -- this file is fixtures for the leak check itself, so it
contains deliberately leak-shaped paths. Without this marker the plugin's own
scanner hard-blocks any commit that stages it.

The pre-commit hook only sees files in the staged set: `--staged` collects names
via `git diff --cached --name-only` and scans each of those files' full content.
So a leak in a file you never touch is never scanned, and five absolute paths
carrying a username sat in a tracked doc for 157 days that way. This audit
covers the whole tree instead, which is the gap the hook cannot reach.

(An earlier version of this docstring said the hook "scans the diff, so it only
ever sees added lines". That was never true -- `--staged` has passed whole files
to the scanner since 0.1.0. The distinction matters: whole-content scanning of
staged files is why editing a long-lived file can block a commit over lines you
did not write, which reads as a surprise if you expect a diff scan.)

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


# --- wrapper/plugin version comparison ---------------------------------------
# The stale-wrapper notice decides between two OPPOSITE remedies: an older
# wrapper should be refreshed with install-git-hooks.sh, a newer one must not be
# (regenerating it from the older plugin downgrades a working gate). That check
# was a bare `!=` in three separate places, so it could not tell the cases apart
# and all three drifted independently. These pin the shared helper.

_PLUGIN = Path(__file__).resolve().parents[3] / "skills" / "path-privacy"
_VERSION_LIB = _PLUGIN / "skills" / "path-privacy" / "scripts" / "_version_compare.sh"
_INSTALLER = _PLUGIN / "skills" / "path-privacy" / "scripts" / "install-git-hooks.sh"


def _is_newer(a: str, b: str, lib: Path | None = None) -> bool:
    """Run the real shell helper; exit 0 means 'a is strictly newer than b'."""
    script = f'. "{lib or _VERSION_LIB}"; pp_version_is_newer "{a}" "{b}"'
    return subprocess.run(["bash", "-c", script]).returncode == 0


def test_newer_version_is_detected():
    assert _is_newer("0.7.3", "0.7.2")


def test_older_version_is_not_newer():
    assert not _is_newer("0.7.1", "0.7.2")


def test_equal_version_is_not_newer():
    assert not _is_newer("0.7.2", "0.7.2")


def test_double_digit_component_orders_numerically():
    """0.9.0 vs 0.10.0 -- a lexicographic compare inverts this.

    path-privacy shipped exactly that bug in 0.3.2, in the cache-selection glob.
    """
    assert _is_newer("0.10.0", "0.9.0")
    assert not _is_newer("0.9.0", "0.10.0")


def test_unknown_stamp_is_never_treated_as_newer():
    """`unknown` is written when plugin.json is unreadable at install time.

    Under `sort -V` it sorts ABOVE a numeric version, so a naive comparison
    routes it to the ahead branch and tells the user NOT to refresh a wrapper
    of unknown, probably ancient provenance -- the opposite of the right advice.
    """
    assert not _is_newer("unknown", "0.7.2")


def test_prehistoric_stamp_is_never_treated_as_newer():
    assert not _is_newer("pre-0.6.0", "0.7.2")


def test_unparsable_versions_are_never_treated_as_newer():
    """Anything not plainly numeric must fail toward the idempotent remedy."""
    assert not _is_newer("", "0.7.2")
    assert not _is_newer("0.7.2-rc1", "0.7.2")
    assert not _is_newer("0.7.2", "")


def test_generated_wrapper_carries_the_helper_inline():
    """A wrapper is frozen at install time and cannot source anything at runtime.

    If the helper stops being injected, the wrapper's version notice silently
    reverts to whatever an undefined function does -- so pin the injection.
    """
    src = _INSTALLER.read_text(encoding="utf-8")
    assert "$VERSION_COMPARE_SRC" in src, "wrapper heredoc no longer injects the helper"


def test_no_call_site_reintroduces_a_bare_version_inequality():
    """The bug class, not the three instances.

    A bare `!=` between a wrapper stamp and a plugin version is direction-blind.
    Guard the shape rather than trusting three copies to stay in step.
    """
    hooks = (_PLUGIN / "hooks" / "session-start.sh").read_text(encoding="utf-8")
    installer = _INSTALLER.read_text(encoding="utf-8")
    for name, body in (("session-start.sh", hooks), ("install-git-hooks.sh", installer)):
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "!=" not in stripped:
                continue
            # The one legitimate `!=` is the cheap equality shortcut that guards
            # the direction test; it must be followed by a pp_version_is_newer call.
            if "VERSION" in stripped and "pp_version_is_newer" not in body:
                raise AssertionError(f"{name}: bare version inequality: {stripped}")
