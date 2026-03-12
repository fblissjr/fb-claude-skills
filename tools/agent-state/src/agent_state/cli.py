"""CLI entry point: agent-state."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from agent_state.database import AgentStateDB, DEFAULT_DB_PATH


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize the agent-state database."""
    db = AgentStateDB(args.db)
    print(f"Database initialized at {db.db_path}")
    print(f"Schema version: {db.schema_version()}")
    db.close()


def cmd_status(args: argparse.Namespace) -> None:
    """Show database status and summary statistics."""
    from agent_state.query import get_run_stats

    db = AgentStateDB(args.db)
    stats = get_run_stats(db)
    db.close()

    print(f"Database: {args.db or DEFAULT_DB_PATH}")
    print(f"Total runs: {stats['total_runs']}")
    print(f"Total messages: {stats['total_messages']}")
    print(f"Active watermarks: {stats['active_watermarks']}")
    print(f"Tracked skills: {stats['tracked_skills']}")
    if stats["by_status"]:
        print("\nBy status:")
        for status, count in stats["by_status"].items():
            print(f"  {status}: {count}")
    if stats["by_type"]:
        print("\nBy type:")
        for run_type, count in stats["by_type"].items():
            print(f"  {run_type}: {count}")


def cmd_runs(args: argparse.Namespace) -> None:
    """List recent runs."""
    from agent_state.query import get_recent_runs

    db = AgentStateDB(args.db)
    runs = get_recent_runs(db, limit=args.limit, run_type=args.type, status=args.status)
    db.close()

    if not runs:
        print("No runs found.")
        return

    for run in runs:
        status_indicator = {"success": "+", "failure": "!", "running": "~", "partial": "?"}.get(
            run["status"], " "
        )
        duration = f"{run['duration_ms']}ms" if run.get("duration_ms") else "---"
        print(f"  [{status_indicator}] {run['run_id'][:12]}  {run['run_name']:<25} "
              f"{run['status']:<10} {duration:>8}  {run['started_at']}")


def cmd_tree(args: argparse.Namespace) -> None:
    """Show hierarchical run tree."""
    from agent_state.query import get_run_tree

    db = AgentStateDB(args.db)
    tree = get_run_tree(db, args.run_id)
    db.close()

    if not tree:
        print("No runs found.")
        return

    for node in tree:
        indent = "  " * node.get("depth", 0)
        status = node["status"]
        duration = f"{node['duration_ms']}ms" if node.get("duration_ms") else "---"
        print(f"{indent}[{status}] {node['run_name']} ({node['run_id'][:12]}) {duration}")


def cmd_watermarks(args: argparse.Namespace) -> None:
    """Show current watermarks."""
    from agent_state.watermarks import get_all_watermarks

    db = AgentStateDB(args.db)
    watermarks = get_all_watermarks(db)
    db.close()

    if not watermarks:
        print("No watermarks tracked.")
        return

    for wm in watermarks:
        changed = "*" if wm.get("changed") else " "
        value = wm["current_value"][:16] if wm.get("current_value") else "---"
        name = wm.get("display_name", wm.get("identifier", "unknown"))
        print(f"  {changed} {name:<50} {value}  ({wm.get('checked_at', '')})")


def cmd_flywheel(args: argparse.Namespace) -> None:
    """Show flywheel view (producer -> skill -> consumer)."""
    from agent_state.query import get_flywheel

    db = AgentStateDB(args.db)
    flywheel = get_flywheel(db, args.skill)
    db.close()

    if not flywheel:
        print("No flywheel data.")
        return

    for row in flywheel:
        producer = row.get("producer_name", "---")
        consumer = row.get("consumer_name", "---")
        skill = row.get("skill_name", "unknown")
        print(f"  {producer:<25} -> [{skill}] -> {consumer}")


def cmd_migrate(args: argparse.Namespace) -> None:
    """Import data from skill-maintainer's changes.jsonl and upstream_hashes.json."""
    from agent_state.migration import migrate_from_jsonl

    db = AgentStateDB(args.db)
    counts = migrate_from_jsonl(db, args.dir, dry_run=args.dry_run)
    db.close()

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Migration complete:")
    print(f"  Runs imported: {counts['runs']}")
    print(f"  Watermarks imported: {counts['watermarks']}")
    print(f"  Skipped: {counts['skipped']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-state",
        description="DuckDB audit and state tracking for agent and pipeline runs",
    )
    parser.add_argument(
        "--db", type=Path, default=None,
        help=f"Database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize database")
    sub.add_parser("status", help="Show database status")

    runs_parser = sub.add_parser("runs", help="List recent runs")
    runs_parser.add_argument("-n", "--limit", type=int, default=20)
    runs_parser.add_argument("-t", "--type", help="Filter by run type")
    runs_parser.add_argument("-s", "--status", help="Filter by status")

    tree_parser = sub.add_parser("tree", help="Show run tree")
    tree_parser.add_argument("run_id", nargs="?", help="Root run ID (optional)")

    sub.add_parser("watermarks", help="Show current watermarks")

    flywheel_parser = sub.add_parser("flywheel", help="Show flywheel view")
    flywheel_parser.add_argument("--skill", help="Filter by skill name")

    migrate_parser = sub.add_parser("migrate", help="Import from changes.jsonl")
    migrate_parser.add_argument("--dir", type=Path, default=Path("."),
                                help="Repo directory with .skill-maintainer/state/")
    migrate_parser.add_argument("--dry-run", action="store_true",
                                help="Show what would be imported")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "init": cmd_init,
        "status": cmd_status,
        "runs": cmd_runs,
        "tree": cmd_tree,
        "watermarks": cmd_watermarks,
        "flywheel": cmd_flywheel,
        "migrate": cmd_migrate,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
