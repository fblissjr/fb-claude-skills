#!/usr/bin/env python3
"""
Apply detected changes to skills: the key differentiator from mlx-skills.

Reads change reports from monitors, classifies changes, and applies updates
with validation. Supports multiple modes: report-only, apply-local, create-pr.

State is stored in DuckDB via the Store class. Backward-compatible state.json
is exported after each run.

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

import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


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
    """Create a backup of the skill directory before modifications."""
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
    store: Store,
) -> list[dict]:
    """Extract pending changes relevant to a specific skill from DuckDB."""
    skill_config = config.get("skills", {}).get(skill_name, {})
    if not skill_config:
        return []

    changes = []

    # Get recent changes from the store for sources this skill depends on
    skill_sources = skill_config.get("sources", [])
    recent = store.get_recent_changes(days=30)

    for change in recent:
        if change["source_name"] in skill_sources:
            if change["page_url"]:
                changes.append({
                    "type": "docs",
                    "source": change["source_name"],
                    "url": change["page_url"],
                    "hash": change["new_hash"][:12] if change["new_hash"] else "",
                    "classification": change["classification"],
                    "summary": change["summary"],
                    "detected_at": change["detected_at"],
                })
            elif change["commit_hash"]:
                changes.append({
                    "type": "source",
                    "source": change["source_name"],
                    "commits": change["commit_count"] or 0,
                    "last_commit": change["commit_hash"],
                    "classification": change["classification"],
                    "summary": change["summary"],
                    "detected_at": change["detected_at"],
                })

    return changes


def generate_update_context(
    skill_name: str,
    skill_path: Path,
    changes: list[dict],
) -> str:
    """Generate context for Claude-assisted skill updates."""
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
                f"- [{change['classification']}] Documentation change in **{change['source']}**: "
                f"`{change['url']}` (hash: `{change['hash']}`)"
            )
        elif change["type"] == "source":
            lines.append(
                f"- [{change['classification']}] Source code change in **{change['source']}**: "
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
    store: Store,
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
            lines.append(f"### [{change['classification']}] Docs: {change['source']}")
            lines.append(f"- URL: `{change['url']}`")
            lines.append(f"- Hash: `{change['hash']}`")
            lines.append(f"- Detected: {change['detected_at']}")
        elif change["type"] == "source":
            lines.append(f"### [{change['classification']}] Source: {change['source']}")
            lines.append(f"- Commits: {change['commits']}")
            lines.append(f"- Latest: `{change['last_commit']}`")
            lines.append(f"- Detected: {change['detected_at']}")
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

    # Record validation
    store.record_validation(
        skill_name, is_valid, errors=errors, trigger_type="report-only",
    )

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
    store: Store,
) -> str:
    """Apply changes locally, validate, leave for user to review."""
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

    # Record validation
    store.record_validation(
        skill_name, is_valid, errors=errors, trigger_type="pre-update",
    )

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

    # Record update attempt in Store
    store.record_update_attempt(
        skill_name,
        mode="apply-local",
        status="pending_review",
        changes_applied=len(changes),
        backup_path=str(backup_path),
    )

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
        "--db", type=Path, default=DEFAULT_DB,
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
        help="Path to export backward-compatible state.json",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
    )
    args = parser.parse_args()

    config = load_config(args.config)

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

    with Store(db_path=args.db, config_path=args.config) as store:
        changes = get_changes_for_skill(args.skill, config, store)

        if args.mode == "report-only":
            report = apply_report_only(args.skill, skill_path, changes, store)
        elif args.mode == "apply-local":
            report = apply_local(args.skill, skill_path, changes, store)
        elif args.mode == "create-pr":
            report = apply_local(args.skill, skill_path, changes, store)
            report += "\n\n(create-pr mode: CI should create branch and PR from this)\n"
        else:
            report = f"Unknown mode: {args.mode}"

        # Export backward-compatible state.json
        store.export_state_json_file(args.state)

    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
