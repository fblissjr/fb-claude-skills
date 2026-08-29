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


def resolve_root(argv: list[str]) -> Path:
    """Where to look for a vendored copy of this tool.

    Honours --dir like every other command, then walks up from the working
    directory, so `cd tools && skill-maintain quality` still finds the repo.
    The first version looked only at ./tools/skill-maintainer and so disabled
    itself from any subdirectory without saying so.

    Deliberately NOT the uv tool receipt, which records the tree the binary
    was BUILT from. The question here is whether the build matches the source
    you are presently reading, and that is the working directory.
    """
    def vendors(p: Path) -> bool:
        return (p / "tools" / "skill-maintainer" / "pyproject.toml").exists()

    # --dir names the repo being ACTED ON, which is not necessarily where this
    # tool's source lives -- `init --dir /fresh/repo` targets a repo that
    # vendors nothing. Use it only when it actually holds a vendored copy,
    # then fall back to the tree we are standing in.
    if "--dir" in argv:
        i = argv.index("--dir")
        if i + 1 < len(argv):
            target = Path(argv[i + 1])
            if vendors(target):
                return target
    here = Path(".").resolve()
    for candidate in (here, *here.parents):
        if vendors(candidate):
            return candidate
    return here


def source_version(root: Path) -> str | None:
    """The version declared by a vendored copy of this tool, if one is here.

    Returns None outside a repo that vendors it, and on ANY malformed input.
    This runs ahead of every command, so an escape here takes down the whole
    CLI -- the first version caught only (OSError, KeyError, ValueError),
    which covers unparseable TOML but not a well-formed file whose `project`
    key is a string. A non-string version is also rejected: comparing it
    against the running version can never be equal, so the warning would fire
    on every command and the reinstall it recommends would never clear it.
    """
    pyproject = Path(root) / "tools" / "skill-maintainer" / "pyproject.toml"
    try:
        with open(pyproject, "rb") as fh:
            declared = tomllib.load(fh)["project"]["version"]
    except Exception:
        return None
    return declared if isinstance(declared, str) else None


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

    # Before EVERY command, init included. init is where a stale build does
    # the most damage: install_pre_commit_hook writes the hook template out of
    # the running build, so an old binary scaffolds an outdated hook silently.
    warning = staleness_warning(resolve_root(sys.argv[1:]))
    if warning:
        print(warning, file=sys.stderr)

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

    # Dynamic import and dispatch
    import importlib

    module = importlib.import_module(COMMANDS[command])
    module.main()
