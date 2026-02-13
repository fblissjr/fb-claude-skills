last updated: 2026-02-13

# cogapp-markdown

Auto-generate sections of markdown documentation by embedding Python code that produces content. Keeps docs in sync with code by embedding CLI --help output, generating tables, or deriving content from the codebase itself.

## installation

```bash
claude plugin add /path/to/fb-claude-skills/cogapp-markdown
```

Or from the repo URL:

```bash
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin cogapp-markdown
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `cogapp-markdown` | "keep docs in sync with code", "embed CLI help in README", "auto-generate markdown" | Guides using cogapp to embed Python code in markdown that produces auto-generated sections |

## invocation

```
/cogapp-markdown
```

## credits

From [simonw's skills repo](https://github.com/simonw/skills/tree/main/cogapp-markdown).
