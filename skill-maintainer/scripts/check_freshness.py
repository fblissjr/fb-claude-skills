#!/usr/bin/env python3
"""
Lightweight staleness check for skill freshness.

Reads from DuckDB store, checks last_checked timestamps, warns if stale.
Designed to be fast -- just reads a few DB rows.
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

import yaml

from store import Store


DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
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


def get_last_checked_for_source(store: Store, source_name: str) -> str | None:
    """Get the most recent check timestamp for a source from DuckDB."""
    timestamps = []

    # Check watermark (docs sources)
    wm_ts = store.get_latest_watermark_checked_at(source_name)
    if wm_ts:
        timestamps.append(wm_ts)

    # Check page timestamps
    page_ts = store.get_latest_page_checked_at(source_name)
    if page_ts:
        timestamps.append(page_ts)

    # Check file hash timestamp
    fh = store.get_file_hash(source_name)
    if fh and fh.get("last_checked"):
        timestamps.append(fh["last_checked"])

    # Check source repo timestamp
    src = store.get_latest_source_check(source_name)
    if src and src.get("last_checked"):
        timestamps.append(src["last_checked"])

    if not timestamps:
        return None
    return max(timestamps)


def check_skill_freshness(
    skill_name: str,
    config: dict,
    store: Store,
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
        last_checked = get_last_checked_for_source(store, source_name)
        if last_checked:
            ts = datetime.fromisoformat(last_checked)
            # Ensure timezone-aware for comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
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
        "--db", type=Path, default=DEFAULT_DB,
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
    threshold = parse_threshold(args.threshold)

    skills_to_check = []
    if args.skill:
        skills_to_check = [args.skill]
    else:
        skills_to_check = list(config.get("skills", {}).keys())

    with Store(db_path=args.db, config_path=args.config) as store:
        for skill_name in skills_to_check:
            result = check_skill_freshness(skill_name, config, store, threshold)

            if result["is_stale"]:
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
