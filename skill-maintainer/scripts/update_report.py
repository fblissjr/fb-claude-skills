#!/usr/bin/env python3
"""
Produce a unified SKILLS_UPDATE.md-style report combining docs and source changes.

Reads state.json for recent check results and generates an actionable report
mapping changes to affected skills.

Usage:
    uv run python skill-maintainer/scripts/update_report.py
    uv run python skill-maintainer/scripts/update_report.py --output state/last_report.md
"""

import argparse
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


def generate_unified_report(config: dict, state: dict) -> str:
    """Generate a unified report combining all monitoring data."""
    lines = [
        "# Skills Update Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    changed_sources = []

    # Docs changes
    docs_state = state.get("docs", {})
    docs_changes = []
    for source_name, urls in docs_state.items():
        if not isinstance(urls, dict):
            continue
        for url, url_data in urls.items():
            if url.startswith("_"):
                continue
            if not isinstance(url_data, dict):
                continue
            last_checked = url_data.get("last_checked", "")
            content_hash = url_data.get("hash", "")
            if content_hash:
                docs_changes.append({
                    "source": source_name,
                    "url": url,
                    "hash": content_hash[:12],
                    "last_checked": last_checked,
                })
                if source_name not in changed_sources:
                    changed_sources.append(source_name)

    # Source repo changes
    sources_state = state.get("sources", {})
    source_changes = []
    for source_name, src_data in sources_state.items():
        if not isinstance(src_data, dict):
            continue
        commits = src_data.get("commits_since_last", 0)
        if commits > 0:
            source_changes.append({
                "source": source_name,
                "commits": commits,
                "last_commit": src_data.get("last_commit", ""),
                "last_checked": src_data.get("last_checked", ""),
            })
            if source_name not in changed_sources:
                changed_sources.append(source_name)

    # Report sections
    if not docs_changes and not source_changes:
        lines.append("No changes detected. All monitored sources are current.")
        lines.append("")
        lines.append("Run the monitors to check for updates:")
        lines.append("```bash")
        lines.append("uv run python skill-maintainer/scripts/docs_monitor.py")
        lines.append("uv run python skill-maintainer/scripts/source_monitor.py")
        lines.append("```")
        return "\n".join(lines)

    # Affected skills
    affected = find_affected_skills(config, changed_sources)
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
            lines.append(f"- **{dc['source']}**: `{dc['url']}`")
            lines.append(f"  - Hash: `{dc['hash']}`")
            lines.append(f"  - Last checked: {dc['last_checked']}")
        lines.append("")

    # Source changes detail
    if source_changes:
        lines.append("## Source Repository Changes")
        lines.append("")
        for sc in source_changes:
            lines.append(f"- **{sc['source']}**: {sc['commits']} new commits")
            lines.append(f"  - Latest: `{sc['last_commit']}`")
            lines.append(f"  - Last checked: {sc['last_checked']}")
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
        "--state", type=Path, default=DEFAULT_STATE,
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    state = load_state(args.state)

    report = generate_unified_report(config, state)

    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
