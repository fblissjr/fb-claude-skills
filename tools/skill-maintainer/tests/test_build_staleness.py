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

from skill_maintainer.cli import source_version, staleness_warning


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
