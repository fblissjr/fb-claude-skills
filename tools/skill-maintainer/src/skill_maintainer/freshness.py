"""Lightweight staleness check for skill freshness."""

import sys
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter

from skill_maintainer.shared import STALE_DAYS, discover_skills, get_review_interval
from skill_maintainer.shared import get_last_verified as _get_last_verified


def _read_last_verified(skill_dir: Path) -> tuple[str | None, int | None, int | None]:
    """Read last_verified and the skill's own review interval from frontmatter."""
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return None, None, None

    try:
        content = skill_md.read_text()
        metadata, _ = parse_frontmatter(content)
    except Exception:
        return None, None, None

    lv_str, days_ago = _get_last_verified(metadata)
    return lv_str, days_ago, get_review_interval(metadata)


def check_skill(skill_dir: Path, threshold_days: int | None = None) -> dict:
    """Check freshness of a single skill."""
    name = skill_dir.name
    lv_str, days_ago, interval = _read_last_verified(skill_dir)
    # An explicit --threshold is an override; otherwise honour the skill's own
    # declared interval, falling back to the global default.
    if threshold_days is None:
        threshold_days = interval if interval is not None else STALE_DAYS

    if lv_str is None:
        return {
            "name": name,
            "is_stale": True,
            "last_verified": None,
            "days_ago": None,
            "message": f"{name}: no last_verified date in metadata",
        }

    if days_ago is None:
        return {
            "name": name,
            "is_stale": True,
            "last_verified": lv_str,
            "days_ago": None,
            "message": f"{name}: invalid last_verified date: {lv_str}",
        }

    is_stale = days_ago > threshold_days

    message = None
    if is_stale:
        message = f"{name}: last verified {days_ago} days ago ({lv_str}). Consider reviewing."

    return {
        "name": name,
        "is_stale": is_stale,
        "last_verified": lv_str,
        "days_ago": days_ago,
        "message": message,
    }


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Check freshness of skills.")
    parser.add_argument("skill", nargs="?", default=None, help="Skill directory name to check")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search")
    parser.add_argument("--threshold", type=int, default=None,
                        help="Override every skill's review interval (default: per-skill, else %(default)s)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output stale skills")
    parsed = parser.parse_args(args)

    skills = discover_skills(parsed.dir)

    if parsed.skill:
        skills = [s for s in skills if s.name == parsed.skill]
        if not skills:
            print(f"Skill '{parsed.skill}' not found", file=sys.stderr)
            sys.exit(1)

    if not parsed.quiet:
        print(f"Checking freshness of {len(skills)} skills...", file=sys.stderr, flush=True)

    for skill_dir in skills:
        result = check_skill(skill_dir, parsed.threshold)

        if result["is_stale"]:
            if result.get("message"):
                print(result["message"], file=sys.stderr)
        elif not parsed.quiet:
            print(f"{result['name']}: OK (verified {result['days_ago']} days ago)", file=sys.stderr)

    sys.exit(0)
