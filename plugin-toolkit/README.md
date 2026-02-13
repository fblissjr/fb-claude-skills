last updated: 2026-02-13

# plugin-toolkit

Tools for analyzing, polishing, and managing Claude Code plugins.

## installation

```bash
claude plugin add /path/to/fb-claude-skills/plugin-toolkit
```

Or from the repo URL:

```bash
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin plugin-toolkit
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `plugin-toolkit` | "analyze plugin", "polish plugin", "add command to plugin" | Analyze plugin structure, add standard utility commands, manage features |

## invocation

```
/plugin-toolkit:analyze ~/path/to/plugin
/plugin-toolkit:polish ~/path/to/plugin
/plugin-toolkit:feature add ~/my-plugin command "review" "Review code for issues"
```

## commands

| Command | Purpose |
|---------|---------|
| `/plugin-toolkit:analyze <path>` | Produce structured analysis documentation |
| `/plugin-toolkit:polish <path>` | Add standard utility commands (help, status, on/off) |
| `/plugin-toolkit:feature <action> <path>` | Add, remove, or modify plugin features |

## components

### agents

- **plugin-scanner** -- Explores plugin structure, returns inventory
- **quality-checker** -- Evaluates against checklist, returns ratings

### references

- **analysis-template.md** -- Structure for analysis documentation
- **command-template.md** -- Boilerplate for new commands
- **quality-checklist.md** -- Evaluation criteria
- **hook-patterns.md** -- Common hook implementations

## integration with other tools

See [USE_CASES.md](USE_CASES.md) for detailed workflows combining plugin-toolkit with codebase-analyzer, context-fields, pr-review-toolkit, feature-dev, and hookify.
