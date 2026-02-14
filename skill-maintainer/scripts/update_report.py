#!/usr/bin/env python3
"""
Produce a unified SKILLS_UPDATE.md-style report combining docs and source changes.

Reads from DuckDB store for recent changes and generates an actionable report
mapping changes to affected skills.

Usage:
    uv run python skill-maintainer/scripts/update_report.py
    uv run python skill-maintainer/scripts/update_report.py --output state/last_report.md
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def find_affected_skills(
    config: dict,
    changed_sources: list[str],
) -> dict[str, list[str]]:
    """Map changed sources to the skills that depend on them.

    Returns: {skill_name: [source_names]}
    """
    affected = {}
    skills = config.get("skills", {})
    for skill_name, skill_config in skills.items():
        skill_sources = skill_config.get("sources", [])
        matched = [s for s in changed_sources if s in skill_sources]
        if matched:
            affected[skill_name] = matched
    return affected


def generate_unified_report(config: dict, store: Store) -> str:
    """Generate a unified report combining all monitoring data from DuckDB."""
    lines = [
        "# Skills Update Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    # Get recent changes from DuckDB
    recent_changes = store.get_recent_changes(days=30)

    if not recent_changes:
        lines.append("No changes detected. All monitored sources are current.")
        lines.append("")
        lines.append("Run the monitors to check for updates:")
        lines.append("```bash")
        lines.append("uv run python skill-maintainer/scripts/docs_monitor.py")
        lines.append("uv run python skill-maintainer/scripts/source_monitor.py")
        lines.append("```")
        return "\n".join(lines)

    # Separate docs changes and source changes
    docs_changes = []
    source_changes = []
    changed_sources = set()

    for change in recent_changes:
        changed_sources.add(change["source_name"])
        if change["page_url"]:
            docs_changes.append(change)
        elif change["commit_hash"]:
            source_changes.append(change)

    # Affected skills
    affected = find_affected_skills(config, list(changed_sources))
    if affected:
        lines.append("## Affected Skills")
        lines.append("")
        for skill_name, sources in affected.items():
            skill_config = config.get("skills", {}).get(skill_name, {})
            auto_update = skill_config.get("auto_update", False)
            skill_path = skill_config.get("path", "")
            mode = "auto-update enabled" if auto_update else "manual review required"
            lines.append(f"### {skill_name}")
            lines.append(f"- **Path**: `{skill_path}`")
            lines.append(f"- **Changed sources**: {', '.join(sources)}")
            lines.append(f"- **Mode**: {mode}")
            lines.append("")

    # Docs changes detail
    if docs_changes:
        lines.append("## Documentation Changes")
        lines.append("")
        for dc in docs_changes:
            lines.append(f"- [{dc['classification']}] **{dc['source_name']}**: `{dc['page_url']}`")
            lines.append(f"  - {dc['summary']}")
            lines.append(f"  - Hash: `{dc['new_hash'][:12]}`")
            lines.append(f"  - Detected: {dc['detected_at']}")
        lines.append("")

    # Source changes detail
    if source_changes:
        lines.append("## Source Repository Changes")
        lines.append("")
        for sc in source_changes:
            count = sc["commit_count"] or 0
            lines.append(f"- [{sc['classification']}] **{sc['source_name']}**: {count} new commits")
            lines.append(f"  - Latest: `{sc['commit_hash']}`")
            lines.append(f"  - {sc['summary']}")
            lines.append(f"  - Detected: {sc['detected_at']}")
        lines.append("")

    # Suggested actions
    lines.append("## Suggested Actions")
    lines.append("")
    if affected:
        for skill_name in affected:
            lines.append(
                f"- Review and update `{skill_name}`: "
                f"`uv run python skill-maintainer/scripts/apply_updates.py --skill {skill_name}`"
            )
    lines.append(
        "- Validate all skills: "
        "`uv run skills-ref validate <skill-path>`"
    )
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate unified skills update report."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    with Store(db_path=args.db, config_path=args.config) as store:
        report = generate_unified_report(config, store)

    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
