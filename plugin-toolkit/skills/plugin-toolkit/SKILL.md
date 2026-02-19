---
name: plugin-toolkit
description: Analyze, polish, and manage Claude Code plugins. Use when user wants to evaluate a plugin (/plugin-toolkit:analyze), add standard utility commands (/plugin-toolkit:polish), or add/remove/modify plugin features (/plugin-toolkit:feature). Also use when user mentions "plugin analysis", "plugin review", "add command to plugin", or "improve plugin". Also use when user says "review my plugin", "check plugin quality", "what's wrong with my plugin", "add a help command to my plugin", or "improve my plugin structure".
metadata:
  author: Fred Bliss
  version: 0.1.0
allowed-tools: "Read, Glob, Grep"
---

# Plugin Toolkit

Tools for working with Claude Code plugins: analyze their structure, add standard polish, and manage features.

## Commands

| Command | Purpose |
|---------|---------|
| `/plugin-toolkit:analyze <path>` | Produce structured analysis documentation |
| `/plugin-toolkit:polish <path>` | Add standard utility commands (help, status, on/off) |
| `/plugin-toolkit:feature <action> <path>` | Add, remove, or modify plugin features |

---

## /plugin-toolkit:analyze

Produce comprehensive analysis of any Claude Code plugin.

### Usage

```
/plugin-toolkit:analyze ~/path/to/plugin
/plugin-toolkit:analyze .  # Current directory
```

### Output

Creates `analysis/` directory with:

```
analysis/
├── ANALYSIS.md           # Architecture, data flow, components
├── RECOMMENDATIONS.md    # Prioritized improvements
├── INTEGRATION_WORKFLOWS.md  # Cross-plugin patterns
└── SKILL_REVIEW.md       # Quality ratings
```

### Process

1. **Scan plugin structure** using plugin-scanner agent
2. **Evaluate quality** using quality-checker agent
3. **Generate documentation** using analysis-template reference

### Analysis Criteria

From [references/quality-checklist.md](references/quality-checklist.md):

- Plugin metadata completeness
- Command consistency and coverage
- Hook implementation (opt-out exists?)
- Documentation quality
- Error handling
- Maintenance burden (duplication?)
- Integration potential

---

## /plugin-toolkit:polish

Add standard utility infrastructure to any plugin.

### Usage

```
/plugin-toolkit:polish ~/path/to/plugin
/plugin-toolkit:polish . --skip-changelog  # Skip CHANGELOG creation
```

### What It Adds

| Component | Description |
|-----------|-------------|
| `/help` command | Lists all commands with descriptions |
| `/status` command | Shows current plugin state |
| `/off` command | Disables auto-activation (if hooks exist) |
| `/on` command | Enables auto-activation |
| `CHANGELOG.md` | Version history (if missing) |
| Error handling | Adds to hook scripts |

### Smart Behavior

- Detects existing hooks and only adds on/off if relevant
- Scans existing commands to generate help content
- Idempotent - won't duplicate if already present
- Preserves existing file formatting

### Process

1. **Scan plugin** using plugin-scanner agent
2. **Check existing utilities** - skip what's already present
3. **Generate commands** using command-template reference
4. **Add hooks** if plugin uses auto-activation
5. **Create CHANGELOG** if missing

---

## /plugin-toolkit:feature

Add, remove, or modify plugin features.

### Usage

```
/plugin-toolkit:feature add <path> command <name> "<description>"
/plugin-toolkit:feature add <path> hook <event> <script>
/plugin-toolkit:feature add <path> trait <name> "<description>"
/plugin-toolkit:feature add <path> agent <name> "<description>"

/plugin-toolkit:feature remove <path> command <name>
/plugin-toolkit:feature remove <path> hook <event>

/plugin-toolkit:feature change <path> command <name> --description "<new>"
```

### Examples

**Add a new command:**
```
/plugin-toolkit:feature add ~/my-plugin command "review" "Review code for issues"
```

**Add a hook:**
```
/plugin-toolkit:feature add ~/my-plugin hook "UserPromptSubmit" "inject-context.sh"
```

**Remove a command:**
```
/plugin-toolkit:feature remove ~/my-plugin command "deprecated-cmd"
```

**Modify a command:**
```
/plugin-toolkit:feature change ~/my-plugin command "help" --description "Updated help text"
```

### What It Handles

**Add:**
- Creates command/trait/agent markdown file
- Updates plugin.json if needed
- Creates hook script with boilerplate
- Updates SKILL.md references

**Remove:**
- Removes the file
- Cleans up plugin.json references
- Removes hook entries
- Warns about potential breakage

**Change:**
- Modifies existing files in place
- Updates related references

---

## Composability

This skill uses shared components:

### Agents

- **plugin-scanner** - Explores plugin structure, returns inventory
- **quality-checker** - Evaluates against checklist, returns ratings

### References

- **[analysis-template.md](references/analysis-template.md)** - Structure for analysis docs
- **[command-template.md](references/command-template.md)** - Boilerplate for new commands
- **[quality-checklist.md](references/quality-checklist.md)** - Evaluation criteria
- **[hook-patterns.md](references/hook-patterns.md)** - Common hook implementations

---

## Examples

### Full Plugin Review Workflow

```
# 1. Analyze the plugin
/plugin-toolkit:analyze ~/claude/my-plugin

# 2. Review the analysis
cat ~/claude/my-plugin/analysis/RECOMMENDATIONS.md

# 3. Apply standard polish
/plugin-toolkit:polish ~/claude/my-plugin

# 4. Add any custom features
/plugin-toolkit:feature add ~/claude/my-plugin command "custom" "My custom command"
```

### Quick Polish for New Plugin

```
# Just add utilities, skip analysis
/plugin-toolkit:polish ~/claude/my-plugin
```

### Feature Management

```
# Add a debugging command
/plugin-toolkit:feature add . command "debug" "Show debugging information"

# Later, remove it
/plugin-toolkit:feature remove . command "debug"
```
