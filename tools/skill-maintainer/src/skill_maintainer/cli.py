"""CLI entry point for skill-maintain."""

import sys


COMMANDS = {
    "validate": "skill_maintainer.validate",
    "quality": "skill_maintainer.quality",
    "freshness": "skill_maintainer.freshness",
    "measure": "skill_maintainer.measure",
    "upstream": "skill_maintainer.upstream",
    "sources": "skill_maintainer.sources",
    "test": "skill_maintainer.tests",
    "log": "skill_maintainer.log",
    "lint": "skill_maintainer.lint",
    "init": None,  # handled inline
}

HELP = """\
skill-maintain: maintenance tooling for Agent Skills repos

Usage: skill-maintain <command> [options]

Commands:
  init        Initialize .skill-maintainer/ config in the current directory
  validate    Validate skills against Agent Skills spec + best practices
  quality     Unified quality report (validation, budget, freshness, description)
  freshness   Check last_verified staleness
  measure     Token budget measurement
  test        Red/green test suite (skills, plugins, repo hygiene)
  upstream    Check for upstream doc changes (llms-full.txt)
  sources     Pull tracked git repos and detect changes
  log         Query the append-only changes log
  lint        Wiki sanity: orphan detection in docs/analysis/, count drift across READMEs

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
"""


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
        from pathlib import Path

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
