last updated: 2026-02-14

# cogapp-markdown

Auto-generate sections of markdown documentation by embedding Python code that produces content. Keeps docs in sync with code by embedding CLI --help output, generating tables, or deriving content from the codebase itself.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install cogapp-markdown@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/cogapp-markdown
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
