#!/usr/bin/env python3
"""
Lightweight staleness check for skill freshness.

Reads state.json, checks last_updated timestamps, warns if stale.
Designed to be fast (<100ms) - just reads a JSON file.
Never blocks skill invocation.

Usage:
    uv run python skill-maintainer/scripts/check_freshness.py
    uv run python skill-maintainer/scripts/check_freshness.py plugin-toolkit
    uv run python skill-maintainer/scripts/check_freshness.py --threshold 14d
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import orjson
import yaml


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_STATE = Path("skill-maintainer/state/state.json")
DEFAULT_THRESHOLD_DAYS = 7


def parse_threshold(threshold_str: str) -> timedelta:
    """Parse a threshold string like '7d', '24h', '168h' into a timedelta."""
    s = threshold_str.strip().lower()
    if s.endswith("d"):
        return timedelta(days=int(s[:-1]))
    elif s.endswith("h"):
        return timedelta(hours=int(s[:-1]))
    else:
        return timedelta(days=int(s))


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    data = state_path.read_bytes()
    if not data or data.strip() == b"{}":
        return {}
    return orjson.loads(data)


def get_last_checked(state: dict, source_name: str) -> str | None:
    """Get the most recent check timestamp for a source."""
    # Check docs state
    docs = state.get("docs", {}).get(source_name, {})
    timestamps = []
    for url, url_data in docs.items():
        if url.startswith("_"):
            ts = docs.get("_file_last_checked")
            if ts:
                timestamps.append(ts)
        elif isinstance(url_data, dict):
            ts = url_data.get("last_checked")
            if ts:
                timestamps.append(ts)

    # Check sources state
    src = state.get("sources", {}).get(source_name, {})
    if isinstance(src, dict):
        ts = src.get("last_checked")
        if ts:
            timestamps.append(ts)

    if not timestamps:
        return None
    return max(timestamps)


def check_skill_freshness(
    skill_name: str,
    config: dict,
    state: dict,
    threshold: timedelta,
) -> dict:
    """Check freshness of a single skill.

    Returns dict with: name, is_stale, last_checked, staleness_days, sources
    """
    skill_config = config.get("skills", {}).get(skill_name, {})
    if not skill_config:
        return {
            "name": skill_name,
            "is_stale": True,
            "last_checked": None,
            "staleness_days": None,
            "message": f"Skill '{skill_name}' not found in config",
        }

    skill_sources = skill_config.get("sources", [])
    now = datetime.now(timezone.utc)
    oldest_check = None

    source_status = []
    for source_name in skill_sources:
        last_checked = get_last_checked(state, source_name)
        if last_checked:
            ts = datetime.fromisoformat(last_checked)
            if oldest_check is None or ts < oldest_check:
                oldest_check = ts
            age = now - ts
            source_status.append({
                "source": source_name,
                "last_checked": last_checked,
                "age_days": age.days,
                "is_stale": age > threshold,
            })
        else:
            source_status.append({
                "source": source_name,
                "last_checked": None,
                "age_days": None,
                "is_stale": True,
            })

    if oldest_check is None:
        return {
            "name": skill_name,
            "is_stale": True,
            "last_checked": None,
            "staleness_days": None,
            "sources": source_status,
            "message": f"skill-maintainer: {skill_name} has never been checked. "
                       "Run `/skill-maintainer check` to capture initial state.",
        }

    age = now - oldest_check
    is_stale = age > threshold

    message = None
    if is_stale:
        message = (
            f"skill-maintainer: {skill_name} was last checked "
            f"{age.days} days ago. Run `/skill-maintainer check` "
            "to see what changed."
        )

    return {
        "name": skill_name,
        "is_stale": is_stale,
        "last_checked": oldest_check.isoformat(),
        "staleness_days": age.days,
        "sources": source_status,
        "message": message,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check freshness of tracked skills."
    )
    parser.add_argument(
        "skill", nargs="?", default=None,
        help="Skill name to check (default: all tracked skills)",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
    )
    parser.add_argument(
        "--threshold", default=f"{DEFAULT_THRESHOLD_DAYS}d",
        help=f"Staleness threshold (default: {DEFAULT_THRESHOLD_DAYS}d)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Only output warnings for stale skills",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    state = load_state(args.state)
    threshold = parse_threshold(args.threshold)

    skills_to_check = []
    if args.skill:
        skills_to_check = [args.skill]
    else:
        skills_to_check = list(config.get("skills", {}).keys())

    any_stale = False
    for skill_name in skills_to_check:
        result = check_skill_freshness(skill_name, config, state, threshold)

        if result["is_stale"]:
            any_stale = True
            if result.get("message"):
                print(result["message"], file=sys.stderr)
        elif not args.quiet:
            checked = result.get("staleness_days", "?")
            print(
                f"{skill_name}: OK (last checked {checked} days ago)",
                file=sys.stderr,
            )

    # Exit 0 always - this is a warning tool, not a gate
    sys.exit(0)


if __name__ == "__main__":
    main()
