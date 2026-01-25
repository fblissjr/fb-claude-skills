# Plugin Toolkit

Tools for analyzing, polishing, and managing Claude Code plugins.

## Installation

Add to your Claude Code plugins directory or reference in your settings.

## Commands

| Command | Purpose |
|---------|---------|
| `/plugin-toolkit:analyze <path>` | Produce structured analysis documentation |
| `/plugin-toolkit:polish <path>` | Add standard utility commands (help, status, on/off) |
| `/plugin-toolkit:feature <action> <path>` | Add, remove, or modify plugin features |

## Quick Start

### Analyze a Plugin

```
/plugin-toolkit:analyze ~/claude/my-plugin
```

Creates `analysis/` directory with:
- `ANALYSIS.md` - Architecture and component inventory
- `RECOMMENDATIONS.md` - Prioritized improvements
- `INTEGRATION_WORKFLOWS.md` - Cross-plugin patterns
- `SKILL_REVIEW.md` - Quality ratings

### Polish a Plugin

```
/plugin-toolkit:polish ~/claude/my-plugin
```

Adds standard utilities:
- `/help` - Lists all commands
- `/status` - Shows current state
- `/off` / `/on` - Toggle auto-activation
- `CHANGELOG.md` - Version history

### Manage Features

```
# Add a command
/plugin-toolkit:feature add ~/my-plugin command "review" "Review code for issues"

# Remove a command
/plugin-toolkit:feature remove ~/my-plugin command "deprecated"

# Add a hook
/plugin-toolkit:feature add ~/my-plugin hook "UserPromptSubmit" "inject.sh"
```

## Components

### Agents

- **plugin-scanner** - Explores plugin structure, returns inventory
- **quality-checker** - Evaluates against checklist, returns ratings

### References

- **analysis-template.md** - Structure for analysis documentation
- **command-template.md** - Boilerplate for new commands
- **quality-checklist.md** - Evaluation criteria
- **hook-patterns.md** - Common hook implementations

## Example Workflow

```bash
# Full plugin review and improvement
/plugin-toolkit:analyze ~/claude/my-plugin
/plugin-toolkit:polish ~/claude/my-plugin
/plugin-toolkit:feature add ~/my-plugin command "custom" "My feature"
```

## Integration with Other Tools

See **[USE_CASES.md](USE_CASES.md)** for detailed workflows combining plugin-toolkit with:

| Tool | Integration |
|------|-------------|
| **codebase-analyzer** | Deep Python analysis before plugin evaluation |
| **context-fields** | Cognitive constraints during development |
| **pr-review-toolkit** | Code-level review of plugin changes |
| **feature-dev** | Architecture planning for new plugins |
| **hookify** | Auto-activate constraints for plugin work |

## License

MIT
