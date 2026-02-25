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

TOKEN_BUDGET_WARN = 4000
TOKEN_BUDGET_CRITICAL = 8000
STALE_DAYS = 30
CHANGES_LOG = Path("skill-maintainer/state/changes.jsonl")

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


def measure_tokens(skill_dir: Path) -> int:
    """Estimate total tokens for all text files in a skill directory."""
    total_chars = 0
    skip = {"__pycache__", ".backup", "node_modules", "state"}
    for f in skill_dir.rglob("*"):
        if f.is_dir():
            continue
        if f.name.startswith("."):
            continue
        if any(s in f.parts for s in skip):
            continue
        if f.suffix in (".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml"):
            try:
                total_chars += len(f.read_text())
            except (OSError, UnicodeDecodeError):
                pass
    return total_chars // 4


def check_description_quality(description: str) -> list[str]:
    """Check description for WHAT + WHEN pattern."""
    issues = []
    if not description:
        issues.append("no description")
        return issues

    desc_lower = description.lower()
    has_what = any(w in desc_lower for w in [
        "use when", "use for", "handles", "manages", "creates",
        "generates", "monitors", "validates", "analyzes", "design",
    ])
    has_when = any(w in desc_lower for w in [
        "use when", "when user", "when the", "if user",
        "trigger", "mention", "says",
    ])

    if not has_what:
        issues.append("missing WHAT verb")
    if not has_when:
        issues.append("missing WHEN trigger")
    if "<" in description or ">" in description:
        issues.append("angle brackets in description")

    return issues


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
