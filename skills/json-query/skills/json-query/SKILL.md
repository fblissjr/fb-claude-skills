---
name: json-query
description: Guide JSON query tool selection and syntax. Use when user needs to extract data from JSON files, search JSON for keys, query nested JSON structures, filter JSON arrays, or process large JSON. Triggers on "query JSON", "extract from JSON", "search JSON", "parse JSON file", "jq alternative", "jsongrep", "jg command", "find in JSON", "JSON path query", "grep JSON", "large JSON file", "process JSON", "JSON extraction".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-03-27
allowed-tools: "Read,Bash"
---

# JSON Query Tool Selection

Pick the right tool for JSON querying based on task, file size, and query complexity.

## When to Use

- Extracting values from JSON files (especially large ones)
- Searching for keys at any depth in nested JSON
- Choosing between jq, jg (jsongrep), gron, or jmespath
- Writing path queries for JSON tree traversal
- Processing large JSON files (>1MB) where performance matters

## Core Principle

**jg for extraction, jq for transformation.** jsongrep (jg) compiles path queries into DFAs for single-pass tree traversal — 3-7x faster than jq on large files. But jq is a full programming language for reshaping data. Use the right tool for the job.

## Decision Matrix

| Task | Tool | Why |
|------|------|-----|
| Extract value by path from large file (>1MB) | `jg` | 3-7x faster, 300+ MB/s throughput |
| Find all occurrences of a key at any depth | `jg` | DFA recursive descent: `(* \| [*])*.keyname` |
| Transform/reshape JSON structure | `jq` | Full language: filters, math, string ops |
| Small file quick inspection | `jq` | Universal, difference is <2ms |
| Grep-like search for values | `gron \| grep` | Flatten-then-grep is intuitive |
| Pipeline composition | `jq` | Mature ecosystem, better piping |
| Log analysis on large NDJSON | `jg` | Throughput advantage at scale |

## Syntax Mapping (jq → jg)

| Operation | jq | jg |
|-----------|----|----|
| Field access | `.field` | `field` |
| Nested path | `.a.b.c` | `a.b.c` |
| Array index | `.[0]` | `[0]` |
| Array slice | `.[0:5]` | `[0:5]` |
| All array elements | `.[]` | `[*]` |
| Wildcard field | `.[]` | `*` |
| Recursive descent | `.. \| .key?` | `(* \| [*])*.key` |
| Multiple fields | `.a, .b` | `(a \| b)` |
| Fixed string search | N/A | `-F keyname` (any depth) |

## Process

### Step 1: Assess the Task

Is this extraction (finding/reading values) or transformation (reshaping/computing new values)?

- **Extraction** → consider `jg` first, especially for files >1MB
- **Transformation** → use `jq`

### Step 2: Write the Query

For jg queries:
```bash
# Simple field
jg 'fieldname' file.json

# Nested path
jg 'data.users[0].profile.address.city' file.json

# Find all "description" keys at any depth
jg '(* | [*])*.description' file.json

# All array element fields
jg 'items[*].name' file.json

# Quick fixed-string search (any depth)
jg -F description file.json

# Count matches
jg '(* | [*])*.id' --count -n file.json
```

### Step 3: Install if Needed

```bash
# jsongrep
cargo install jsongrep  # installs as 'jg'

# Verify
jg --version
```

## Performance Reference

Benchmarked on 10MB files across 7 schema types (flat, nested, deep, array-heavy, mixed, wide, GeoJSON):

| Query Pattern | jg | jq | jaq | Speedup (jg vs jq) |
|--------------|----|----|-----|-------------------|
| Simple field | 31ms | 184ms | 90ms | 5.9x |
| Nested path (4 levels) | 25ms | 158ms | 66ms | 6.4x |
| Recursive descent | 44ms | 327ms | 383ms | 7.5x |
| Array wildcard | 53ms | 198ms | 92ms | 3.7x |
| Deep path (15 levels) | 37ms | 155ms | 59ms | 4.2x |

Full benchmark data: `research/schema-processing/REPORT.md`

## References

- Query syntax details: see `references/syntax_guide.md`
- Full benchmark report: `research/schema-processing/REPORT.md`
- jsongrep GitHub: https://github.com/micahkepe/jsongrep
- Blog post: https://micahkepe.com/blog/jsongrep/
