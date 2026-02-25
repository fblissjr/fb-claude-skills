#!/usr/bin/env python3
"""
Validate a skill against the Agent Skills spec and best practices.

Wraps the skills-ref validator and adds additional checks.
No DuckDB dependency.

Usage:
    uv run python skill-maintainer/scripts/validate_skill.py ./plugin-toolkit/skills/plugin-toolkit
    uv run python skill-maintainer/scripts/validate_skill.py --all
"""

import argparse
import sys
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

SKILL_MD_MAX_LINES = 500
SKILL_MD_MAX_WORDS = 5000

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


def check_best_practices(skill_path: Path) -> list[str]:
    """Run additional best-practice checks beyond skills-ref validation."""
    warnings = []
    skill_md = find_skill_md(skill_path)

    if skill_md is None:
        return ["SKILL.md not found"]

    content = skill_md.read_text()
    lines = content.splitlines()
    words = content.split()

    if len(lines) > SKILL_MD_MAX_LINES:
        warnings.append(
            f"SKILL.md has {len(lines)} lines (recommended max: {SKILL_MD_MAX_LINES}). "
            "Consider moving detailed docs to references/."
        )

    if len(words) > SKILL_MD_MAX_WORDS:
        warnings.append(
            f"SKILL.md has {len(words)} words (recommended max: {SKILL_MD_MAX_WORDS}). "
            "Consider using progressive disclosure."
        )

    try:
        metadata, body = parse_frontmatter(content)
    except Exception:
        return warnings

    description = metadata.get("description", "")
    if description:
        desc_lower = description.lower()

        has_what = any(w in desc_lower for w in [
            "use when", "use for", "handles", "manages", "creates",
            "generates", "monitors", "validates", "analyzes",
        ])
        has_when = any(w in desc_lower for w in [
            "use when", "when user", "when the", "if user",
            "trigger", "mention",
        ])

        if not has_what:
            warnings.append(
                "Description may be missing WHAT the skill does. "
                "Include verbs like 'handles', 'generates', 'monitors'."
            )
        if not has_when:
            warnings.append(
                "Description may be missing WHEN to use it (trigger conditions). "
                "Include phrases like 'Use when user says...' or trigger keywords."
            )
        if "<" in description or ">" in description:
            warnings.append(
                "Description contains angle brackets (< >), which are "
                "forbidden in frontmatter per the skills guide."
            )

    refs_dir = skill_path / "references"
    if refs_dir.exists() and refs_dir.is_dir():
        ref_files = list(refs_dir.iterdir())
        if ref_files:
            body_lower = body.lower() if body else ""
            for ref_file in ref_files:
                if ref_file.name.startswith("."):
                    continue
                if ref_file.name.lower() not in body_lower:
                    warnings.append(
                        f"Reference file '{ref_file.name}' may not be linked "
                        "from SKILL.md. Link references so Claude knows about them."
                    )

    return warnings


def validate_single(skill_path: Path, verbose: bool = False) -> tuple[bool, list[str], list[str]]:
    """Validate a single skill. Returns (is_valid, errors, warnings)."""
    errors = validate(skill_path)
    warnings = check_best_practices(skill_path)

    if verbose:
        if errors:
            print(f"  ERRORS ({len(errors)}):", file=sys.stderr)
            for e in errors:
                print(f"    - {e}", file=sys.stderr)
        if warnings:
            print(f"  WARNINGS ({len(warnings)}):", file=sys.stderr)
            for w in warnings:
                print(f"    - {w}", file=sys.stderr)

    return len(errors) == 0, errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate skills against spec and best practices."
    )
    parser.add_argument(
        "skill_path", nargs="?", type=Path, default=None,
        help="Path to skill directory to validate",
    )
    parser.add_argument("--all", action="store_true", help="Validate all skills in repo")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.all:
        skills = discover_skills(Path("."))
        all_valid = True

        for skill_dir in skills:
            name = skill_dir.name
            print(f"Validating {name} ({skill_dir})...", file=sys.stderr)
            is_valid, errors, warnings = validate_single(skill_dir, args.verbose)

            if is_valid:
                status = "PASS"
                if warnings:
                    status += f" ({len(warnings)} warnings)"
                print(f"  {status}")
            else:
                status = f"FAIL ({len(errors)} errors)"
                if warnings:
                    status += f" ({len(warnings)} warnings)"
                print(f"  {status}")
                all_valid = False
                if not args.verbose:
                    for e in errors:
                        print(f"    - {e}")

        sys.exit(0 if all_valid else 1)

    elif args.skill_path:
        is_valid, errors, warnings = validate_single(args.skill_path, True)

        if is_valid:
            print(f"Valid skill: {args.skill_path}")
            if warnings:
                print(f"\n{len(warnings)} warning(s):")
                for w in warnings:
                    print(f"  - {w}")
        else:
            print(f"Validation failed for {args.skill_path}:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            if warnings:
                print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
                for w in warnings:
                    print(f"  - {w}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
