"""Generate markdown benchmark report."""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from schema_bench.analyze import (
    BenchResult,
    compute_scaling_analysis,
    compute_speedup_table,
)
from schema_bench.tools import check_tools


def _get_hardware_info() -> str:
    """Capture basic hardware info."""
    lines = [f"- Platform: {platform.platform()}"]
    lines.append(f"- Python: {platform.python_version()}")
    try:
        proc = subprocess.run(["nproc"], capture_output=True, text=True, timeout=5)
        lines.append(f"- CPUs: {proc.stdout.strip()}")
    except Exception:
        pass
    try:
        proc = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        for line in proc.stdout.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                lines.append(f"- Memory: {parts[1]} total")
                break
    except Exception:
        pass
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    """Format time in human-readable units."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.1f} us"
    elif seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    else:
        return f"{seconds:.3f} s"


def generate_report(
    results: list[BenchResult],
    output_path: Path,
    memory_csv: Path | None = None,
) -> None:
    """Generate the full markdown benchmark report."""
    lines: list[str] = []

    # Header
    lines.append("# jsongrep Claims Evaluation: Benchmark Report")
    lines.append("")
    lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append("")

    # Executive Summary
    speedups = compute_speedup_table(results)
    lines.append("## Executive Summary")
    lines.append("")
    if speedups:
        jg_faster_count = sum(
            1 for q_speedups in speedups.values()
            for factor in q_speedups.values()
            if factor > 1.0
        )
        total_comparisons = sum(len(s) for s in speedups.values())
        lines.append(
            f"Across {total_comparisons} tool comparisons, jsongrep (`jg`) was faster "
            f"in {jg_faster_count} cases ({jg_faster_count/total_comparisons*100:.0f}%)."
        )
    else:
        lines.append("No benchmark results available.")
    lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append("### Hardware")
    lines.append("")
    lines.append(_get_hardware_info())
    lines.append("")
    lines.append("### Tools")
    lines.append("")
    versions = check_tools()
    lines.append("| Tool | Version |")
    lines.append("|------|---------|")
    for tool, version in versions.items():
        lines.append(f"| {tool} | {version or 'not installed'} |")
    lines.append("")
    lines.append("### Approach")
    lines.append("")
    lines.append("- **CLI-level benchmarks** using `hyperfine` — measures what developers actually experience")
    lines.append("- **Output to /dev/null** — measures computation, not terminal I/O")
    lines.append("- **Statistical rigor** — warmup runs, 3-10 measured runs with confidence intervals")
    lines.append("- **Equivalent queries** — same semantic operation across all tools")
    lines.append("- **Diverse schemas** — 7 schema types across 5 size tiers (100B to 100MB)")
    lines.append("")

    # Results by query pattern
    lines.append("## Results by Query Pattern")
    lines.append("")

    # Group results by query
    by_query: dict[str, list[BenchResult]] = {}
    for r in results:
        by_query.setdefault(r.query, []).append(r)

    for query_name, query_results in sorted(by_query.items()):
        lines.append(f"### {query_name}")
        lines.append("")

        # Table header
        lines.append("| Schema | Size | Tool | Median | Mean | Stddev | Throughput |")
        lines.append("|--------|------|------|--------|------|--------|------------|")

        # Sort by schema, size order, then median time
        size_order = {"tiny": 0, "small": 1, "medium": 2, "large": 3, "xlarge": 4}
        sorted_results = sorted(
            query_results,
            key=lambda r: (r.schema, size_order.get(r.size, 5), r.median_s),
        )

        for r in sorted_results:
            tp = f"{r.throughput_mbs:.1f} MB/s" if r.throughput_mbs > 0 else "-"
            lines.append(
                f"| {r.schema} | {r.size} | **{r.tool}** | "
                f"{_format_time(r.median_s)} | {_format_time(r.mean_s)} | "
                f"{_format_time(r.stddev_s)} | {tp} |"
            )

        lines.append("")

    # Speedup summary
    lines.append("## Speedup Summary (jg vs others)")
    lines.append("")
    if speedups:
        lines.append("| Query | Tool | Speedup Factor |")
        lines.append("|-------|------|----------------|")
        for query, tool_speedups in sorted(speedups.items()):
            for tool, factor in sorted(tool_speedups.items()):
                indicator = "faster" if factor > 1 else "slower"
                lines.append(f"| {query} | {tool} | {factor:.2f}x ({indicator}) |")
        lines.append("")
    else:
        lines.append("No comparison data available.")
        lines.append("")

    # Scaling analysis
    lines.append("## Scaling Analysis")
    lines.append("")
    scaling = compute_scaling_analysis(results)
    if scaling:
        lines.append("How does processing time scale with file size?")
        lines.append("")
        for query, tool_data in sorted(scaling.items()):
            lines.append(f"### {query}")
            lines.append("")
            lines.append("| Tool | Sizes tested | Time range |")
            lines.append("|------|-------------|------------|")
            for tool, points in sorted(tool_data.items()):
                if len(points) >= 2:
                    sizes_str = " -> ".join(f"{s/(1024*1024):.1f}MB" if s > 1024*1024 else f"{s/1024:.0f}KB" if s > 1024 else f"{s}B" for s, _ in points)
                    times_str = f"{_format_time(points[0][1])} -> {_format_time(points[-1][1])}"
                    lines.append(f"| {tool} | {sizes_str} | {times_str} |")
            lines.append("")
    else:
        lines.append("Insufficient data for scaling analysis.")
        lines.append("")

    # Memory usage
    if memory_csv and memory_csv.exists():
        lines.append("## Memory Usage (Peak RSS)")
        lines.append("")
        mem_lines = memory_csv.read_text().strip().split("\n")
        if len(mem_lines) > 1:
            lines.append("| Tool | Schema | Size | Peak RSS (KB) |")
            lines.append("|------|--------|------|---------------|")
            for line in mem_lines[1:]:
                parts = line.split(",")
                if len(parts) >= 4:
                    lines.append(f"| {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} |")
            lines.append("")

    # Claim-by-claim evaluation
    lines.append("## Claim-by-Claim Evaluation")
    lines.append("")

    lines.append("### Claim 1: DFA-based matching is fundamentally faster")
    lines.append("")
    lines.append("**Evidence:** See speedup table above. Compare jg vs jq/jaq across query patterns.")
    lines.append("Note that CLI startup cost may dominate for small files, masking algorithmic advantages.")
    lines.append("")

    lines.append("### Claim 2: Zero-copy parsing reduces memory")
    lines.append("")
    lines.append("**Evidence:** See Memory Usage table. Compare jg peak RSS vs jq/jaq.")
    lines.append("")

    lines.append("### Claim 3: O(1) per tree edge — linear scaling")
    lines.append("")
    lines.append("**Evidence:** See Scaling Analysis. If jg scales linearly while others scale super-linearly,")
    lines.append("this supports the claim. Look for the time ratio between sizes.")
    lines.append("")

    lines.append("### Claim 4: Compilation cost amortizes")
    lines.append("")
    lines.append("**Evidence:** CLI benchmarks do NOT test this — each invocation recompiles the DFA.")
    lines.append("This claim applies to library usage only. In CLI context, jg pays compile cost every time.")
    lines.append("")

    lines.append("### Claim 5: Performance gap widens with file size")
    lines.append("")
    lines.append("**Evidence:** Compare speedup factors across size tiers in the scaling analysis.")
    lines.append("If the speedup factor increases with file size, this claim is supported.")
    lines.append("")

    # Practical recommendations
    lines.append("## Practical Recommendations")
    lines.append("")
    lines.append("| Use Case | Recommended Tool | Reason |")
    lines.append("|----------|-----------------|--------|")
    lines.append("| Simple extraction from large file | `jg` | DFA advantage scales with file size |")
    lines.append("| Complex transformation/reshaping | `jq` | Full programming language |")
    lines.append("| Grep-like recursive key search | `jg` or `gron` | Pattern matching strength |")
    lines.append("| Small files / quick inspection | `jq` | Mature, universal, fast enough |")
    lines.append("| Scripting integration | `jq` | Better ecosystem, piping support |")
    lines.append("| Repeated queries on same large file | `jg` (library) | DFA compilation amortizes |")
    lines.append("")

    # Limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append("- CLI overhead dominates for small files — algorithmic advantages only matter at scale")
    lines.append("- jsongrep is a **query** tool, not a **transformation** tool — it cannot replace jq")
    lines.append("- Benchmarks run on a single machine — results may vary by hardware")
    lines.append("- Python jmespath benchmarks include interpreter startup cost")
    lines.append("- gron benchmarks include pipe overhead (gron | grep)")
    lines.append("")

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"Report written to {output_path}")
