#!/usr/bin/env python3
"""
One-time migration: import existing state.json into DuckDB store.

Reads state.json, populates the DuckDB database (v2 Kimball schema),
then verifies that export_state_json() produces equivalent output.

Usage:
    uv run python skill-maintainer/scripts/migrate_state.py
    uv run python skill-maintainer/scripts/migrate_state.py --verify-only
"""

import argparse
import sys
from pathlib import Path

import orjson

from store import Store


DEFAULT_STATE = Path("skill-maintainer/state/state.json")
DEFAULT_DB = Path("skill-maintainer/state/skill_store.duckdb")


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        print(f"State file not found: {state_path}", file=sys.stderr)
        return {}
    data = state_path.read_bytes()
    if not data or data.strip() == b"{}":
        return {}
    return orjson.loads(data)


def compare_states(original: dict, exported: dict) -> list[str]:
    """Compare original state.json with exported version. Returns list of differences."""
    diffs = []

    # Compare docs section
    orig_docs = original.get("docs", {})
    exp_docs = exported.get("docs", {})

    for source_name in set(list(orig_docs.keys()) + list(exp_docs.keys())):
        orig_src = orig_docs.get(source_name, {})
        exp_src = exp_docs.get(source_name, {})

        # Compare watermark
        orig_wm = orig_src.get("_watermark", {})
        exp_wm = exp_src.get("_watermark", {})
        if orig_wm.get("last_modified") and not exp_wm:
            diffs.append(f"docs.{source_name}._watermark: missing in export")
        elif orig_wm.get("last_modified") != exp_wm.get("last_modified"):
            diffs.append(
                f"docs.{source_name}._watermark.last_modified: "
                f"'{orig_wm.get('last_modified')}' vs '{exp_wm.get('last_modified')}'"
            )

        # Compare pages (hash values)
        orig_pages = orig_src.get("_pages", {})
        exp_pages = exp_src.get("_pages", {})
        for url in set(list(orig_pages.keys()) + list(exp_pages.keys())):
            orig_hash = orig_pages.get(url, {}).get("hash", "")
            exp_hash = exp_pages.get(url, {}).get("hash", "")
            if orig_hash != exp_hash:
                diffs.append(
                    f"docs.{source_name}._pages.{url}.hash: "
                    f"'{orig_hash[:12]}' vs '{exp_hash[:12]}'"
                )

        # Compare file hash
        orig_fh = orig_src.get("_file_hash", "")
        exp_fh = exp_src.get("_file_hash", "")
        if orig_fh != exp_fh:
            diffs.append(
                f"docs.{source_name}._file_hash: '{orig_fh[:12]}' vs '{exp_fh[:12]}'"
            )

    # Compare sources section
    orig_sources = original.get("sources", {})
    exp_sources = exported.get("sources", {})
    for source_name in set(list(orig_sources.keys()) + list(exp_sources.keys())):
        orig_src = orig_sources.get(source_name, {})
        exp_src = exp_sources.get(source_name, {})
        if orig_src.get("last_commit") != exp_src.get("last_commit"):
            diffs.append(
                f"sources.{source_name}.last_commit: "
                f"'{orig_src.get('last_commit')}' vs '{exp_src.get('last_commit')}'"
            )

    return diffs


def main():
    parser = argparse.ArgumentParser(
        description="Migrate state.json to DuckDB store (v2 Kimball schema)."
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE,
        help=f"Path to state.json (default: {DEFAULT_STATE})",
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help=f"Path to DuckDB file (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only verify export matches original, don't import",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-import even if DB already has data",
    )
    args = parser.parse_args()

    original_state = load_state(args.state)
    if not original_state:
        print("No state data to migrate.", file=sys.stderr)
        sys.exit(0)

    # Delete existing DB file if --force to get clean v2 schema
    if args.force and args.db.exists():
        args.db.unlink()
        wal = args.db.with_suffix(".duckdb.wal")
        if wal.exists():
            wal.unlink()

    with Store(db_path=args.db) as store:
        if args.verify_only:
            exported = store.export_state_json()
            diffs = compare_states(original_state, exported)
            if diffs:
                print("Differences found:", file=sys.stderr)
                for d in diffs:
                    print(f"  - {d}", file=sys.stderr)
                sys.exit(1)
            else:
                print("Export matches original state.json")
                sys.exit(0)

        # Check if already has data
        row = store.con.execute("SELECT COUNT(*) FROM fact_change").fetchone()
        existing_count = row[0] if row else 0
        if existing_count > 0 and not args.force:
            print(
                f"DB already has {existing_count} change records. "
                "Use --force to re-import.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Import
        store.log_load_start("migrate_state")
        print("Importing state.json into DuckDB (v2 schema)...", file=sys.stderr)
        summary = store.import_state_json(original_state)
        total = sum(summary.values())
        store.log_load_end("migrate_state", rows_inserted=total)

        print(f"  Watermarks imported: {summary['watermarks']}", file=sys.stderr)
        print(f"  Pages imported: {summary['pages']}", file=sys.stderr)
        print(f"  File hashes imported: {summary['file_hashes']}", file=sys.stderr)
        print(f"  Source checks imported: {summary['source_checks']}", file=sys.stderr)

        # Verify
        exported = store.export_state_json()
        diffs = compare_states(original_state, exported)
        if diffs:
            print("\nVerification found differences:", file=sys.stderr)
            for d in diffs:
                print(f"  - {d}", file=sys.stderr)
            print(
                "\nNote: timestamp differences are expected since import uses "
                "the original timestamps from state.json.",
                file=sys.stderr,
            )
        else:
            print("\nVerification passed: export matches original state.json",
                  file=sys.stderr)

        store.print_stats()


if __name__ == "__main__":
    main()
