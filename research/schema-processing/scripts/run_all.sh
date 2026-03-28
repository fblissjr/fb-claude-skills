#!/usr/bin/env bash
# Full benchmark pipeline: generate data, run benchmarks, analyze results
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Phase 1: Check tools ==="
uv run schema-bench tools
echo ""

echo "=== Phase 2: Generate test data ==="
uv run schema-bench generate --sizes tiny,small,medium,large
echo ""

echo "=== Phase 3: Run benchmarks ==="
uv run schema-bench bench --sizes tiny,small,medium,large
echo ""

echo "=== Phase 4: Analyze and generate report ==="
uv run schema-bench analyze
echo ""

echo "=== Done ==="
echo "Report: results/report.md"
