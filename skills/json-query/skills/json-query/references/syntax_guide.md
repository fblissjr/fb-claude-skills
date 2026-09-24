# jsongrep (jg) Syntax Guide

## Concept

JSON documents are trees. jsongrep queries are regular expressions over tree paths — matching edges (keys and indices), not characters.

## Operators

| Operator | Syntax | Meaning | Example |
|----------|--------|---------|---------|
| Sequence | `a.b.c` | Match path a → b → c | `user.profile.name` |
| Disjunction | `a \| b` | Match either a or b | `name \| title` |
| Kleene star | `**` | Zero or more field accesses | `**.name` |
| Wildcard | `*` | Any single field | `users.*.email` |
| Array wildcard | `[*]` | Any array index | `items[*].price` |
| Array index | `[N]` | Specific index | `[0]` |
| Array slice | `[N:M]` | Index range (inclusive) | `[0:5]` |
| Repetition | `a*` | Zero or more of preceding | |
| Optional | `a?` | Zero or one of preceding | |
| Grouping | `(...)` | Group sub-expressions | `users[0].(name \| email)` |
| Recursive | `(* \| [*])*` | Any depth through objects and arrays | `(* \| [*])*.key` |

## Common Patterns

### Find a field at any depth
```bash
jg '(* | [*])*.fieldname' file.json
# Or use the shortcut:
jg -F fieldname file.json
```

### Extract all values from array
```bash
jg '[*].fieldname' file.json
```

### Multiple fields from same object
```bash
jg 'obj.(field1 | field2 | field3)' file.json
```

### Nested path through arrays
```bash
jg 'data.users[*].profile.address.city' file.json
```

### Count matches without displaying values
```bash
jg '(* | [*])*.id' --count -n file.json
```

### Case-insensitive matching
```bash
jg -i 'name' file.json
```

## CLI Flags

| Flag | Description |
|------|-------------|
| `-F, --fixed-string` | Treat query as literal field name, search at any depth |
| `--count` | Display match count |
| `-n, --no-display` | Suppress matched value output |
| `--with-path` | Show path header for each match |
| `--no-path` | Hide path headers |
| `-i, --ignore-case` | Case-insensitive matching |

## Key Differences from jq

1. **No leading dot**: jg uses `field` not `.field`
2. **No transformation**: jg finds values, doesn't compute new ones
3. **No filters/conditionals**: No `select()`, `if-then-else`, arithmetic
4. **Regular language**: Queries compile to DFA — no backtracking, O(1) per node
5. **Path-oriented**: Every query describes a set of paths through the tree

## When jq is Still Better

- Data transformation: `jq '{name: .first, age: (.birth_year | now - .)}' `
- Filtering: `jq '.[] | select(.status == "active")'`
- String interpolation: `jq '"Hello, \(.name)"'`
- Pipeline composition: `jq '.data | map(.value) | add'`
- Arithmetic: `jq '.items | map(.price * .qty) | add'`
