"""Parse benchmark results and compute analysis."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import orjson

from schema_bench.generate import SIZE_TIERS


@dataclass
class BenchResult:
    query: str
    schema: str
    size: str
    tool: str
    mean_s: float
    stddev_s: float
    median_s: float
    min_s: float
    max_s: float
    file_size_bytes: int = 0
    throughput_mbs: float = 0.0


def parse_hyperfine_results(raw_dir: Path) -> list[BenchResult]:
    """Parse all hyperfine JSON output files into BenchResult list."""
    results = []
    for json_file in sorted(raw_dir.glob("*.json")):
        # Filename format: {query}__{schema}__{size}.json
        parts = json_file.stem.split("__")
        if len(parts) != 3:
            continue
        query_name, schema, size = parts

        raw = json_file.read_bytes()
        if not raw.strip():
            continue
        data = orjson.loads(raw)
        file_size = SIZE_TIERS.get(size, 0)

        for entry in data.get("results", []):
            tool = entry.get("command", "unknown")
            # hyperfine -n sets the command name
            # Check if there's a "parameter" or use command
            tool_name = entry.get("command", "")
            # When using -n flag, hyperfine stores name differently
            mean = entry.get("mean", 0)
            stddev = entry.get("stddev", 0)
            median = entry.get("median", 0)
            min_val = entry.get("min", 0)
            max_val = entry.get("max", 0)

            throughput = (file_size / median / 1_000_000) if median > 0 and file_size > 0 else 0

            results.append(BenchResult(
                query=query_name,
                schema=schema,
                size=size,
                tool=tool_name,
                mean_s=mean,
                stddev_s=stddev,
                median_s=median,
                min_s=min_val,
                max_s=max_val,
                file_size_bytes=file_size,
                throughput_mbs=throughput,
            ))

    return results


def results_to_csv(results: list[BenchResult], output_path: Path) -> None:
    """Write results to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query", "schema", "size", "tool",
            "mean_s", "stddev_s", "median_s", "min_s", "max_s",
            "file_size_bytes", "throughput_mbs",
        ])
        for r in results:
            writer.writerow([
                r.query, r.schema, r.size, r.tool,
                f"{r.mean_s:.6f}", f"{r.stddev_s:.6f}", f"{r.median_s:.6f}",
                f"{r.min_s:.6f}", f"{r.max_s:.6f}",
                r.file_size_bytes, f"{r.throughput_mbs:.2f}",
            ])


def compute_speedup_table(results: list[BenchResult]) -> dict[str, dict[str, float]]:
    """Compute speedup of jg vs each other tool per query pattern.

    Returns {query: {tool: speedup_factor}} where >1 means jg is faster.
    """
    # Group by (query, schema, size)
    groups: dict[tuple, dict[str, float]] = {}
    for r in results:
        key = (r.query, r.schema, r.size)
        if key not in groups:
            groups[key] = {}
        groups[key][r.tool] = r.median_s

    # Compute per-query average speedups
    query_speedups: dict[str, dict[str, list[float]]] = {}
    for (query, schema, size), tool_times in groups.items():
        jg_time = tool_times.get("jg")
        if jg_time is None or jg_time == 0:
            continue
        if query not in query_speedups:
            query_speedups[query] = {}
        for tool, time in tool_times.items():
            if tool == "jg":
                continue
            if tool not in query_speedups[query]:
                query_speedups[query][tool] = []
            query_speedups[query][tool].append(time / jg_time)

    # Average speedups
    return {
        query: {tool: sum(vals) / len(vals) for tool, vals in tools.items()}
        for query, tools in query_speedups.items()
    }


def compute_scaling_analysis(results: list[BenchResult]) -> dict[str, dict[str, list[tuple[int, float]]]]:
    """Group results by (query, tool) with (file_size, median_time) pairs for scaling analysis.

    Returns {query: {tool: [(file_size, median_s), ...]}}.
    """
    scaling: dict[str, dict[str, list[tuple[int, float]]]] = {}
    for r in results:
        if r.query not in scaling:
            scaling[r.query] = {}
        if r.tool not in scaling[r.query]:
            scaling[r.query][r.tool] = []
        scaling[r.query][r.tool].append((r.file_size_bytes, r.median_s))

    # Sort by file size
    for query in scaling:
        for tool in scaling[query]:
            scaling[query][tool].sort()

    return scaling
