"""
AWM-1K catalog browser.

Downloads and indexes scenario metadata from Snowflake/AgentWorldModel-1K
on Hugging Face. Provides search by keyword and category listing.

Usage:
    uv run python env-forge/scripts/catalog.py --list-categories
    uv run python env-forge/scripts/catalog.py --search "e-commerce"
    uv run python env-forge/scripts/catalog.py --category "booking"
    uv run python env-forge/scripts/catalog.py --details marketplace_1
    uv run python env-forge/scripts/catalog.py --refresh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import orjson

REPO_ID = "Snowflake/AgentWorldModel-1K"
CACHE_DIR = Path(".env-forge/cache")
SCENARIO_FILE = "gen_scenario.jsonl"
TASKS_FILE = "gen_tasks.jsonl"
DB_FILE = "gen_db.jsonl"
SPEC_FILE = "gen_spec.jsonl"


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def download_file(filename: str, refresh: bool = False) -> Path:
    """Download a JSONL file from HF, caching locally."""
    cached = CACHE_DIR / filename
    if cached.exists() and not refresh:
        return cached

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Error: huggingface_hub not installed. Run: uv add huggingface_hub", file=sys.stderr)
        sys.exit(1)

    ensure_cache_dir()
    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        repo_type="dataset",
        local_dir=str(CACHE_DIR),
    )
    return Path(path)


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(orjson.loads(line))
    return records


def load_scenarios(refresh: bool = False) -> list[dict]:
    """Load all scenario records."""
    path = download_file(SCENARIO_FILE, refresh=refresh)
    return load_jsonl(path)


def load_tasks(refresh: bool = False) -> dict[str, list[str]]:
    """Load tasks indexed by scenario name."""
    path = download_file(TASKS_FILE, refresh=refresh)
    records = load_jsonl(path)
    return {r["scenario"]: r["tasks"] for r in records}


def extract_categories(scenarios: list[dict]) -> dict[str, list[dict]]:
    """Group scenarios by inferred category prefix."""
    import re

    categories: dict[str, list[dict]] = {}
    for s in scenarios:
        name = s["name"]
        m = re.match(r"(.+?)_\d+$", name)
        prefix = m.group(1) if m else name
        # Humanize: replace _ with space, title case
        cat = prefix.replace("_", " ").title()
        categories.setdefault(cat, []).append(s)
    return dict(sorted(categories.items()))


def search_scenarios(scenarios: list[dict], query: str) -> list[dict]:
    """Search scenarios by keyword in name and description."""
    query_lower = query.lower()
    terms = query_lower.split()
    results = []
    for s in scenarios:
        text = f"{s['name']} {s['description']}".lower()
        if all(t in text for t in terms):
            results.append(s)
    return results


def print_scenario_list(scenarios: list[dict], max_desc: int = 120) -> None:
    """Print a formatted list of scenarios."""
    for i, s in enumerate(scenarios, 1):
        desc = s["description"]
        if len(desc) > max_desc:
            desc = desc[: max_desc - 3] + "..."
        print(f"  {i:4d}. {s['name']}")
        print(f"        {desc}")
        print()


def print_scenario_details(scenario: dict, tasks: list[str] | None = None) -> None:
    """Print full details for a scenario."""
    print(f"Scenario: {scenario['name']}")
    print(f"{'=' * 60}")
    print()
    print(scenario["description"])
    print()
    if tasks:
        print(f"Tasks ({len(tasks)}):")
        for i, t in enumerate(tasks):
            print(f"  {i}. {t}")
        print()


def cmd_list_categories(args: argparse.Namespace) -> None:
    scenarios = load_scenarios(refresh=args.refresh)
    categories = extract_categories(scenarios)
    print(f"AWM-1K Catalog: {len(scenarios)} scenarios in {len(categories)} categories\n")
    for cat, items in categories.items():
        print(f"  {cat} ({len(items)})")
    print(f"\nTotal: {len(scenarios)} scenarios")


def cmd_search(args: argparse.Namespace) -> None:
    scenarios = load_scenarios(refresh=args.refresh)
    results = search_scenarios(scenarios, args.search)
    if not results:
        print(f"No scenarios matching '{args.search}'")
        return
    print(f"Found {len(results)} scenarios matching '{args.search}':\n")
    print_scenario_list(results)


def cmd_category(args: argparse.Namespace) -> None:
    scenarios = load_scenarios(refresh=args.refresh)
    # Search by partial category match
    query = args.category.lower()
    results = []
    for s in scenarios:
        prefix = s["name"].rsplit("_", 1)[0] if "_" in s["name"] else s["name"]
        cat = prefix.replace("_", " ").lower()
        if query in cat:
            results.append(s)
    if not results:
        print(f"No scenarios in category matching '{args.category}'")
        return
    print(f"Found {len(results)} scenarios in category '{args.category}':\n")
    print_scenario_list(results)


def cmd_details(args: argparse.Namespace) -> None:
    scenarios = load_scenarios(refresh=args.refresh)
    tasks_map = load_tasks(refresh=args.refresh)

    scenario = None
    for s in scenarios:
        if s["name"] == args.details:
            scenario = s
            break

    if not scenario:
        print(f"Scenario '{args.details}' not found")
        # Suggest close matches
        close = [s for s in scenarios if args.details.lower() in s["name"].lower()]
        if close:
            print(f"\nDid you mean one of these?")
            for s in close[:10]:
                print(f"  - {s['name']}")
        return

    tasks = tasks_map.get(args.details)
    print_scenario_details(scenario, tasks)

    # Try to show table/endpoint counts
    try:
        db_path = download_file(DB_FILE, refresh=args.refresh)
        db_records = load_jsonl(db_path)
        for r in db_records:
            if r["scenario"] == args.details:
                tables = r.get("db_schema", {}).get("tables", [])
                print(f"Tables: {len(tables)}")
                for t in tables:
                    print(f"  - {t['name']}")
                break
    except Exception:
        pass

    try:
        spec_path = download_file(SPEC_FILE, refresh=args.refresh)
        spec_records = load_jsonl(spec_path)
        for r in spec_records:
            if r["scenario"] == args.details:
                groups = r.get("api_spec", {}).get("api_groups", [])
                total_endpoints = sum(len(g.get("endpoints", [])) for g in groups)
                print(f"\nAPI Endpoints: {total_endpoints}")
                for g in groups:
                    print(f"  {g['group_name']}:")
                    for ep in g.get("endpoints", []):
                        print(f"    {ep['method']} {ep['path']} -- {ep.get('summary', '')}")
                break
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Browse AWM-1K catalog of tool environments"
    )
    parser.add_argument("--list-categories", action="store_true", help="List all categories")
    parser.add_argument("--search", type=str, help="Search scenarios by keyword")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--details", type=str, help="Show details for a scenario")
    parser.add_argument("--refresh", action="store_true", help="Force re-download from HF")
    args = parser.parse_args()

    if args.list_categories:
        cmd_list_categories(args)
    elif args.search:
        cmd_search(args)
    elif args.category:
        cmd_category(args)
    elif args.details:
        cmd_details(args)
    else:
        # Default: list categories
        cmd_list_categories(args)


if __name__ == "__main__":
    main()
