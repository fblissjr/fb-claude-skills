#!/usr/bin/env python3
"""
Query the append-only changes log.

Reads state/changes.jsonl and filters by date, event type, or skill name.

Usage:
    uv run python skill-maintainer/scripts/query_log.py
    uv run python skill-maintainer/scripts/query_log.py --days 7
    uv run python skill-maintainer/scripts/query_log.py --type upstream_check
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import orjson

CHANGES_LOG = Path("skill-maintainer/state/changes.jsonl")


def load_events() -> list[dict]:
    if not CHANGES_LOG.exists():
        return []
    events = []
    for line in CHANGES_LOG.read_bytes().splitlines():
        if line.strip():
            events.append(orjson.loads(line))
    return events


def main():
    parser = argparse.ArgumentParser(description="Query the changes log.")
    parser.add_argument("--days", type=int, default=None, help="Show events from last N days")
    parser.add_argument("--type", type=str, default=None, help="Filter by event type")
    parser.add_argument("--tail", type=int, default=None, help="Show last N events")
    args = parser.parse_args()

    events = load_events()
    if not events:
        print("No events in log.", file=sys.stderr)
        sys.exit(0)

    # Filter by date
    if args.days is not None:
        cutoff = (date.today() - timedelta(days=args.days)).isoformat()
        events = [e for e in events if e.get("date", "") >= cutoff]

    # Filter by type
    if args.type:
        events = [e for e in events if e.get("type") == args.type]

    # Tail
    if args.tail:
        events = events[-args.tail:]

    if not events:
        print("No matching events.", file=sys.stderr)
        sys.exit(0)

    for event in events:
        event_type = event.get("type", "?")
        event_date = event.get("date", "?")
        # Format depends on type
        if event_type == "upstream_check":
            n = event.get("total_changed", 0)
            pages = event.get("changed_pages", [])
            detail = f"{n} pages changed" if n else "no changes"
            if pages:
                detail += f": {', '.join(p.split('/')[-1] for p in pages[:3])}"
        elif event_type == "quality_report":
            detail = (
                f"{event.get('valid', '?')}/{event.get('skills', '?')} valid, "
                f"{event.get('over_budget', 0)} over budget, "
                f"{event.get('stale', 0)} stale"
            )
        else:
            detail = str(event)

        print(f"[{event_date}] {event_type}: {detail}")


if __name__ == "__main__":
    main()
