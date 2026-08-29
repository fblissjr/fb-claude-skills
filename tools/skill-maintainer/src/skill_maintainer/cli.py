"""CLI entry point for skill-maintain."""

import sys
import tomllib
from pathlib import Path


COMMANDS = {
    "validate": "skill_maintainer.validate",
    "quality": "skill_maintainer.quality",
    "measure": "skill_maintainer.measure",
    "upstream": "skill_maintainer.upstream",
    "sources": "skill_maintainer.sources",
    "test": "skill_maintainer.tests",
    "log": "skill_maintainer.log",
    "lint": "skill_maintainer.lint",
    "tune": "skill_maintainer.tune",
    "init": None,  # handled inline
}

HELP = """\
skill-maintain: maintenance tooling for Agent Skills repos

Usage: skill-maintain <command> [options]

Commands:
  init        Initialize .skill-maintainer/ config in the current directory
  validate    Validate skills against Agent Skills spec + best practices
  quality     Unified quality report (validation, budget, description)
  measure     Token budget measurement
  test        Red/green test suite (skills, plugins, repo hygiene)
  upstream    Check for upstream doc changes (llms-full.txt)
  sources     Pull tracked git repos and detect changes
  log         Query the append-only changes log
  lint        Wiki sanity: orphan detection in docs/analysis/, count drift across READMEs
  tune        How plugins actually behave: hook emission rates per project, skill
              invocation counts, and drift in files plugins wrote into repos

All commands accept --dir <path> to target a different directory (default: .)

Examples:
  skill-maintain init
  skill-maintain init --force-hook       # overwrite existing .git/hooks/pre-commit (preserves prior as .local)
  skill-maintain quality
  skill-maintain test --verbose
  skill-maintain validate --all
  skill-maintain upstream
  skill-maintain sources --no-pull
  skill-maintain log --days 7
  skill-maintain lint
  skill-maintain tune --days 30
  skill-maintain tune --project heylook --repo ~/some/repo   # path-privacy: ignore
"""


def source_version(root: Path) -> str | None:
    """The version declared by a vendored copy of this tool, if one is here.

    Returns None outside a repo that vendors it, and on any parse failure:
    this runs ahead of every command and must never be why one fails.
    """
    pyproject = Path(root) / "tools" / "skill-maintainer" / "pyproject.toml"
    try:
        with open(pyproject, "rb") as fh:
            return tomllib.load(fh)["project"]["version"]
    except (OSError, KeyError, ValueError):
        return None


def staleness_warning(root: Path, running: str | None = None) -> str | None:
    """Warn when the running build is not the source tree it is inspecting.

    There are two installs called `skill-maintain`: the `uv tool install` on
    PATH, and the editable workspace install that `uv run` resolves. The tool
    install's receipt points at this directory, so it reads as tracking the
    source while being pinned at whatever version it was built from. They
    diverge in silence, and the skills shipped from this repo instruct the
    bare command -- so a stale build is what actually runs the maintenance
    workflow and reports its results as verification.
    """
    declared = source_version(root)
    if declared is None:
        return None
    if running is None:
        from importlib.metadata import PackageNotFoundError, version
        try:
            running = version("skill-maintainer")
        except PackageNotFoundError:
            return None
    if running == declared:
        return None
    return (
        f"warning: running skill-maintain {running}, but the source here "
        f"declares {declared}. These are two different installs; results "
        f"below come from {running}. Refresh with: "
        f"uv tool install --reinstall ./tools/skill-maintainer"
    )


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        sys.exit(0)

    command = sys.argv[1]

    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(1)

    # Strip the command name so subcommand argparse sees the right args
    sys.argv = [f"skill-maintain {command}"] + sys.argv[2:]

    if command == "init":

        from skill_maintainer.config import init_config
        from skill_maintainer.scaffold import install_pre_commit_hook

        root = Path(".")
        force_hook = "--force-hook" in sys.argv
        # Check for --dir
        if "--dir" in sys.argv:
            idx = sys.argv.index("--dir")
            if idx + 1 < len(sys.argv):
                root = Path(sys.argv[idx + 1])

        cfg_path = init_config(root)
        print(f"Initialized {cfg_path}")
        print(f"Edit {cfg_path} to configure upstream URLs and tracked repos.")

        hook_status = install_pre_commit_hook(root, force=force_hook)
        print(f"Pre-commit hook: {hook_status}")
        sys.exit(0)

    warning = staleness_warning(Path("."))
    if warning:
        print(warning, file=sys.stderr)

    # Dynamic import and dispatch
    import importlib

    module = importlib.import_module(COMMANDS[command])
    module.main()
