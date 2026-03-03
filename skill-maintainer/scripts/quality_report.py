#!/usr/bin/env python3
"""
Unified quality report for all skills in the repo.

Walks all **/SKILL.md files, reports validation status, token budget,
last_verified age, and description quality. No config file needed.

Usage:
    uv run python skill-maintainer/scripts/quality_report.py
    uv run python skill-maintainer/scripts/quality_report.py --dir /path/to/skills
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import orjson

from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

from shared import (
    CHANGES_LOG,
    STALE_DAYS,
    TOKEN_BUDGET_CRITICAL,
    TOKEN_BUDGET_WARN,
    check_description_quality,
    discover_skills,
    measure_tokens,
)


def analyze_skill(skill_dir: Path) -> dict:
    """Analyze a single skill directory."""
    skill_md = find_skill_md(skill_dir)
    result = {
        "name": skill_dir.name,
        "path": str(skill_dir),
        "valid": False,
        "errors": [],
        "tokens": 0,
        "budget_status": "OK",
        "last_verified": None,
        "days_ago": None,
        "desc_issues": [],
    }

    if skill_md is None:
        result["errors"] = ["SKILL.md not found"]
        return result

    # Validation
    errors = validate(skill_dir)
    result["valid"] = len(errors) == 0
    result["errors"] = errors

    # Token budget
    tokens = measure_tokens(skill_dir)
    result["tokens"] = tokens
    if tokens > TOKEN_BUDGET_CRITICAL:
        result["budget_status"] = "CRITICAL"
    elif tokens > TOKEN_BUDGET_WARN:
        result["budget_status"] = "OVER"

    # Parse frontmatter
    try:
        content = skill_md.read_text()
        metadata, _ = parse_frontmatter(content)
    except Exception:
        return result

    # last_verified
    meta = metadata.get("metadata", {})
    if isinstance(meta, dict):
        lv = meta.get("last_verified")
        if lv:
            result["last_verified"] = str(lv)
            try:
                lv_date = date.fromisoformat(str(lv))
                result["days_ago"] = (date.today() - lv_date).days
            except ValueError:
                pass

    # Description quality
    description = metadata.get("description", "")
    result["desc_issues"] = check_description_quality(description)
    result["name"] = metadata.get("name", skill_dir.name)

    return result


def append_to_log(results: list[dict]) -> None:
    """Append quality report event to changes.jsonl."""
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "type": "quality_report",
        "date": date.today().isoformat(),
        "skills": len(results),
        "valid": sum(1 for r in results if r["valid"]),
        "over_budget": sum(1 for r in results if r["budget_status"] != "OK"),
        "stale": sum(1 for r in results if r["days_ago"] is not None and r["days_ago"] > STALE_DAYS),
    }
    with open(CHANGES_LOG, "ab") as f:
        f.write(orjson.dumps(event) + b"\n")


def main():
    parser = argparse.ArgumentParser(description="Quality report for all skills.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    args = parser.parse_args()

    skills = discover_skills(args.dir)
    if not skills:
        print("No SKILL.md files found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for skill_dir in skills:
        result = analyze_skill(skill_dir)
        results.append(result)

    # Table header
    print(f"{'Skill':<25} {'Valid':>5} {'Tokens':>7} {'Budget':>8} {'Verified':>12} {'Age':>5}  Desc Issues")
    print("-" * 95)

    for r in results:
        valid_str = "OK" if r["valid"] else "FAIL"
        age_str = str(r["days_ago"]) + "d" if r["days_ago"] is not None else "n/a"
        verified_str = r["last_verified"] or "n/a"
        desc_str = ", ".join(r["desc_issues"]) if r["desc_issues"] else "OK"

        print(
            f"{r['name']:<25} {valid_str:>5} {r['tokens']:>7,} {r['budget_status']:>8} "
            f"{verified_str:>12} {age_str:>5}  {desc_str}"
        )

    # Summary
    total = len(results)
    valid = sum(1 for r in results if r["valid"])
    over = sum(1 for r in results if r["budget_status"] != "OK")
    stale = sum(1 for r in results if r["days_ago"] is not None and r["days_ago"] > STALE_DAYS)
    print()
    print(f"{valid}/{total} valid, {over} over budget, {stale} stale (>{STALE_DAYS}d)")

    if not args.no_log:
        append_to_log(results)

    # Exit 1 if any invalid
    sys.exit(0 if valid == total else 1)


if __name__ == "__main__":
    main()
