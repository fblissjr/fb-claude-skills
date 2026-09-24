---
name: json-query
description: Guide JSON query tool selection and syntax. Use when user needs to extract data from JSON files, search JSON for keys, query nested JSON structures, filter JSON arrays, or process large JSON. Triggers on "query JSON", "extract from JSON", "search JSON", "parse JSON file", "jq alternative", "jsongrep", "jg command", "find in JSON", "JSON path query", "grep JSON", "large JSON file", "process JSON", "JSON extraction".
allowed-tools: "Read,Bash"
---

# JSON query tool selection

**jg for extraction, jq for transformation.** jsongrep (`jg`) compiles a path query into a DFA and walks the tree once, so it outruns jq on large files when the task is finding values. It cannot compute anything: no `select()`, conditionals, arithmetic or reshaping. jq is a full language and the default whenever output differs in shape from input.

<choose>
| Task | Tool |
|------|------|
| Extract values by path from a large file | `jg` |
| Find every occurrence of a key at any depth | `jg '(* \| [*])*.key'` or `jg -F key` |
| Filter, reshape, compute, interpolate strings | `jq` |
| Small file, quick look | `jq`; the speed difference is negligible there |
| Grep-style search over values | `gron file.json \| grep` |
| Large NDJSON log extraction | `jg` |

When `jg` is not installed, use jq rather than stalling on the install; offer `cargo install jsongrep` (it installs as `jg`) when the files are large enough for the speed to matter.
</choose>

<syntax>
jg has no leading dot and describes sets of paths:

| Operation | jq | jg |
|-----------|----|----|
| Field / nested path | `.a.b.c` | `a.b.c` |
| Array index / slice | `.[0]` / `.[0:5]` | `[0]` / `[0:5]` |
| All array elements | `.[]` | `[*]` |
| Any single field | `.[]` | `*` |
| Recursive descent | `.. \| .key?` | `(* \| [*])*.key` |
| Several fields | `.a, .b` | `(a \| b)` |
| Key at any depth, literal | n/a | `-F key` |

```bash
jg 'data.users[*].profile.address.city' file.json
jg '(* | [*])*.id' --count -n file.json    # count matches, print nothing
```

Operators, flags (`--with-path`, `-i`, `--count`) and more patterns: [references/syntax_guide.md](references/syntax_guide.md).
</syntax>

The speed claim comes from a benchmark in this repo's history (`git show cc12498:research/schema-processing/REPORT.md`) and the [jsongrep author's write-up](https://micahkepe.com/blog/jsongrep/).
