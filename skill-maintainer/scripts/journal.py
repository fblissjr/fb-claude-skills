#!/usr/bin/env python3
"""
Session activity journal for Claude Code hooks.

Two modes of operation:
1. APPEND (fast, for hooks): Append event to JSONL buffer file. No DuckDB import needed.
   This avoids the uv cold-start penalty for hooks that must complete in <500ms.

2. INGEST (batch): Read JSONL buffer and insert into DuckDB fact_session_event table.
   Run periodically or at session end.

3. QUERY: Show recent session activity from DuckDB.

Session boundaries are events (event_type='session_start'/'session_end'), not a
separate table. This eliminates the awkward FK from fact to fact.

Usage:
    # From a hook (fast path -- just appends to JSONL):
    echo '{"event_type":"file_modified","target_path":"foo.py"}' | \
        uv run python skill-maintainer/scripts/journal.py append --session-id abc123

    # Batch ingest JSONL into DuckDB:
    uv run python skill-maintainer/scripts/journal.py ingest

    # Query recent activity:
    uv run python skill-maintainer/scripts/journal.py query
    uv run python skill-maintainer/scripts/journal.py query --session abc123
    uv run python skill-maintainer/scripts/journal.py query --days 7
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import orjson

from store import Store


DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")
DEFAULT_CONFIG = Path("skill-maintainer/config.yaml")
DEFAULT_JOURNAL = Path("skill-maintainer/state/journal.jsonl")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# APPEND: fast path for hooks
# ---------------------------------------------------------------------------

def append_event(
    journal_path: Path,
    session_id: str,
    event_type: str,
    target_path: str = "",
    metadata: dict | None = None,
) -> None:
    """Append a single event to the JSONL buffer. Fast, no DB access."""
    event = {
        "session_id": session_id,
        "event_type": event_type,
        "event_at": _now_iso(),
        "target_path": target_path,
    }
    if metadata:
        event["metadata"] = metadata

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with open(journal_path, "ab") as f:
        f.write(orjson.dumps(event))
        f.write(b"\n")


def append_from_stdin(journal_path: Path, session_id: str) -> None:
    """Read JSON event from stdin and append to journal."""
    data = sys.stdin.buffer.read()
    if not data.strip():
        return

    try:
        event = orjson.loads(data)
    except Exception:
        # Not valid JSON, treat as raw event
        event = {"raw": data.decode(errors="replace").strip()}

    append_event(
        journal_path,
        session_id=session_id,
        event_type=event.get("event_type", "unknown"),
        target_path=event.get("target_path", ""),
        metadata=event.get("metadata"),
    )


# ---------------------------------------------------------------------------
# INGEST: batch import JSONL into DuckDB
# ---------------------------------------------------------------------------

def ingest_journal(
    journal_path: Path,
    store: Store,
) -> int:
    """Read JSONL buffer and insert into DuckDB. Returns count of events ingested."""
    if not journal_path.exists():
        return 0

    count = 0
    events = []

    with open(journal_path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = orjson.loads(line)
                events.append(event)
            except Exception:
                continue

    if not events:
        return 0

    store.log_load_start("journal_ingest")

    # Insert events directly -- session boundaries are just events now
    for event in events:
        sid = event.get("session_id", "")
        if not sid:
            continue
        store.record_session_event(
            session_id=sid,
            event_type=event.get("event_type", "unknown"),
            target_path=event.get("target_path", ""),
            metadata=event.get("metadata"),
            record_source="journal",
        )
        count += 1

    store.log_load_end("journal_ingest", rows_inserted=count)

    # Truncate the journal file after successful ingest
    journal_path.write_bytes(b"")

    return count


# ---------------------------------------------------------------------------
# QUERY: show recent activity
# ---------------------------------------------------------------------------

def query_activity(
    store: Store,
    session_id: str | None = None,
    days: int = 7,
    limit: int = 50,
) -> list[dict]:
    """Query recent session activity from DuckDB."""
    params: list = []
    query = """
        SELECT e.event_at, e.session_id, e.event_type, e.target_path, e.metadata
        FROM fact_session_event e
        WHERE e.event_at >= current_timestamp - INTERVAL (? || ' days')
    """
    params.append(days)

    if session_id:
        query += " AND e.session_id = ?"
        params.append(session_id)

    query += " ORDER BY e.event_at DESC LIMIT ?"
    params.append(limit)

    rows = store.con.execute(query, params).fetchall()
    results = []
    for row in rows:
        results.append({
            "event_at": row[0].isoformat() if row[0] else "",
            "session_id": row[1] or "",
            "event_type": row[2] or "",
            "target_path": row[3] or "",
            "metadata": row[4] or "",
        })
    return results


def print_activity(events: list[dict]) -> None:
    """Format and print activity events."""
    if not events:
        print("No recent activity.")
        return

    print(f"# Recent Activity ({len(events)} events)")
    print()
    for e in events:
        ts = e["event_at"][:19] if e["event_at"] else "?"
        etype = e["event_type"]
        target = e["target_path"]
        line = f"  {ts}  [{etype}]"
        if target:
            line += f"  {target}"
        print(line)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Session activity journal for Claude Code."
    )
    subparsers = parser.add_subparsers(dest="command")

    # append subcommand
    append_p = subparsers.add_parser(
        "append", help="Append event to JSONL buffer (fast, for hooks)",
    )
    append_p.add_argument("--session-id", required=True)
    append_p.add_argument("--event-type", default=None)
    append_p.add_argument("--target-path", default="")
    append_p.add_argument(
        "--journal", type=Path, default=DEFAULT_JOURNAL,
    )

    # ingest subcommand
    ingest_p = subparsers.add_parser(
        "ingest", help="Batch-import JSONL buffer into DuckDB",
    )
    ingest_p.add_argument(
        "--journal", type=Path, default=DEFAULT_JOURNAL,
    )
    ingest_p.add_argument("--db", type=Path, default=DEFAULT_DB)
    ingest_p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    # query subcommand
    query_p = subparsers.add_parser(
        "query", help="Query recent session activity",
    )
    query_p.add_argument("--session", type=str, default=None)
    query_p.add_argument("--days", type=int, default=7)
    query_p.add_argument("--limit", type=int, default=50)
    query_p.add_argument("--db", type=Path, default=DEFAULT_DB)
    query_p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    args = parser.parse_args()

    if args.command == "append":
        if args.event_type:
            # Direct append from CLI args
            append_event(
                args.journal,
                session_id=args.session_id,
                event_type=args.event_type,
                target_path=args.target_path,
            )
        else:
            # Read from stdin
            append_from_stdin(args.journal, args.session_id)

    elif args.command == "ingest":
        with Store(db_path=args.db, config_path=args.config) as store:
            count = ingest_journal(args.journal, store)
            print(f"Ingested {count} events into DuckDB.", file=sys.stderr)

    elif args.command == "query":
        with Store(db_path=args.db, config_path=args.config) as store:
            events = query_activity(store, args.session, args.days, args.limit)
            print_activity(events)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
