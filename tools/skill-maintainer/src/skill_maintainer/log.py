"""Query the append-only changes log."""

import sys
from datetime import date, timedelta
from pathlib import Path

import orjson

from skill_maintainer.config import changes_log


def load_events(root: Path) -> list[dict]:
    log_path = changes_log(root)
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_bytes().splitlines():
        if line.strip():
            events.append(orjson.loads(line))
    return events


def main(args=None):
    import argparse

    parser = argparse.ArgumentParser(description="Query the changes log.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory (for state)")
    parser.add_argument("--days", type=int, default=None, help="Show events from last N days")
    parser.add_argument("--type", type=str, default=None, help="Filter by event type")
    parser.add_argument("--tail", type=int, default=None, help="Show last N events")
    parsed = parser.parse_args(args)

    events = load_events(parsed.dir)
    if not events:
        print("No events in log.", file=sys.stderr)
        sys.exit(0)

    # Filter by date
    if parsed.days is not None:
        cutoff = (date.today() - timedelta(days=parsed.days)).isoformat()
        events = [e for e in events if e.get("date", "") >= cutoff]

    # Filter by type
    if parsed.type:
        events = [e for e in events if e.get("type") == parsed.type]

    # Tail
    if parsed.tail:
        events = events[-parsed.tail:]

    if not events:
        print("No matching events.", file=sys.stderr)
        sys.exit(0)

    for event in events:
        event_type = event.get("type", "?")
        event_date = event.get("date", "?")
        if event_type == "upstream_check":
            n = event.get("total_changed", 0)
            pages = event.get("changed_pages", [])
            detail = f"{n} pages changed" if n else "no changes"
            if pages:
                detail += f": {', '.join(p.split('/')[-1] for p in pages[:3])}"
        elif event_type == "source_pull":
            n = event.get("repos_changed", 0)
            repos = [c["repo"].replace("coderef/", "") for c in event.get("changes", [])]
            detail = f"{n}/{event.get('repos_checked', '?')} repos changed"
            if repos:
                detail += f": {', '.join(repos[:3])}"
                if len(repos) > 3:
                    detail += f" +{len(repos) - 3} more"
        elif event_type == "quality_report":
            detail = (
                f"{event.get('valid', '?')}/{event.get('skills', '?')} valid, "
                f"{event.get('over_budget', 0)} over budget, "
                f"{event.get('stale', 0)} stale"
            )
        else:
            detail = str(event)

        print(f"[{event_date}] {event_type}: {detail}")
