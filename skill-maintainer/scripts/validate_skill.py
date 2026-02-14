#!/usr/bin/env python3
"""
Validate a skill against the Agent Skills spec and best practices.

Wraps the skills-ref validator and adds additional checks from best_practices.md.
Records validation results in DuckDB for trend tracking.

Usage:
    uv run python skill-maintainer/scripts/validate_skill.py ./skill-maintainer
    uv run python skill-maintainer/scripts/validate_skill.py ./plugin-toolkit/skills/plugin-toolkit
    uv run python skill-maintainer/scripts/validate_skill.py --all
"""

import argparse
import sys
from pathlib import Path

import yaml

# Import skills-ref directly for programmatic access
from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")

# Additional checks beyond what skills-ref validates
SKILL_MD_MAX_LINES = 500
SKILL_MD_MAX_WORDS = 5000


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def check_best_practices(skill_path: Path) -> list[str]:
    """Run additional best-practice checks beyond skills-ref validation.

    Returns list of warning strings (not necessarily errors).
    """
    warnings = []
    skill_md = find_skill_md(skill_path)

    if skill_md is None:
        return ["SKILL.md not found"]

    content = skill_md.read_text()
    lines = content.splitlines()
    words = content.split()

    # Size checks
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

    # Parse frontmatter for additional checks
    try:
        metadata, body = parse_frontmatter(content)
    except Exception:
        return warnings  # skills-ref will catch parse errors

    # Description quality checks
    description = metadata.get("description", "")
    if description:
        desc_lower = description.lower()

        # Check for WHAT + WHEN pattern
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

        # Check for XML brackets (forbidden in frontmatter)
        if "<" in description or ">" in description:
            warnings.append(
                "Description contains angle brackets (< >), which are "
                "forbidden in frontmatter per the skills guide."
            )

    # Check for README.md in skill folder (not recommended)
    readme = skill_path / "README.md"
    if readme.exists():
        warnings.append(
            "README.md found in skill folder. The skills guide recommends "
            "putting all documentation in SKILL.md or references/."
        )

    # Check references are linked
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
    """Validate a single skill.

    Returns (is_valid, errors, warnings).
    """
    # Run skills-ref validation
    errors = validate(skill_path)

    # Run best practice checks
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


def _skill_name_from_config(skill_path: Path, config: dict) -> str | None:
    """Find the skill name in config that matches this path."""
    skill_path_str = str(skill_path)
    for name, skill_config in config.get("skills", {}).items():
        config_path = skill_config.get("path", "")
        # Normalize both paths for comparison
        if Path(config_path).resolve() == Path(skill_path_str).resolve():
            return name
        # Also try without resolve for relative paths
        if config_path.lstrip("./") in skill_path_str:
            return name
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Validate skills against spec and best practices."
    )
    parser.add_argument(
        "skill_path", nargs="?", type=Path, default=None,
        help="Path to skill directory to validate",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Validate all skills in config.yaml",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
    )
    args = parser.parse_args()

    if args.all:
        config = load_config(args.config)
        skills = config.get("skills", {})
        all_valid = True

        with Store(db_path=args.db, config_path=args.config) as store:
            for name, skill_config in skills.items():
                path = Path(skill_config["path"])
                print(f"Validating {name} ({path})...", file=sys.stderr)
                is_valid, errors, warnings = validate_single(path, args.verbose)

                # Record in DuckDB
                store.record_validation(
                    name, is_valid,
                    errors=errors, warnings=warnings,
                    trigger_type="manual",
                )

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

        # Try to record in DuckDB if we can find the skill name
        config = load_config(args.config)
        skill_name = _skill_name_from_config(args.skill_path, config)
        if skill_name:
            with Store(db_path=args.db, config_path=args.config) as store:
                store.record_validation(
                    skill_name, is_valid,
                    errors=errors, warnings=warnings,
                    trigger_type="manual",
                )

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
