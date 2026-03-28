# json-query

*Last updated: 2026-03-27*

JSON query tool selection and syntax guidance. Helps choose between jg (jsongrep) for fast extraction and jq for transformations, with syntax mapping between tools.

## Installation

```bash
/plugin install json-query@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `json-query` | "query JSON", "extract from JSON", "search JSON", "jg command" | Guide tool selection and provide syntax for JSON path queries |

## Invocation

```
/json-query:json-query
```

Or trigger automatically by asking about JSON extraction, searching JSON files, or referencing jsongrep/jg.

## Background

Based on independent benchmark evaluation of [jsongrep](https://github.com/micahkepe/jsongrep) claims. jsongrep compiles JSON path queries into DFAs for single-pass tree traversal, achieving 3-7x speedups over jq on files >1MB.

Full benchmark data: `research/schema-processing/REPORT.md`
