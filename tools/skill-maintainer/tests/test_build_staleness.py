"""The running build can be older than the source tree it is inspecting.

`skill-maintain` on PATH is a `uv tool install` -- a SEPARATE copy from the
editable workspace install that `uv run skill-maintain` resolves. Both are
called skill-maintain, the tool install's receipt points at
`tools/skill-maintainer` so it reads as tracking the source, and they diverge
silently. Observed 2026-08-29 at v0.18.1 against a 0.34.0 source, still
offering a subcommand deleted that day.

That is not a cosmetic mismatch: the skills shipped from this repo instruct the
bare command, so a stale build is what actually executes the maintenance
workflow, and its results get reported as the repo's verification. Nothing was
watching, and nothing would have: every gate the stale build ran passed.

Each test here pins a case where the check must speak or must stay quiet.

Run: uv run pytest tools/skill-maintainer/tests/test_build_staleness.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from skill_maintainer.cli import resolve_root, source_version, staleness_warning


def _repo(tmp_path: Path, version: str) -> Path:
    pkg = tmp_path / "tools" / "skill-maintainer"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        f'[project]\nname = "skill-maintainer"\nversion = "{version}"\n'
    )
    return tmp_path


def test_reads_the_version_out_of_the_source_tree(tmp_path):
    assert source_version(_repo(tmp_path, "0.34.0")) == "0.34.0"


def test_silent_when_the_build_matches_the_source(tmp_path):
    # A check that speaks on every run is wallpaper. This one must be
    # invisible in the normal case, which is every run in a synced repo.
    assert staleness_warning(_repo(tmp_path, "0.34.0"), running="0.34.0") is None


def test_speaks_when_the_build_is_behind(tmp_path):
    warning = staleness_warning(_repo(tmp_path, "0.34.0"), running="0.18.1")
    assert warning is not None
    # It has to name both numbers, or the reader cannot tell which is which.
    assert "0.18.1" in warning and "0.34.0" in warning
    # And name the fix, since the whole failure mode is not knowing there are
    # two installs.
    assert "uv tool install" in warning


def test_speaks_when_the_build_is_ahead(tmp_path):
    """Ahead is rarer but is the same class -- an uncommitted local downgrade,
    or a tool install from a different checkout. Either way the build is not
    the source, which is the thing worth saying."""
    assert staleness_warning(_repo(tmp_path, "0.30.0"), running="0.34.0") is not None


def test_silent_outside_a_repo_that_vendors_this_tool(tmp_path):
    """The CLI's whole distribution story is running in OTHER repos, which have
    no tools/skill-maintainer and against which it has nothing to compare.
    A warning there would fire on every legitimate run."""
    assert source_version(tmp_path) is None
    assert staleness_warning(tmp_path, running="0.18.1") is None


def test_a_malformed_source_pyproject_is_silent_not_fatal(tmp_path):
    """This runs before every command. It must never be the reason a command
    fails -- it is a diagnostic about the diagnostic."""
    pkg = tmp_path / "tools" / "skill-maintainer"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text("this is not: [valid toml")
    assert source_version(tmp_path) is None
    assert staleness_warning(tmp_path, running="0.18.1") is None


def test_the_check_is_actually_wired_into_dispatch(tmp_path, monkeypatch, capsys):
    """The unit tests above call staleness_warning directly, so they all passed
    while `main()` raised UnboundLocalError on every command -- an inline
    `from pathlib import Path` in the init branch made the module-level name
    function-local for the whole of main(). A check nothing routes to is not a
    check, and testing the helper is not testing the wiring."""
    import skill_maintainer.cli as cli

    monkeypatch.setattr(sys, "argv", ["skill-maintain", "lint"])
    monkeypatch.chdir(tmp_path)
    called = {}
    monkeypatch.setattr(
        "skill_maintainer.lint.main", lambda: called.setdefault("ran", True)
    )
    monkeypatch.setattr(cli, "staleness_warning", lambda root: "STALE-BUILD-MARKER")

    cli.main()

    assert called.get("ran"), "dispatch never reached the subcommand"
    assert "STALE-BUILD-MARKER" in capsys.readouterr().err


# --------------------------------------------------------------------------
# the guard must never be the reason a command fails
#
# The first version caught (OSError, KeyError, ValueError), which covers a
# malformed TOML file but not a well-formed one whose shape is wrong. Since
# the call sits ahead of dispatch, an escape here takes down every command.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("body,label", [
    ('project = "not-a-table"\n', "project key is a string"),
    ("project = []\n", "project key is a list"),
    ("[project]\nname = 'x'\n", "no version key"),
    ("this is not: [valid toml", "unparseable"),
])
def test_a_wrongly_shaped_pyproject_is_silent_not_fatal(tmp_path, body, label):
    pkg = tmp_path / "tools" / "skill-maintainer"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(body)
    assert source_version(tmp_path) is None, label
    assert staleness_warning(tmp_path, running="0.18.1") is None, label


@pytest.mark.parametrize("version", [1, 1.5, True, ["0.35.0"]])
def test_a_non_string_version_does_not_become_permanent_wallpaper(tmp_path, version):
    """`"0.35.0" == 1` is always False, so the warning fires on every command
    and the reinstall it recommends never clears it. A check that cannot be
    satisfied is worse than no check: people learn to scroll past the channel."""
    pkg = tmp_path / "tools" / "skill-maintainer"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text(
        f"[project]\nname = 'x'\nversion = {version!r}\n".replace("'", '"')
    )
    assert staleness_warning(tmp_path, running="0.35.0") is None


# --------------------------------------------------------------------------
# root resolution
# --------------------------------------------------------------------------


def test_finds_the_source_from_a_subdirectory(tmp_path, monkeypatch):
    """`cd tools && skill-maintain quality` must not silently no-op. The first
    version looked only at `./tools/skill-maintainer/pyproject.toml`, so every
    invocation from anywhere but the repo root disabled the check without
    saying so."""
    root = _repo(tmp_path, "0.36.0")
    sub = root / "skills" / "deep" / "nested"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert staleness_warning(resolve_root([]), running="0.35.0") is not None


def test_honours_dir_like_every_other_command(tmp_path, monkeypatch):
    root = _repo(tmp_path, "0.36.0")
    monkeypatch.chdir(tmp_path.parent)
    assert resolve_root(["--dir", str(root)]) == root


def test_upward_walk_stops_rather_than_escaping_to_an_unrelated_repo(tmp_path, monkeypatch):
    """A directory with no vendored copy anywhere above it must resolve to
    nothing, not to whatever tools/skill-maintainer exists further up the
    filesystem."""
    lonely = tmp_path / "somewhere" / "else"
    lonely.mkdir(parents=True)
    monkeypatch.chdir(lonely)
    assert source_version(resolve_root([])) is None


# --------------------------------------------------------------------------
# init is not exempt
# --------------------------------------------------------------------------


def test_init_runs_the_check_too(tmp_path, monkeypatch, capsys):
    """init was exempt because the check sat below its sys.exit(0). That is the
    command where a stale build does the most damage: install_pre_commit_hook
    writes the hook template out of the RUNNING build, so a stale binary
    scaffolds an outdated hook into someone's repo and says nothing."""
    import skill_maintainer.cli as cli

    monkeypatch.setattr(sys, "argv", ["skill-maintain", "init", "--dir", str(tmp_path)])
    monkeypatch.setattr(cli, "staleness_warning", lambda root: "STALE-BUILD-MARKER")
    monkeypatch.setattr("skill_maintainer.config.init_config", lambda root: tmp_path / "cfg")
    monkeypatch.setattr(
        "skill_maintainer.scaffold.install_pre_commit_hook", lambda root, force=False: "ok"
    )
    with pytest.raises(SystemExit):
        cli.main()
    assert "STALE-BUILD-MARKER" in capsys.readouterr().err


def test_the_real_check_reaches_stderr_through_dispatch(tmp_path, monkeypatch, capsys):
    """The other wiring test stubs staleness_warning, so it proves the call site
    exists but never that the real function computes a usable root -- which is
    exactly where the CWD bug lived. This one leaves it unpatched."""
    import skill_maintainer.cli as cli

    _repo(tmp_path, "99.0.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["skill-maintain", "lint"])
    monkeypatch.setattr("skill_maintainer.lint.main", lambda: None)
    cli.main()
    err = capsys.readouterr().err
    assert "99.0.0" in err and "uv tool install" in err


def test_dir_pointing_at_a_repo_that_vendors_nothing_falls_back_to_cwd(tmp_path, monkeypatch):
    """`init --dir /fresh/repo` targets a repo that vendors nothing, so taking
    --dir as the source root disabled the check for exactly the command where
    a stale build does the most damage. Caught by running the binary; the
    unit test above missed it because it stubs staleness_warning and so never
    exercises resolve_root -- the same blind spot review found in the first
    wiring test, reproduced one test later."""
    source = _repo(tmp_path / "src", "0.36.0")
    target = tmp_path / "fresh"
    target.mkdir()
    monkeypatch.chdir(source)
    assert resolve_root(["--dir", str(target)]) == source
    assert staleness_warning(resolve_root(["--dir", str(target)]), running="0.35.0") is not None


def test_dir_is_used_when_it_does_vendor_a_copy(tmp_path, monkeypatch):
    vendored = _repo(tmp_path / "other", "0.40.0")
    monkeypatch.chdir(tmp_path)
    assert resolve_root(["--dir", str(vendored)]) == vendored
