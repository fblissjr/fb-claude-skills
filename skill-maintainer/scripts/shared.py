"""Shared constants and utilities for skill-maintainer scripts."""

from pathlib import Path

SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal"}
HASHES_FILE = Path("skill-maintainer/state/upstream_hashes.json")
CHANGES_LOG = Path("skill-maintainer/state/changes.jsonl")
TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000
STALE_DAYS = 30


def discover_skills(root: Path) -> list[Path]:
    """Find all SKILL.md files, return their parent directories."""
    results = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        if any(skip in skill_md.parts for skip in SKIP_DIRS):
            continue
        if ".backup" in str(skill_md):
            continue
        results.append(skill_md.parent)
    return results


def discover_plugins(root: Path) -> list[Path]:
    """Find all plugin directories (have .claude-plugin/plugin.json), skip coderef/."""
    results = []
    for pj in sorted(root.rglob(".claude-plugin/plugin.json")):
        if any(skip in pj.parts for skip in SKIP_DIRS):
            continue
        # plugin dir is parent of .claude-plugin/
        plugin_dir = pj.parent.parent
        # skip the root marketplace (root .claude-plugin/ is not a plugin)
        if plugin_dir == root:
            continue
        results.append(plugin_dir)
    return results
