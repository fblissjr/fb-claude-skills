last updated: 2026-09-24

# plugin-toolkit

Tools for analyzing, polishing, and managing Claude Code plugins.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install plugin-toolkit@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/plugin-toolkit
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `plugin-toolkit` | "analyze plugin", "polish plugin", "add command to plugin" | Analyze plugin structure, add standard utility commands, manage features |

## invocation

```
/plugin-toolkit:plugin-toolkit analyze /path/to/plugin
/plugin-toolkit:plugin-toolkit polish /path/to/plugin
/plugin-toolkit:plugin-toolkit feature add /path/to/my-plugin command "review" "Review code for issues"
```

## modes

The modes are arguments to the one skill; there are no separate commands.

| Mode | Purpose |
|------|---------|
| `analyze <path>` | Validate, inventory and rate the plugin; write `analysis/` docs |
| `polish <path>` | Add the utilities the plugin lacks (help, status, off/on, CHANGELOG) where the built-ins do not already cover them |
| `feature <action> <path>` | Add, remove, or change a skill, command, agent, or hook |

## components

### agents

- **plugin-scanner** -- Explores plugin structure, returns inventory
- **quality-checker** -- Reviews what `claude plugin validate` cannot see, returns ratings with evidence

## integration with other tools

See [USE_CASES.md](USE_CASES.md) for detailed workflows combining plugin-toolkit with codebase-analyzer, context-fields, pr-review-toolkit, feature-dev, and hookify.
