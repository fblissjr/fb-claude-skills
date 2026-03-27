"""CLI entrypoint for schema-bench."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _project_root() -> Path:
    """Find the research/schema-processing directory."""
    return Path(__file__).resolve().parent.parent.parent


def cmd_generate(args: argparse.Namespace) -> None:
    from schema_bench.generate import generate_all

    output = Path(args.output) if args.output else _project_root() / "results" / "data"
    sizes = args.sizes.split(",") if args.sizes else None
    schemas = args.schemas.split(",") if args.schemas else None

    print(f"Generating test data -> {output}")
    generated = generate_all(output, sizes=sizes, schemas=schemas, seed=args.seed)
    print(f"\nGenerated {len(generated)} files.")


def cmd_tools(args: argparse.Namespace) -> None:
    from schema_bench.tools import print_tool_status

    print_tool_status()


def cmd_bench(args: argparse.Namespace) -> None:
    from schema_bench.bench import measure_memory, run_benchmarks

    root = _project_root()
    data_dir = Path(args.data_dir) if args.data_dir else root / "results" / "data"
    results_dir = Path(args.results_dir) if args.results_dir else root / "results"
    sizes = args.sizes.split(",") if args.sizes else None
    schemas = args.schemas.split(",") if args.schemas else None
    queries = args.queries.split(",") if args.queries else None
    tools = args.tools.split(",") if args.tools else None

    print(f"Data dir: {data_dir}")
    print(f"Results dir: {results_dir}")
    print()

    result_files = run_benchmarks(
        data_dir, results_dir,
        sizes=sizes, schemas=schemas, queries=queries, tools=tools,
    )
    print(f"\n{len(result_files)} benchmark result files written.")

    if not args.skip_memory:
        print("\nMeasuring memory usage...")
        mem_csv = measure_memory(data_dir, results_dir, sizes=sizes, schemas=schemas)
        print(f"Memory results: {mem_csv}")


def cmd_analyze(args: argparse.Namespace) -> None:
    from schema_bench.analyze import parse_hyperfine_results, results_to_csv
    from schema_bench.report import generate_report

    root = _project_root()
    results_dir = Path(args.results_dir) if args.results_dir else root / "results"
    raw_dir = results_dir / "raw"
    processed_dir = results_dir / "processed"

    if not raw_dir.exists() or not list(raw_dir.glob("*.json")):
        print("ERROR: No benchmark results found. Run 'schema-bench bench' first.")
        sys.exit(1)

    print("Parsing results...")
    results = parse_hyperfine_results(raw_dir)
    print(f"  {len(results)} result entries parsed.")

    csv_path = processed_dir / "all_results.csv"
    results_to_csv(results, csv_path)
    print(f"  CSV written to {csv_path}")

    mem_csv = processed_dir / "memory_usage.csv"
    report_path = results_dir / "report.md"
    generate_report(
        results, report_path,
        memory_csv=mem_csv if mem_csv.exists() else None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="schema-bench", description="JSON query tool benchmark harness")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Generate test data files")
    gen.add_argument("--output", "-o", help="Output directory")
    gen.add_argument("--sizes", help="Comma-separated size tiers (tiny,small,medium,large,xlarge)")
    gen.add_argument("--schemas", help="Comma-separated schemas (flat,nested,deep,...)")
    gen.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")

    # tools
    sub.add_parser("tools", help="Check tool availability")

    # bench
    bench = sub.add_parser("bench", help="Run benchmarks")
    bench.add_argument("--data-dir", help="Directory with test data")
    bench.add_argument("--results-dir", help="Directory for results output")
    bench.add_argument("--sizes", help="Comma-separated size tiers")
    bench.add_argument("--schemas", help="Comma-separated schemas")
    bench.add_argument("--queries", help="Comma-separated query names")
    bench.add_argument("--tools", help="Comma-separated tool names")
    bench.add_argument("--skip-memory", action="store_true", help="Skip memory measurement")

    # analyze
    analyze = sub.add_parser("analyze", help="Analyze results and generate report")
    analyze.add_argument("--results-dir", help="Directory with benchmark results")

    args = parser.parse_args()
    {
        "generate": cmd_generate,
        "tools": cmd_tools,
        "bench": cmd_bench,
        "analyze": cmd_analyze,
    }[args.command](args)


if __name__ == "__main__":
    main()
