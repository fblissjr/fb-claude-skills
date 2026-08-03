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

from skill_maintainer.tests import _SKIP_MARKER, _has_skip_marker

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


FENCED = [
    "```\n# path-privacy: skip-file\n```",
    "```sh\n# path-privacy: skip-file -- regex source\n```",
    "~~~\n<!-- path-privacy: skip-file -->\n~~~",
    "Write it like this:\n\n```\n# path-privacy: skip-file\n```\n",
    # A fence closes only with the character that opened it. The first fence
    # pass toggled on ``` OR ~~~ interchangeably, so the ~~~ line below flipped
    # the state OFF and the marker -- inside a code block to any markdown
    # renderer and any human -- was live to the scanner.
    "```\n~~~\n# path-privacy: skip-file\n```",
    "~~~\n```\n<!-- path-privacy: skip-file -->\n~~~",
    # ...and only with a run at least as long: a ```` block demonstrating a
    # ``` example must not be closed by the example.
    "````\n```\n# path-privacy: skip-file\n```\n````",
    # An unclosed fence swallows to EOF -- fail-closed, like markdown itself.
    "```\n# path-privacy: skip-file",
    # A closing fence takes no info string, so ```sh cannot close; the marker
    # after it is still inside the block.
    "```\nexample\n``` sh\n# path-privacy: skip-file",
]


@pytest.mark.parametrize("block", FENCED)
def test_fenced_example_does_not_exempt(tmp_path, block):
    """A doc DEMONSTRATING the marker must not thereby switch the audit off.

    This is the case that survived the anchoring release: a fenced block is not
    indented, so the example line is byte-identical to a real marker. No line
    pattern separates them; fence state is carried between lines, so it takes a
    scan. The claim that no pattern could do it was simply wrong.
    """
    f = _write(tmp_path, f"{block}\nleak {LEAK}\n")
    assert not _scan_file(f, tmp_path), f"fenced example exempted the file: {block!r}"


def test_marker_after_a_closed_fence_still_exempts(tmp_path):
    """Fence tracking must not swallow a real marker that follows an example."""
    f = _write(tmp_path, f"```\nexample\n```\n# path-privacy: skip-file\nleak {LEAK}\n")
    assert _scan_file(f, tmp_path)


def test_marker_after_a_longer_closing_run_still_exempts(tmp_path):
    """A closing run LONGER than the opener still closes, per markdown."""
    f = _write(tmp_path, f"```\nexample\n`````\n# path-privacy: skip-file\nleak {LEAK}\n")
    assert _scan_file(f, tmp_path)


def test_closing_fence_with_trailing_blanks_still_closes(tmp_path):
    """Trailing spaces on a closing fence are blanks, not an info string."""
    f = _write(tmp_path, f"```\nexample\n```   \n# path-privacy: skip-file\nleak {LEAK}\n")
    assert _scan_file(f, tmp_path)


# Unicode blanks markdown does not treat as indentation. The point is not which
# way these classify -- a NBSP-prefixed ``` is a paragraph, not a fence, so the
# marker after it is live and the file exempt, same as any unfenced quotation.
# The point is that BOTH engines say so: the fence indent used to be [[:space:]]
# under LC_ALL=C on the shell side (ASCII-only) and \s on the Python side
# (Unicode), so this exact file was exempt to the commit gate while
# _has_skip_marker returned False -- which kept check_marker_denylist, the
# loud-recurrence backstop, silent about a file the gate was waving through.
UNICODE_BLANKS = ["\u00a0", "\u2028", "\u3000"]  # NBSP, LINE SEP, IDEOGRAPHIC SPACE


@pytest.mark.parametrize("ws", UNICODE_BLANKS)
def test_unicode_blank_before_a_fence_is_not_a_fence_in_either_engine(tmp_path, ws):
    body = f"{ws}```\n# path-privacy: skip-file\n{ws}```\nleak {LEAK}\n"
    f = _write(tmp_path, body)
    shell_exempt = _scan_file(f, tmp_path)
    python_exempt = _has_skip_marker(body)
    assert shell_exempt == python_exempt, (
        f"engines disagree for {ws!r}: shell={shell_exempt} python={python_exempt}"
    )
    assert python_exempt, "not a fence, so the leading marker is live"


def _lib_head_has_marker(path: Path) -> bool:
    """The library function itself, not the scanner: pp_head_has_skip_marker.

    The scanner short-circuits NUL-bearing files into its binary detour
    ("not scanned, check by hand", exit 0) before any marker logic runs, so
    scanner-level tests cannot see the fence tracker's byte handling. The
    PreToolUse hook and the scrub call this function directly, so its
    behaviour is load-bearing on its own.
    """
    r = subprocess.run(
        ["bash", "-c", f'. "{LIB}"; pp_head_has_skip_marker "$1"', "_", str(path)],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def test_nul_byte_cannot_forge_a_closing_fence(tmp_path):
    """BSD awk ends its record at NUL, so a ``` line with a NUL tail read as a
    bare closer to the shell -- closing the fence and exposing the marker --
    while Python saw a non-blank tail and kept the fence open. The split-engine
    class again, through bytes no honestly-authored text file carries. Both
    engines must refuse the forged closer: fence stays open, marker stays
    hidden. (The tr in pp_strip_fenced is what makes the shell side hold.)
    """
    body = "```\n```\x00\n# path-privacy: skip-file\nleak " + LEAK + "\n"
    f = _write(tmp_path, body)
    assert not _lib_head_has_marker(f), "shell treated a NUL-tailed run as a closer"
    assert not _has_skip_marker(body), "python treated a NUL-tailed run as a closer"


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
    # Whole bodies, not bare lines: the two engines must agree about fenced
    # blocks and the 30-line window too, and neither is a property of one line.
    bodies = [f"{line}\nleak {LEAK}\n" for line in corpus]
    bodies += [f"{block}\nleak {LEAK}\n" for block in FENCED]
    bodies += [
        "```\nexample\n```\n# path-privacy: skip-file\nleak " + LEAK + "\n",
        "\n".join(["filler"] * 40 + ["# path-privacy: skip-file", f"leak {LEAK}"]),
    ]
    # The divergence class: fence-shaped lines only one engine used to see.
    bodies += [
        f"{ws}```\n# path-privacy: skip-file\n{ws}```\nleak {LEAK}\n"
        for ws in UNICODE_BLANKS
    ]
    # NUL bodies are deliberately absent here: the scanner routes NUL-bearing
    # files into its binary detour before marker logic runs, so scanner-vs-
    # audit agreement legitimately does not hold for them. The library-level
    # agreement is pinned by test_nul_byte_cannot_forge_a_closing_fence.
    disagreements = []
    for body in bodies:
        f = _write(tmp_path, body, name="agree.md")
        shell_exempt = _scan_file(f, tmp_path)
        python_exempt = _has_skip_marker(body)
        if shell_exempt != python_exempt:
            disagreements.append((body[:60], shell_exempt, python_exempt))
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
