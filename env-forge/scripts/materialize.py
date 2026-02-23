"""
Materialize an AWM-1K scenario into a runnable environment.

Fetches scenario data from Snowflake/AgentWorldModel-1K on HF,
writes server.py, schema.sql, seed_data.sql, creates SQLite DB.

Usage:
    uv run python env-forge/scripts/materialize.py --scenario e_commerce_33
    uv run python env-forge/scripts/materialize.py --scenario marketplace_1 --output-dir /tmp/envs
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import orjson

REPO_ID = "Snowflake/AgentWorldModel-1K"
CACHE_DIR = Path(".env-forge/cache")
DEFAULT_OUTPUT_BASE = Path(".env-forge/environments")

JSONL_FILES = [
    "gen_scenario.jsonl",
    "gen_tasks.jsonl",
    "gen_db.jsonl",
    "gen_sample.jsonl",
    "gen_spec.jsonl",
    "gen_envs.jsonl",
    "gen_verifier.jsonl",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(filename: str) -> Path:
    """Download a JSONL file from HF, caching locally."""
    cached = CACHE_DIR / filename
    if cached.exists():
        return cached

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Error: huggingface_hub not installed. Run: uv add huggingface_hub", file=sys.stderr)
        sys.exit(1)

    ensure_dir(CACHE_DIR)
    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        repo_type="dataset",
        local_dir=str(CACHE_DIR),
    )
    return Path(path)


def find_record(path: Path, scenario: str, key: str = "scenario") -> dict | None:
    """Find a record matching the scenario name in a JSONL file."""
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = orjson.loads(line)
            # gen_scenario.jsonl uses "name", others use "scenario"
            record_key = record.get(key) or record.get("name")
            if record_key == scenario:
                return record
    return None


def find_all_records(path: Path, scenario: str, key: str = "scenario") -> list[dict]:
    """Find all records matching the scenario name (e.g., verifiers have multiple)."""
    results = []
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = orjson.loads(line)
            record_key = record.get(key) or record.get("name")
            if record_key == scenario:
                results.append(record)
    return results


def materialize(scenario_name: str, output_base: Path) -> Path:
    """Materialize a scenario into a runnable environment directory."""
    output_dir = output_base / scenario_name
    if output_dir.exists():
        print(f"Environment already exists: {output_dir}")
        print("Delete it first to re-materialize.")
        sys.exit(1)

    print(f"Downloading dataset files from {REPO_ID}...")
    paths = {}
    for f in JSONL_FILES:
        print(f"  {f}...", end=" ", flush=True)
        paths[f] = download_file(f)
        print("ok")

    # --- Fetch scenario ---
    print(f"\nLooking up scenario: {scenario_name}")
    scenario_rec = find_record(paths["gen_scenario.jsonl"], scenario_name, key="name")
    if not scenario_rec:
        print(f"Error: Scenario '{scenario_name}' not found in catalog.")
        sys.exit(1)

    # --- Fetch tasks ---
    tasks_rec = find_record(paths["gen_tasks.jsonl"], scenario_name)
    tasks = tasks_rec["tasks"] if tasks_rec else []

    # --- Fetch DB schema ---
    db_rec = find_record(paths["gen_db.jsonl"], scenario_name)
    if not db_rec:
        print(f"Error: No database schema found for '{scenario_name}'")
        sys.exit(1)

    db_schema = db_rec.get("db_schema", {})
    tables = db_schema.get("tables", [])

    # --- Fetch sample data ---
    sample_rec = find_record(paths["gen_sample.jsonl"], scenario_name)
    sample_data = sample_rec.get("sample_data", {}) if sample_rec else {}

    # --- Fetch API spec ---
    spec_rec = find_record(paths["gen_spec.jsonl"], scenario_name)
    api_spec = spec_rec.get("api_spec", {}) if spec_rec else {}

    # --- Fetch server code ---
    env_rec = find_record(paths["gen_envs.jsonl"], scenario_name)
    server_code = env_rec.get("full_code", "") if env_rec else ""

    # --- Fetch verifiers ---
    verifier_recs = find_all_records(paths["gen_verifier.jsonl"], scenario_name)

    # --- Create output directory ---
    print(f"\nMaterializing to: {output_dir}")
    ensure_dir(output_dir)
    ensure_dir(output_dir / "db")

    # --- Write scenario.json ---
    scenario_json = {
        "name": scenario_name,
        "description": scenario_rec["description"],
        "tasks": tasks,
    }
    (output_dir / "scenario.json").write_bytes(
        orjson.dumps(scenario_json, option=orjson.OPT_INDENT_2)
    )
    print("  scenario.json")

    # --- Write schema.sql ---
    schema_lines = []
    for t in tables:
        schema_lines.append(t["ddl"])
        for idx in t.get("indexes", []):
            schema_lines.append(idx)
        schema_lines.append("")
    schema_sql = "\n".join(schema_lines)
    (output_dir / "schema.sql").write_text(schema_sql)
    print(f"  schema.sql ({len(tables)} tables)")

    # --- Write seed_data.sql ---
    seed_lines = []
    sample_tables = sample_data.get("tables", [])
    for st in sample_tables:
        seed_lines.append(f"-- {st['table_name']}")
        for stmt in st.get("insert_statements", []):
            seed_lines.append(stmt)
        seed_lines.append("")
    seed_sql = "\n".join(seed_lines)
    (output_dir / "seed_data.sql").write_text(seed_sql)
    insert_count = sum(len(st.get("insert_statements", [])) for st in sample_tables)
    print(f"  seed_data.sql ({insert_count} inserts)")

    # --- Write api_spec.json ---
    (output_dir / "api_spec.json").write_bytes(
        orjson.dumps(api_spec, option=orjson.OPT_INDENT_2)
    )
    endpoint_count = sum(
        len(g.get("endpoints", [])) for g in api_spec.get("api_groups", [])
    )
    print(f"  api_spec.json ({endpoint_count} endpoints)")

    # --- Write server.py ---
    if server_code:
        (output_dir / "server.py").write_text(server_code)
        print("  server.py")
    else:
        print("  server.py -- MISSING (no server code in dataset)")

    # --- Write verifiers.py ---
    if verifier_recs:
        verifier_lines = [
            '"""Task verification functions for ' + scenario_name + '."""',
            "",
            "import sqlite3",
            "",
        ]
        for vrec in sorted(verifier_recs, key=lambda r: r.get("task_idx", 0)):
            idx = vrec.get("task_idx", 0)
            task = vrec.get("task", "")
            code = vrec.get("verification", {}).get("code", "")
            if code:
                verifier_lines.append(f"# Task {idx}: {task[:80]}")
                verifier_lines.append(code)
                verifier_lines.append("")
        (output_dir / "verifiers.py").write_text("\n".join(verifier_lines))
        print(f"  verifiers.py ({len(verifier_recs)} verifiers)")
    else:
        print("  verifiers.py -- MISSING (no verifier code in dataset)")

    # --- Write pyproject.toml ---
    pyproject = f"""[project]
name = "env-forge-{scenario_name.replace('_', '-')}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "sqlalchemy>=2.0.0",
    "fastapi-mcp>=0.3.0",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
    (output_dir / "pyproject.toml").write_text(pyproject)
    print("  pyproject.toml")

    # --- Create and seed SQLite database ---
    print("\nCreating SQLite database...")
    db_path = output_dir / "db" / "current.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    # Apply schema
    try:
        conn.executescript(schema_sql)
        print(f"  Schema applied ({len(tables)} tables)")
    except sqlite3.Error as e:
        print(f"  Schema error: {e}")
        print("  Attempting table-by-table creation...")
        for t in tables:
            try:
                conn.execute(t["ddl"])
                for idx in t.get("indexes", []):
                    conn.execute(idx)
            except sqlite3.Error as te:
                print(f"    Warning: {t['name']}: {te}")
        conn.commit()

    # Apply seed data
    errors = 0
    for st in sample_tables:
        for stmt in st.get("insert_statements", []):
            try:
                conn.execute(stmt)
            except sqlite3.Error:
                errors += 1
    conn.commit()
    conn.close()
    print(f"  Seed data applied ({insert_count - errors}/{insert_count} inserts)")
    if errors:
        print(f"  {errors} insert(s) failed (likely FK constraint issues)")

    # Copy to initial.db as backup
    import shutil

    shutil.copy2(str(db_path), str(output_dir / "db" / "initial.db"))
    print("  Copied to initial.db (backup)")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"Environment materialized: {output_dir}")
    print(f"  Tables: {len(tables)}")
    print(f"  Endpoints: {endpoint_count}")
    print(f"  Tasks: {len(tasks)}")
    print(f"  Verifiers: {len(verifier_recs)}")
    print(f"\nTo start:")
    print(f"  cd {output_dir} && uv run python server.py")
    print(f"\nMCP endpoint: http://127.0.0.1:8000/mcp")

    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize an AWM-1K scenario into a runnable environment"
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help="Scenario name from the AWM-1K catalog (e.g., e_commerce_33)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_BASE,
        help=f"Base output directory (default: {DEFAULT_OUTPUT_BASE})",
    )
    args = parser.parse_args()

    materialize(args.scenario, args.output_dir)


if __name__ == "__main__":
    main()
