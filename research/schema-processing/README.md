# schema-bench: jsongrep Claims Evaluation

*Last updated: 2026-03-27*

Independent benchmark suite evaluating the performance claims from ["jsongrep is faster than {jq, jmespath, jsonpath-rust, jql}"](https://micahkepe.com/blog/jsongrep/).

## What This Tests

jsongrep compiles JSON path queries into DFAs (Deterministic Finite Automata) for tree traversal. The blog post claims orders-of-magnitude speedups over jq and similar tools. This benchmark evaluates those claims at the **CLI level** — what developers actually experience.

### Claims Under Evaluation

1. DFA-based matching is fundamentally faster than interpreted approaches
2. Zero-copy parsing reduces memory overhead
3. O(1) per tree edge, no backtracking — linear scaling
4. Compilation cost amortizes across searches
5. Performance gap widens with file size

### Tools Compared

| Tool | Role |
|------|------|
| `jq` | The standard JSON processor |
| `jaq` | Rust jq clone (isolates language vs implementation) |
| `jg` (jsongrep) | DFA-based path matcher (the challenger) |
| `gron` | Flatten-then-grep approach |
| Python `jmespath` | Scripting baseline |

### Schema Types

| Schema | Description |
|--------|-------------|
| flat | Config-like key-value pairs |
| nested | API response (3-5 levels) |
| deep | 10+ levels of nesting |
| array_heavy | Log-like arrays of objects |
| mixed | Heterogeneous event streams |
| wide | Many keys at same level |
| real_world | GeoJSON FeatureCollection |

### Size Tiers

tiny (100B), small (10KB), medium (1MB), large (10MB), xlarge (100MB)

## Setup

```bash
# Install benchmark tools
bash scripts/install_tools.sh

# Install Python deps
cd /path/to/fb-claude-skills
uv sync --all-packages
```

## Usage

```bash
# Check tool availability
uv run schema-bench tools

# Generate test data
uv run schema-bench generate
uv run schema-bench generate --sizes small,medium --schemas flat,nested

# Run benchmarks
uv run schema-bench bench
uv run schema-bench bench --sizes small,medium --schemas nested --queries nested_path

# Analyze results and generate report
uv run schema-bench analyze

# Full pipeline
bash scripts/run_all.sh
```

## Results

After running benchmarks, find results in:
- `results/raw/` — hyperfine JSON output per benchmark
- `results/processed/all_results.csv` — consolidated data
- `results/processed/memory_usage.csv` — peak RSS measurements
- `results/report.md` — full analysis report

## Query Patterns Tested

| Pattern | Description | Example (jg) |
|---------|-------------|--------------|
| simple_field | Top-level key access | `key_000000` |
| nested_path | Multi-level path | `data.users[0].profile.address.city` |
| recursive_descent | Find key at any depth | `(* \| [*])*.description` |
| wildcard_array | All array elements | `[*].timestamp` |
| array_index | Specific element | `[0]` |
| array_slice | Range of elements | `[0:5]` |
| multi_field | Union/alternation | `data.users[0].(name \| email)` |
| deep_nested_path | 10+ level path | `chains[0].config.system...value` |
| geo_all_types | GeoJSON geometry types | `features[*].geometry.type` |
| geo_recursive_coords | All coordinates | `(* \| [*])*.coordinates` |

## Development

```bash
# Run tests
uv run pytest research/schema-processing/tests/ -v
```
