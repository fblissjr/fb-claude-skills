"""
Validate a generated environment for structural correctness.

Checks: required files exist, schema.sql parses, server.py has expected
imports, SQLite DB has expected tables, API spec has endpoints.

Usage:
    uv run python env-forge/scripts/validate_env.py .env-forge/environments/e_commerce_33/
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import orjson

REQUIRED_FILES = [
    "scenario.json",
    "schema.sql",
    "seed_data.sql",
    "api_spec.json",
    "server.py",
    "pyproject.toml",
]

OPTIONAL_FILES = [
    "verifiers.py",
]

DB_FILES = [
    "db/current.db",
    "db/initial.db",
]

SERVER_EXPECTED_IMPORTS = [
    "fastapi",
    "sqlalchemy",
    "pydantic",
]


def validate_files(env_dir: Path) -> list[str]:
    """Check that required files exist."""
    issues = []
    for f in REQUIRED_FILES:
        if not (env_dir / f).exists():
            issues.append(f"MISSING: {f}")
    for f in OPTIONAL_FILES:
        if not (env_dir / f).exists():
            issues.append(f"WARNING: {f} not present (optional)")
    for f in DB_FILES:
        if not (env_dir / f).exists():
            issues.append(f"MISSING: {f} (run materialize first)")
    return issues


def validate_scenario(env_dir: Path) -> list[str]:
    """Validate scenario.json structure."""
    issues = []
    path = env_dir / "scenario.json"
    if not path.exists():
        return ["scenario.json not found"]

    data = orjson.loads(path.read_bytes())
    if not data.get("name"):
        issues.append("scenario.json: missing 'name'")
    if not data.get("description"):
        issues.append("scenario.json: missing 'description'")
    tasks = data.get("tasks", [])
    if not tasks:
        issues.append("scenario.json: no tasks defined")
    else:
        for i, t in enumerate(tasks):
            if not isinstance(t, str) or len(t) < 10:
                issues.append(f"scenario.json: task {i} is too short or not a string")
    return issues


def validate_schema(env_dir: Path) -> list[str]:
    """Validate schema.sql can be parsed by SQLite."""
    issues = []
    path = env_dir / "schema.sql"
    if not path.exists():
        return ["schema.sql not found"]

    sql = path.read_text()
    if not sql.strip():
        return ["schema.sql is empty"]

    # Try to apply schema to in-memory DB
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql)
        # Count tables
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if not tables:
            issues.append("schema.sql: no tables created")
        else:
            table_names = [t[0] for t in tables]
            if len(table_names) < 2:
                issues.append(f"schema.sql: only {len(table_names)} table(s) -- expected 2+")
    except sqlite3.Error as e:
        issues.append(f"schema.sql: SQL error: {e}")
    finally:
        conn.close()

    return issues


def validate_api_spec(env_dir: Path) -> list[str]:
    """Validate api_spec.json structure."""
    issues = []
    path = env_dir / "api_spec.json"
    if not path.exists():
        return ["api_spec.json not found"]

    data = orjson.loads(path.read_bytes())
    groups = data.get("api_groups", [])
    if not groups:
        issues.append("api_spec.json: no api_groups")
        return issues

    endpoint_count = 0
    operation_ids = set()
    for g in groups:
        if not g.get("group_name"):
            issues.append("api_spec.json: group missing 'group_name'")
        endpoints = g.get("endpoints", [])
        for ep in endpoints:
            endpoint_count += 1
            op_id = ep.get("operation_id")
            if not op_id:
                issues.append(f"api_spec.json: endpoint {ep.get('path', '?')} missing operation_id")
            elif op_id in operation_ids:
                issues.append(f"api_spec.json: duplicate operation_id '{op_id}'")
            else:
                operation_ids.add(op_id)
            if not ep.get("path"):
                issues.append(f"api_spec.json: endpoint missing 'path'")
            if not ep.get("method"):
                issues.append(f"api_spec.json: endpoint {ep.get('path', '?')} missing 'method'")

    if endpoint_count == 0:
        issues.append("api_spec.json: no endpoints defined")

    return issues


def validate_server(env_dir: Path) -> list[str]:
    """Validate server.py has expected structure."""
    issues = []
    path = env_dir / "server.py"
    if not path.exists():
        return ["server.py not found"]

    code = path.read_text()
    if not code.strip():
        return ["server.py is empty"]

    for imp in SERVER_EXPECTED_IMPORTS:
        if imp not in code:
            issues.append(f"server.py: missing expected import '{imp}'")

    if "FastAPI(" not in code:
        issues.append("server.py: no FastAPI() app instantiation found")

    if "uvicorn" not in code:
        issues.append("server.py: no uvicorn reference (may not be runnable)")

    return issues


def validate_database(env_dir: Path) -> list[str]:
    """Validate the SQLite database has tables and data."""
    issues = []
    db_path = env_dir / "db" / "current.db"
    if not db_path.exists():
        return ["db/current.db not found"]

    conn = sqlite3.connect(str(db_path))
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        if not table_names:
            issues.append("db/current.db: no tables")
        else:
            empty_tables = []
            for tn in table_names:
                count = conn.execute(f'SELECT COUNT(*) FROM "{tn}"').fetchone()[0]
                if count == 0:
                    empty_tables.append(tn)
            if empty_tables:
                issues.append(
                    f"db/current.db: {len(empty_tables)} empty table(s): {', '.join(empty_tables[:5])}"
                )
    except sqlite3.Error as e:
        issues.append(f"db/current.db: error reading: {e}")
    finally:
        conn.close()

    return issues


def validate(env_dir: Path) -> bool:
    """Run all validations. Returns True if no errors (warnings ok)."""
    print(f"Validating: {env_dir}\n")

    all_issues = []

    checks = [
        ("Files", validate_files),
        ("Scenario", validate_scenario),
        ("Schema", validate_schema),
        ("API Spec", validate_api_spec),
        ("Server", validate_server),
        ("Database", validate_database),
    ]

    for name, check_fn in checks:
        issues = check_fn(env_dir)
        errors = [i for i in issues if not i.startswith("WARNING")]
        warnings = [i for i in issues if i.startswith("WARNING")]

        if not issues:
            print(f"  [PASS] {name}")
        elif not errors:
            print(f"  [WARN] {name}")
            for w in warnings:
                print(f"         {w}")
        else:
            print(f"  [FAIL] {name}")
            for i in issues:
                prefix = "    " if i.startswith("WARNING") else "  ! "
                print(f"       {prefix}{i}")

        all_issues.extend(issues)

    errors = [i for i in all_issues if not i.startswith("WARNING")]
    warnings = [i for i in all_issues if i.startswith("WARNING")]

    print()
    if not errors:
        print(f"Result: PASS ({len(warnings)} warning(s))")
        return True
    else:
        print(f"Result: FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a generated environment for structural correctness"
    )
    parser.add_argument(
        "env_dir",
        type=Path,
        help="Path to environment directory",
    )
    args = parser.parse_args()

    if not args.env_dir.is_dir():
        print(f"Error: {args.env_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    ok = validate(args.env_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
