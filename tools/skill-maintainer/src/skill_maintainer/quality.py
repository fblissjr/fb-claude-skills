"""Unified quality report for all skills."""

import sys
from datetime import date
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter
from skill_maintainer.cc_schema import validate_cc as validate

from skill_maintainer.config import append_event
from skill_maintainer.shared import (
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
        "desc_issues": [],
    }

    if skill_md is None:
        result["errors"] = ["SKILL.md not found"]
        return result

    # Validation
    errors = validate(skill_dir)
    result["valid"] = len(errors) == 0
    result["errors"] = errors

    # Token budget (apply thresholds to skill_tokens only, not references)
    token_info = measure_tokens(skill_dir)
    result["tokens"] = token_info["skill_tokens"]
    result["ref_tokens"] = token_info["ref_tokens"]
    result["total_tokens"] = token_info["total"]
    if token_info["skill_tokens"] > TOKEN_BUDGET_CRITICAL:
        result["budget_status"] = "CRITICAL"
    elif token_info["skill_tokens"] > TOKEN_BUDGET_WARN:
        result["budget_status"] = "OVER"

    # Parse frontmatter
    try:
        content = skill_md.read_text()
        metadata, _ = parse_frontmatter(content)
    except Exception:
        return result

    # Description quality
    description = metadata.get("description", "")
    result["desc_issues"] = check_description_quality(
        description,
        model_invocable=not metadata.get("disable-model-invocation", False),
    )
    result["name"] = metadata.get("name", skill_dir.name)

    return result


def _log_event(root: Path, results: list[dict]) -> None:
    """Append quality report event to changes.jsonl."""
    append_event(root, {
        "type": "quality_report",
        "date": date.today().isoformat(),
        "skills": len(results),
        "valid": sum(1 for r in results if r["valid"]),
        "over_budget": sum(1 for r in results if r["budget_status"] != "OK"),
    })


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Quality report for all skills.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search")
    parser.add_argument("--no-log", action="store_true", help="Skip writing to changes.jsonl")
    parsed = parser.parse_args(args)

    skills = discover_skills(parsed.dir)
    if not skills:
        print("No SKILL.md files found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for skill_dir in skills:
        result = analyze_skill(skill_dir)
        results.append(result)

    # Table header
    print(f"{'Skill':<25} {'Valid':>5} {'Skill':>7} {'Refs':>7} {'Budget':>8}  Desc Issues")
    print("-" * 80)

    for r in results:
        valid_str = "OK" if r["valid"] else "FAIL"
        desc_str = ", ".join(r["desc_issues"]) if r["desc_issues"] else "OK"
        ref_tokens = r.get("ref_tokens", 0)

        print(
            f"{r['name']:<25} {valid_str:>5} {r['tokens']:>7,} {ref_tokens:>7,} {r['budget_status']:>8}"
            f"  {desc_str}"
        )

    # Summary
    total = len(results)
    valid = sum(1 for r in results if r["valid"])
    over = sum(1 for r in results if r["budget_status"] != "OK")
    print()
    print(f"{valid}/{total} valid, {over} over budget")

    if not parsed.no_log:
        _log_event(parsed.dir, results)

    # Exit 1 if any invalid
    sys.exit(0 if valid == total else 1)
