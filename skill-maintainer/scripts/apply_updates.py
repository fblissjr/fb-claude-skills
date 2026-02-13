#!/usr/bin/env python3
"""
Apply detected changes to skills: the key differentiator from mlx-skills.

Reads change reports from monitors, classifies changes, and applies updates
with validation. Supports multiple modes: report-only, apply-local, create-pr.

Usage:
    uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit
    uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit --mode report-only
    uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit --mode apply-local
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import orjson
import yaml


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    data = state_path.read_bytes()
    if not data or data.strip() == b"{}":
        return {}
    return orjson.loads(data)


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))


def validate_skill(skill_path: Path) -> tuple[bool, list[str]]:
    """Run skills-ref validate on a skill directory.

    Returns (is_valid, list_of_errors).
    """
    try:
        result = subprocess.run(
            ["uv", "run", "skills-ref", "validate", str(skill_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return True, []
        errors = [
            line.strip().lstrip("- ")
            for line in result.stderr.splitlines()
            if line.strip() and not line.startswith("Validation failed")
        ]
        return False, errors
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, [f"Validation command failed: {e}"]


def backup_skill(skill_path: Path) -> Path:
    """Create a backup of the skill directory before modifications.

    Returns the backup path.
    """
    backup_path = skill_path.parent / f"{skill_path.name}.backup"
    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.copytree(skill_path, backup_path)
    return backup_path


def restore_from_backup(skill_path: Path, backup_path: Path) -> None:
    """Restore skill from backup after a failed update."""
    if backup_path.exists():
        shutil.rmtree(skill_path)
        shutil.copytree(backup_path, skill_path)
        shutil.rmtree(backup_path)


def cleanup_backup(backup_path: Path) -> None:
    """Remove backup after successful update."""
    if backup_path.exists():
        shutil.rmtree(backup_path)


def get_changes_for_skill(
    skill_name: str,
    config: dict,
    state: dict,
) -> list[dict]:
    """Extract pending changes relevant to a specific skill."""
    skill_config = config.get("skills", {}).get(skill_name, {})
    if not skill_config:
        return []

    skill_sources = skill_config.get("sources", [])
    changes = []

    # Check docs changes (CDC format: _pages dict with per-page state)
    docs_state = state.get("docs", {})
    for source_name in skill_sources:
        source_data = docs_state.get(source_name, {})
        pages = source_data.get("_pages", {})
        if not isinstance(pages, dict):
            continue
        for url, page_data in pages.items():
            if not isinstance(page_data, dict):
                continue
            if page_data.get("hash"):
                changes.append({
                    "type": "docs",
                    "source": source_name,
                    "url": url,
                    "hash": page_data.get("hash", "")[:12],
                    "last_checked": page_data.get("last_checked", ""),
                    "last_changed": page_data.get("last_changed", ""),
                })

    # Check source repo changes
    sources_state = state.get("sources", {})
    for source_name in skill_sources:
        if source_name in sources_state:
            src_data = sources_state[source_name]
            if isinstance(src_data, dict) and src_data.get("commits_since_last", 0) > 0:
                changes.append({
                    "type": "source",
                    "source": source_name,
                    "commits": src_data.get("commits_since_last", 0),
                    "last_commit": src_data.get("last_commit", ""),
                    "last_checked": src_data.get("last_checked", ""),
                })

    return changes


def generate_update_context(
    skill_name: str,
    skill_path: Path,
    changes: list[dict],
) -> str:
    """Generate context for Claude-assisted skill updates.

    This produces a structured prompt that describes what changed and
    what the skill currently looks like, so Claude can suggest updates.
    """
    skill_md = skill_path / "SKILL.md"
    current_content = skill_md.read_text() if skill_md.exists() else "(missing)"

    lines = [
        f"# Update Context for {skill_name}",
        "",
        "## Current SKILL.md",
        "```markdown",
        current_content,
        "```",
        "",
        "## Detected Changes",
        "",
    ]

    for change in changes:
        if change["type"] == "docs":
            lines.append(
                f"- Documentation change in **{change['source']}**: "
                f"`{change['url']}` (hash: `{change['hash']}`)"
            )
        elif change["type"] == "source":
            lines.append(
                f"- Source code change in **{change['source']}**: "
                f"{change['commits']} new commits (latest: `{change['last_commit']}`)"
            )

    lines.extend([
        "",
        "## Instructions",
        "",
        "Review the changes above and determine if the skill needs updating.",
        "Check against the best practices in `skill-maintainer/references/best_practices.md`.",
        "If updates are needed, modify the SKILL.md to incorporate the changes.",
        "Then validate with: `uv run skills-ref validate " + str(skill_path) + "`",
    ])

    return "\n".join(lines)


def apply_report_only(
    skill_name: str,
    skill_path: Path,
    changes: list[dict],
) -> str:
    """Generate report without making changes."""
    lines = [
        f"# Update Report: {skill_name}",
        "",
        f"Path: `{skill_path}`",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not changes:
        lines.append("No pending changes for this skill.")
        return "\n".join(lines)

    lines.append(f"## {len(changes)} Pending Change(s)")
    lines.append("")

    for change in changes:
        if change["type"] == "docs":
            lines.append(f"### Docs: {change['source']}")
            lines.append(f"- URL: `{change['url']}`")
            lines.append(f"- Hash: `{change['hash']}`")
            lines.append(f"- Last checked: {change['last_checked']}")
        elif change["type"] == "source":
            lines.append(f"### Source: {change['source']}")
            lines.append(f"- Commits: {change['commits']}")
            lines.append(f"- Latest: `{change['last_commit']}`")
            lines.append(f"- Last checked: {change['last_checked']}")
        lines.append("")

    # Validation status
    is_valid, errors = validate_skill(skill_path)
    lines.append("## Current Validation Status")
    lines.append("")
    if is_valid:
        lines.append("PASS: Skill currently passes validation.")
    else:
        lines.append("FAIL: Skill has validation errors:")
        for err in errors:
            lines.append(f"  - {err}")
    lines.append("")

    # Update context for Claude
    lines.append("## Update Context (for Claude-assisted editing)")
    lines.append("")
    lines.append("```")
    lines.append(generate_update_context(skill_name, skill_path, changes))
    lines.append("```")

    return "\n".join(lines)


def apply_local(
    skill_name: str,
    skill_path: Path,
    changes: list[dict],
    state: dict,
    state_path: Path,
) -> str:
    """Apply changes locally, validate, leave for user to review.

    This is the default mode. It:
    1. Creates a backup
    2. Generates update context
    3. Validates the skill (pre-check)
    4. Records the update attempt in state
    5. Does NOT auto-edit files (that's for Claude to do interactively)
    """
    lines = [
        f"# Local Update: {skill_name}",
        "",
        f"Path: `{skill_path}`",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not changes:
        lines.append("No pending changes for this skill.")
        return "\n".join(lines)

    # Pre-validation
    is_valid, errors = validate_skill(skill_path)
    lines.append("## Pre-Update Validation")
    if is_valid:
        lines.append("PASS")
    else:
        lines.append("FAIL (existing issues):")
        for err in errors:
            lines.append(f"  - {err}")
    lines.append("")

    # Create backup
    backup_path = backup_skill(skill_path)
    lines.append(f"Backup created at: `{backup_path}`")
    lines.append("")

    # Generate context
    context = generate_update_context(skill_name, skill_path, changes)
    lines.append("## Update Context")
    lines.append("")
    lines.append(context)
    lines.append("")

    # Record update attempt in state
    if "updates" not in state:
        state["updates"] = {}
    state["updates"][skill_name] = {
        "last_attempt": datetime.now(timezone.utc).isoformat(),
        "changes_count": len(changes),
        "backup_path": str(backup_path),
        "status": "pending_review",
    }
    save_state(state_path, state)

    lines.extend([
        "## Next Steps",
        "",
        "1. Review the changes above",
        "2. Edit the skill files as needed",
        f"3. Validate: `uv run skills-ref validate {skill_path}`",
        "4. If satisfied, remove the backup: "
        f"`rm -rf {backup_path}`",
        "5. Commit the changes",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Apply detected changes to a skill."
    )
    parser.add_argument(
        "--skill", required=True,
        help="Name of the skill to update (from config.yaml)",
    )
    parser.add_argument(
        "--mode", choices=["report-only", "apply-local", "create-pr"],
        default="apply-local",
        help="Update mode (default: apply-local)",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
    )
    parser.add_argument(
        "--output", type=Path, default=None,
    )
    args = parser.parse_args()

    config = load_config(args.config)
    state = load_state(args.state)

    skill_config = config.get("skills", {}).get(args.skill)
    if not skill_config:
        print(
            f"Error: skill '{args.skill}' not found in config.yaml",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_path = Path(skill_config["path"])
    if not skill_path.exists():
        print(
            f"Error: skill path does not exist: {skill_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    changes = get_changes_for_skill(args.skill, config, state)

    if args.mode == "report-only":
        report = apply_report_only(args.skill, skill_path, changes)
    elif args.mode == "apply-local":
        report = apply_local(
            args.skill, skill_path, changes, state, args.state,
        )
    elif args.mode == "create-pr":
        # For CI: same as apply-local but would create branch + PR
        # Keeping it simple for now - outputs the context for CI to use
        report = apply_local(
            args.skill, skill_path, changes, state, args.state,
        )
        report += "\n\n(create-pr mode: CI should create branch and PR from this)\n"
    else:
        report = f"Unknown mode: {args.mode}"

    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
