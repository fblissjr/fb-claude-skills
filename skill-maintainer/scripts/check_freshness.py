#!/usr/bin/env python3
"""
Lightweight staleness check for skill freshness.

Reads last_verified from SKILL.md frontmatter, warns if stale.
No DuckDB dependency.

Usage:
    uv run python skill-maintainer/scripts/check_freshness.py
    uv run python skill-maintainer/scripts/check_freshness.py plugin-toolkit
    uv run python skill-maintainer/scripts/check_freshness.py --threshold 14
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter

DEFAULT_THRESHOLD_DAYS = 30
SKIP_DIRS = {"__pycache__", ".backup", "node_modules", ".git", "coderef", ".venv", "internal"}


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


def get_last_verified(skill_dir: Path) -> str | None:
    """Read last_verified from SKILL.md frontmatter."""
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return None

    try:
        content = skill_md.read_text()
        metadata, _ = parse_frontmatter(content)
    except Exception:
        return None

    meta = metadata.get("metadata", {})
    if isinstance(meta, dict):
        lv = meta.get("last_verified")
        return str(lv) if lv else None
    return None


def check_skill(skill_dir: Path, threshold_days: int) -> dict:
    """Check freshness of a single skill."""
    name = skill_dir.name
    lv = get_last_verified(skill_dir)

    if lv is None:
        return {
            "name": name,
            "is_stale": True,
            "last_verified": None,
            "days_ago": None,
            "message": f"{name}: no last_verified date in metadata",
        }

    try:
        lv_date = date.fromisoformat(lv)
    except ValueError:
        return {
            "name": name,
            "is_stale": True,
            "last_verified": lv,
            "days_ago": None,
            "message": f"{name}: invalid last_verified date: {lv}",
        }

    days_ago = (date.today() - lv_date).days
    is_stale = days_ago > threshold_days

    message = None
    if is_stale:
        message = f"{name}: last verified {days_ago} days ago ({lv}). Consider reviewing."

    return {
        "name": name,
        "is_stale": is_stale,
        "last_verified": lv,
        "days_ago": days_ago,
        "message": message,
    }


def main():
    parser = argparse.ArgumentParser(description="Check freshness of skills.")
    parser.add_argument("skill", nargs="?", default=None, help="Skill directory name to check")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_DAYS, help="Staleness threshold in days")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output stale skills")
    args = parser.parse_args()

    skills = discover_skills(Path("."))

    if args.skill:
        skills = [s for s in skills if s.name == args.skill]
        if not skills:
            print(f"Skill '{args.skill}' not found", file=sys.stderr)
            sys.exit(1)

    for skill_dir in skills:
        result = check_skill(skill_dir, args.threshold)

        if result["is_stale"]:
            if result.get("message"):
                print(result["message"], file=sys.stderr)
        elif not args.quiet:
            print(f"{result['name']}: OK (verified {result['days_ago']} days ago)", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
