"""path-privacy's shell gate, exercised as shell.

path-privacy: skip-file -- fixtures for the leak check itself, so this file is
full of deliberately leak-shaped paths.

WHY THIS FILE EXISTS. The file-level opt-out is defined in `_skip_marker.sh` and
consumed by three shell programs; the Python audit in `tests.py` keeps a
deliberate copy of the same rule. Before this file, every test of that rule went
through the Python copy. So editing `PP_SKIP_MARKER_RE` could break the scanner,
the scrub and the write blocker at once while the suite stayed green -- the
fail-open direction, in the component whose failure is invisible by construction.
A CHANGELOG entry claimed "thirteen shell probes" pinned this behaviour; they
were run by hand in one session and never committed, which is the same defect one
level up. These are those probes, made real.

The cross-engine test is the one that earns the duplicated regex its place: a
copy is only safe if something asserts the copies agree.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from skill_maintainer.tests import _SKIP_MARKER

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/path-privacy/skills/path-privacy/scripts"
HOOKS = REPO / "skills/path-privacy/hooks"
SCANNER = SCRIPTS / "find-external-paths.sh"
SCRUB = SCRIPTS / "scrub-paths.sh"
LIB = SCRIPTS / "_skip_marker.sh"
PRE_TOOL_USE = HOOKS / "path-privacy-pre-tool-use.sh"

LEAK = "/Users/realpersonname/x"

pytestmark = pytest.mark.skipif(
    not SCANNER.exists() or shutil.which("rg") is None,
    reason="path-privacy scripts or ripgrep unavailable",
)


def _scan_file(path: Path, root: Path) -> bool:
    """True when the scanner reports the file CLEAN (exit 0), i.e. exempt."""
    r = subprocess.run(
        [str(SCANNER), "--against-root", str(root), "-f", str(path)],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def _write(tmp_path: Path, body: str, name: str = "f.md") -> Path:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return f


# --- what the marker accepts and rejects, in the real shell ------------------

EXEMPT = [
    "# path-privacy: skip-file",
    "<!-- path-privacy: skip-file -->",
    "# path-privacy: skip-file -- regex source, every pattern looks like a leak",
    "   # path-privacy: skip-file",
    "// path-privacy: skip-file",
    "path-privacy: skip-file",
]

NOT_EXEMPT = [
    "## path-privacy: skip-file",                        # markdown H2
    "### path-privacy: skip-file",                       # markdown H3
    "* path-privacy: skip-file exempts a whole file",    # markdown bullet
    "    # path-privacy: skip-file",                     # indented code block
    "Opt out with `path-privacy: skip-file` at the top.",  # prose mention
    "`path-privacy: skip-file`",                         # backticked alone
    '  "_comment": "path-privacy: skip-file"',           # JSON string value
]


@pytest.mark.parametrize("line", EXEMPT)
def test_shell_honours_marker_forms(tmp_path, line):
    f = _write(tmp_path, f"{line}\nleak {LEAK}\n")
    assert _scan_file(f, tmp_path), f"should be exempt: {line!r}"


@pytest.mark.parametrize("line", NOT_EXEMPT)
def test_shell_rejects_prose_and_markdown_structure(tmp_path, line):
    """Each of these was a working opt-out at some point in this rule's life."""
    f = _write(tmp_path, f"{line}\nleak {LEAK}\n")
    assert not _scan_file(f, tmp_path), f"should NOT be exempt: {line!r}"


def test_shell_ignores_marker_below_the_window(tmp_path):
    body = "\n".join(["filler"] * 40 + ["# path-privacy: skip-file", f"leak {LEAK}"])
    f = _write(tmp_path, body + "\n")
    assert not _scan_file(f, tmp_path)


# --- the two engines must accept the same language --------------------------


def test_shell_and_python_agree(tmp_path):
    """The Python copy in tests.py is deliberate; this is what makes it safe.

    Divergence here is not cosmetic. The shell side gates commits and the Python
    side gates the whole-tree audit, so any string they disagree about is a file
    one of them exempts and the other does not.
    """
    corpus = EXEMPT + NOT_EXEMPT + [
        "#path-privacy: skip-file",
        "\t# path-privacy: skip-file",
        "-- path-privacy: skip-file",
        "; path-privacy: skip-file",
        "> path-privacy: skip-file",
        "- path-privacy: skip-file",
        "**path-privacy: skip-file**",
        "--- path-privacy: skip-file",
        "path-privacy: ignore",
        "nothing to see here",
    ]
    disagreements = []
    for line in corpus:
        f = _write(tmp_path, f"{line}\nleak {LEAK}\n", name="agree.md")
        shell_exempt = _scan_file(f, tmp_path)
        python_exempt = bool(_SKIP_MARKER.match(line))
        if shell_exempt != python_exempt:
            disagreements.append((line, shell_exempt, python_exempt))
    assert not disagreements, f"shell/python disagree on: {disagreements}"


# --- degradation, which is where the security properties actually live ------


def _copy_without_lib(tmp_path: Path, *scripts: Path, broken: bool = False) -> Path:
    """A script directory whose library is absent, or present but unusable."""
    d = tmp_path / "nolib"
    d.mkdir(exist_ok=True)
    for s in scripts:
        shutil.copy(s, d / s.name)
    if broken:
        (d / LIB.name).write_text("", encoding="utf-8")   # readable, defines nothing
    return d


@pytest.mark.parametrize("broken", [False, True])
def test_scanner_fails_closed_without_a_usable_library(tmp_path, broken):
    """Absent AND readable-but-broken must both mean 'nothing is exempt'.

    Guarding on `[ -r ]` alone covered only the absent case: a truncated library
    passed the readability test, the fallback never installed, and the resulting
    undefined function exited 127 -- which every call site reads as 'not exempt',
    i.e. fails open in the one place that must not.
    """
    d = _copy_without_lib(tmp_path, SCANNER, broken=broken)
    f = _write(tmp_path, f"# path-privacy: skip-file\nleak {LEAK}\n")
    r = subprocess.run(
        [str(d / SCANNER.name), "--against-root", str(tmp_path), "-f", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1, "a marked file must still be scanned"
    assert "opt-outs are OFF" in r.stderr


@pytest.mark.parametrize("broken", [False, True])
def test_scrub_aborts_rather_than_rewriting_without_a_usable_library(tmp_path, broken):
    """The scrub REWRITES files, so failing closed would scrub what the marker protects."""
    d = _copy_without_lib(tmp_path, SCRUB, broken=broken)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"suggestions":[{"match":"/Users/realpersonname/","suggest":"<home>/"}]}\n')
    target = _write(tmp_path, f"# path-privacy: skip-file\nkeep {LEAK}\n", name="marked.md")
    before = target.read_text()
    r = subprocess.run(
        [str(d / SCRUB.name), "--against-root", str(tmp_path), "-d", str(tmp_path),
         "--config", str(cfg), "--apply"],
        capture_output=True, text=True,
    )
    assert r.returncode == 2, f"expected abort, got {r.returncode}: {r.stderr}"
    assert target.read_text() == before, "a marker-protected file was rewritten"


def test_scrub_help_works_without_the_library(tmp_path):
    """`--help` must not be refused over a dependency printing usage never uses."""
    d = _copy_without_lib(tmp_path, SCRUB)
    r = subprocess.run([str(d / SCRUB.name), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "scrub-paths.sh" in r.stdout


# --- emitted text must not hand the reader a working opt-out ----------------


@pytest.mark.parametrize("script", [SCANNER, SCRUB])
def test_help_output_carries_no_marker_line(script):
    """Redirect `--help` into a file and that file would be silently exempt.

    `usage` also runs on any unknown argument, so this needed no deliberate act.
    """
    r = subprocess.run([str(script), "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    offenders = [ln for ln in r.stdout.splitlines() if _SKIP_MARKER.match(ln)]
    assert not offenders, f"{script.name} --help emits a marker: {offenders}"


# --- the deliberate asymmetry for commit messages ---------------------------


def test_commit_message_cannot_exempt_itself(tmp_path):
    """`--text` without --allow-skip-file is the commit-msg path; it must ignore markers."""
    r = subprocess.run(
        [str(SCANNER), "--against-root", str(tmp_path), "--text",
         f"# path-privacy: skip-file\nfix {LEAK}"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1


def test_write_payload_honours_a_marker_but_not_a_mention(tmp_path):
    """The PreToolUse path passes --allow-skip-file, since the string IS a file."""
    marked = subprocess.run(
        [str(SCANNER), "--against-root", str(tmp_path), "--allow-skip-file", "--text",
         f"# path-privacy: skip-file\nleak {LEAK}"],
        capture_output=True, text=True,
    )
    mentioned = subprocess.run(
        [str(SCANNER), "--against-root", str(tmp_path), "--allow-skip-file", "--text",
         f"Opt out with `path-privacy: skip-file`.\nleak {LEAK}"],
        capture_output=True, text=True,
    )
    assert marked.returncode == 0
    assert mentioned.returncode == 1


# --- the privacy property of the tool's own diagnostics ---------------------


def test_broken_library_does_not_leak_an_absolute_path_into_diagnostics(tmp_path):
    """Bash's own 'command not found' quotes $0, an absolute path under the plugin root.

    The PreToolUse hook captures the scanner with 2>&1 and re-emits it to the
    user, so an unusable library made the privacy tool print a home path while
    reporting that it could not check for home paths.
    """
    d = _copy_without_lib(tmp_path, SCANNER, broken=True)
    f = _write(tmp_path, f"leak {LEAK}\n")
    r = subprocess.run(
        [str(d / SCANNER.name), "--against-root", str(tmp_path), "-f", str(f)],
        capture_output=True, text=True,
    )
    assert "command not found" not in r.stderr
    assert not re.search(r"(?:/Users|/home)/[^/\s]+/", r.stderr.replace(str(tmp_path), "")), \
        f"diagnostics leaked a path: {r.stderr}"
