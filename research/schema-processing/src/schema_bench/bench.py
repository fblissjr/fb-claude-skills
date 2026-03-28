"""Benchmark orchestrator using hyperfine and /usr/bin/time."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import orjson

from schema_bench.generate import SIZE_TIERS

# Ensure cargo and go binaries are on PATH
_extra_paths = [
    os.path.expanduser("~/.cargo/bin"),
    os.path.expanduser("~/go/bin"),
]
for p in _extra_paths:
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + ":" + os.environ.get("PATH", "")
from schema_bench.queries import QUERIES, TOOLS, get_queries_for_schema, get_tool_cmd
from schema_bench.tools import check_tools


def _hyperfine_settings(size_name: str) -> tuple[int, int]:
    """Return (warmup, min_runs) based on file size tier."""
    if size_name in ("tiny", "small", "medium"):
        return 3, 10
    elif size_name == "large":
        return 2, 5
    else:  # xlarge
        return 1, 3


def run_benchmarks(
    data_dir: Path,
    results_dir: Path,
    sizes: list[str] | None = None,
    schemas: list[str] | None = None,
    queries: list[str] | None = None,
    tools: list[str] | None = None,
) -> list[Path]:
    """Run hyperfine benchmarks for all combinations.

    Returns list of result JSON file paths.
    """
    sizes = sizes or list(SIZE_TIERS.keys())
    schemas = schemas or ["flat", "nested", "deep", "array_heavy", "mixed", "wide", "real_world"]
    tools_to_test = tools or TOOLS
    query_filter = set(queries) if queries else None

    # Check tool availability
    available = check_tools()
    tools_to_test = [t for t in tools_to_test if available.get(t) is not None]
    if not tools_to_test:
        print("ERROR: No benchmark tools are installed.")
        return []

    raw_dir = results_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    result_files = []

    for schema in schemas:
        applicable_queries = get_queries_for_schema(schema)
        for query in applicable_queries:
            if query_filter and query.name not in query_filter:
                continue

            for size in sizes:
                data_file = data_dir / f"{schema}_{size}.json"
                if not data_file.exists():
                    print(f"  SKIP {schema}_{size}: data file not found")
                    continue

                warmup, min_runs = _hyperfine_settings(size)
                output_file = raw_dir / f"{query.name}__{schema}__{size}.json"

                # Build commands for each tool
                cmds = []
                cmd_names = []
                for tool in tools_to_test:
                    cmd = get_tool_cmd(query, tool, schema, str(data_file))
                    if cmd is not None:
                        cmds.append(cmd)
                        cmd_names.append(tool)

                if len(cmds) < 2:
                    # Need at least 2 tools to compare
                    if cmds:
                        print(f"  SKIP {query.name}/{schema}/{size}: only {cmd_names[0]} supports this")
                    continue

                print(f"  BENCH {query.name}/{schema}/{size} [{', '.join(cmd_names)}]")

                # Build hyperfine command
                hyperfine_cmd = [
                    "hyperfine",
                    "--warmup", str(warmup),
                    "--min-runs", str(min_runs),
                    "--export-json", str(output_file),
                    "--shell", "bash",
                ]
                for name, cmd in zip(cmd_names, cmds):
                    hyperfine_cmd.extend(["-n", name, cmd + " > /dev/null"])

                try:
                    proc = subprocess.run(
                        hyperfine_cmd,
                        capture_output=True,
                        text=True,
                        timeout=600,  # 10 min max per benchmark
                    )
                    if proc.returncode != 0:
                        print(f"    FAIL: {proc.stderr[:200]}")
                        continue
                    result_files.append(output_file)
                except subprocess.TimeoutExpired:
                    print(f"    TIMEOUT after 600s")
                    continue

    return result_files


def measure_memory(
    data_dir: Path,
    results_dir: Path,
    sizes: list[str] | None = None,
    schemas: list[str] | None = None,
) -> Path:
    """Measure peak RSS for a representative query per tool.

    Uses /usr/bin/time -v. Returns path to results CSV.
    """
    sizes = sizes or ["small", "medium", "large"]
    schemas = schemas or ["nested", "array_heavy", "real_world"]
    available = check_tools()
    tools_to_test = [t for t in TOOLS if available.get(t) is not None]

    # Use nested_path for nested, wildcard_array for array_heavy, geo_all_types for real_world
    representative_queries = {
        "nested": next(q for q in QUERIES if q.name == "nested_path"),
        "array_heavy": next(q for q in QUERIES if q.name == "wildcard_array"),
        "real_world": next(q for q in QUERIES if q.name == "geo_all_types"),
        "flat": next(q for q in QUERIES if q.name == "simple_field"),
        "deep": next(q for q in QUERIES if q.name == "deep_nested_path"),
        "mixed": next(q for q in QUERIES if q.name == "recursive_descent"),
        "wide": next(q for q in QUERIES if q.name == "simple_field"),
    }

    mem_dir = results_dir / "processed"
    mem_dir.mkdir(parents=True, exist_ok=True)
    csv_path = mem_dir / "memory_usage.csv"

    rows = ["tool,schema,size,peak_rss_kb,command"]
    for schema in schemas:
        query = representative_queries.get(schema)
        if not query:
            continue
        for size in sizes:
            data_file = data_dir / f"{schema}_{size}.json"
            if not data_file.exists():
                continue
            for tool in tools_to_test:
                cmd = get_tool_cmd(query, tool, schema, str(data_file))
                if cmd is None:
                    continue
                # Measure peak RSS via /proc or resource module
                try:
                    proc = subprocess.Popen(
                        cmd + " > /dev/null",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    peak_rss = 0
                    pid = proc.pid
                    while proc.poll() is None:
                        try:
                            status_path = f"/proc/{pid}/status"
                            with open(status_path) as f:
                                for line in f:
                                    if line.startswith("VmRSS:"):
                                        rss_kb = int(line.split()[1])
                                        peak_rss = max(peak_rss, rss_kb)
                                        break
                        except (FileNotFoundError, ProcessLookupError):
                            break
                    proc.wait(timeout=120)
                    if peak_rss > 0:
                        rows.append(f"{tool},{schema},{size},{peak_rss},{cmd[:80]}")
                        print(f"    MEM {tool}/{schema}/{size}: {peak_rss} KB")
                    else:
                        print(f"    MEM {tool}/{schema}/{size}: could not measure")
                except Exception as e:
                    print(f"    MEM FAIL {tool}/{schema}/{size}: {e}")

    csv_path.write_text("\n".join(rows) + "\n")
    return csv_path
