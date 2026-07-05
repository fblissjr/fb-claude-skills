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


def cmd_delegation(args: argparse.Namespace) -> None:
    """Record or report down-tier delegation outcomes."""
    from agent_state.delegations import (
        get_delegation_stats,
        get_recent_delegations,
        record_delegation,
    )

    db = AgentStateDB(args.db)
    try:
        if args.delegation_command == "record":
            key = record_delegation(
                db,
                task_summary=args.task,
                model_name=args.model,
                outcome=args.outcome,
                task_domain=args.domain,
                verification=args.verification,
                orchestrator_model=args.orchestrator_model,
                session_id=args.session_id,
                run_id=args.run_id,
            )
            print(f"Recorded delegation {key[:12]} ({args.model} -> {args.outcome})")
        elif args.delegation_command == "stats":
            stats = get_delegation_stats(db, model_name=args.model, task_domain=args.domain)
            if not stats:
                print("No delegations recorded.")
                return
            print(f"  {'model':<10} {'domain':<12} {'n':>4} {'accept':>7} {'revise':>7} "
                  f"{'redo':>5} {'escal':>6} {'rate':>6}")
            for s in stats:
                print(f"  {s['model_name']:<10} {s['task_domain'] or '---':<12} "
                      f"{s['delegations']:>4} {s['accepted']:>7} {s['revised']:>7} "
                      f"{s['redone']:>5} {s['escalated']:>6} {s['acceptance_rate']:>6}")
        else:
            delegations = get_recent_delegations(db, limit=args.limit)
            if not delegations:
                print("No delegations recorded.")
                return
            for d in delegations:
                print(f"  [{d['outcome']:<9}] {d['model_name']:<8} "
                      f"{d['task_summary'][:50]:<50} {d['recorded_at']}")
    finally:
        db.close()


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

    delegation_parser = sub.add_parser(
        "delegation", help="Record or report down-tier delegation outcomes"
    )
    delegation_sub = delegation_parser.add_subparsers(dest="delegation_command")
    record_parser = delegation_sub.add_parser("record", help="Record one delegation outcome")
    record_parser.add_argument("--task", required=True, help="Short task summary")
    record_parser.add_argument("--model", required=True, help="Model tier delegated to")
    record_parser.add_argument(
        "--outcome", required=True,
        choices=["accepted", "revised", "redone", "escalated"],
    )
    record_parser.add_argument("--domain", help="Task domain (coding, data, docs, ...)")
    record_parser.add_argument(
        "--verification",
        help="How the result was verified (tests, diff_review, schema_validation, spot_check, none)",
    )
    record_parser.add_argument("--orchestrator-model", help="Model tier that delegated")
    record_parser.add_argument("--session-id", help="Session identifier")
    record_parser.add_argument("--run-id", help="Associated fact_run run_id")
    stats_parser = delegation_sub.add_parser("stats", help="Acceptance rates per model/domain")
    stats_parser.add_argument("--model", help="Filter by model tier")
    stats_parser.add_argument("--domain", help="Filter by task domain")
    list_parser = delegation_sub.add_parser("list", help="Recent delegation records")
    list_parser.add_argument("-n", "--limit", type=int, default=20)

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
        "delegation": cmd_delegation,
        "migrate": cmd_migrate,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
