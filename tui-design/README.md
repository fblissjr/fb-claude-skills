last updated: 2026-02-15

# tui-design

Design functional, readable terminal UIs with proper visual hierarchy, semantic color, and responsive layout.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install tui-design@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/tui-design
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `tui-design` | "terminal UI", "TUI", "Rich table", "CLI output", "terminal dashboard", "questionary prompt" | Design terminal interfaces with semantic color, responsive layout, and proper component selection |

## invocation

```
/tui-design
```

Or describe what you need:

```
"Build a CLI dashboard for monitoring services"
"Create a Rich table that works at any terminal width"
"Add interactive session selection with Questionary"
"Make this terminal output more readable"
```

## what it covers

- 5 design principles: semantic color, responsive layout, right component, visual hierarchy, progressive density
- Rich component selection (Table, Panel, Tree, Progress, Columns, Layout)
- Questionary patterns (selection, checkbox, multi-phase wizards)
- 9 anti-patterns with before/after code
- 4 complete layout recipes (data browser, dashboard, progress reporter, selection wizard)
- 16-color safe palette with semantic meanings
- Pipe-safe and NO_COLOR-aware output

## references

| Reference | Purpose |
|-----------|---------|
| rich_patterns.md | Rich component selection guide with code examples |
| questionary_patterns.md | Interactive prompt patterns and multi-phase wizards |
| anti_patterns.md | 9 anti-patterns with before/after case studies |
| layout_recipes.md | 4 complete recipes (data browser, dashboard, progress, wizard) |

## scope

This skill covers Rich, Questionary, and Click-based terminal UIs. Textual (full TUI framework with event-driven widget trees) is a different paradigm and is not covered here.
