"""Validate skills against the Agent Skills spec and best practices."""

import sys
from pathlib import Path

from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

from skill_maintainer.shared import check_description_quality, discover_skills

SKILL_MD_MAX_LINES = 500
SKILL_MD_MAX_WORDS = 5000


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
        desc_issues = check_description_quality(description)
        for issue in desc_issues:
            warnings.append(f"Description: {issue}")
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


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate skills against spec and best practices."
    )
    parser.add_argument(
        "skill_path", nargs="?", type=Path, default=None,
        help="Path to skill directory to validate",
    )
    parser.add_argument("--all", action="store_true", help="Validate all skills")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search")
    parser.add_argument("--verbose", "-v", action="store_true")
    parsed = parser.parse_args(args)

    if parsed.all:
        skills = discover_skills(parsed.dir)
        all_valid = True

        for skill_dir in skills:
            name = skill_dir.name
            print(f"Validating {name} ({skill_dir})...", file=sys.stderr)
            is_valid, errors, warnings = validate_single(skill_dir, parsed.verbose)

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
                if not parsed.verbose:
                    for e in errors:
                        print(f"    - {e}")

        sys.exit(0 if all_valid else 1)

    elif parsed.skill_path:
        is_valid, errors, warnings = validate_single(parsed.skill_path, True)

        if is_valid:
            print(f"Valid skill: {parsed.skill_path}")
            if warnings:
                print(f"\n{len(warnings)} warning(s):")
                for w in warnings:
                    print(f"  - {w}")
        else:
            print(f"Validation failed for {parsed.skill_path}:", file=sys.stderr)
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
