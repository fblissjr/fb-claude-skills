# Plugin Toolkit Use Cases

Practical workflows combining plugin-toolkit with other plugins and skills.

---

## Use Case 1: Deep Plugin Analysis with Codebase Analyzer

**Scenario**: You want to thoroughly understand a Python-based Claude Code plugin before modifying it.

### Workflow

```bash
# 1. Find all entry points in the plugin
cd ~/path/to/plugin
uv run ~/utils/codebase-analyzer/scripts/find_entries.py .

# 2. Trace imports from main scripts (hook scripts, etc.)
uv run ~/utils/codebase-analyzer/scripts/trace.py hooks/inject.py

# 3. Analyze structure
uv run ~/utils/codebase-analyzer/scripts/analyze.py . --structure

# 4. Now run plugin-toolkit analysis with this context
/plugin-toolkit:analyze .
```

### What This Gives You

| Tool | Output |
|------|--------|
| codebase-analyzer | Import graph, classes, functions, dependencies |
| plugin-toolkit | Command quality, hook evaluation, recommendations |

### Combined Value

- Understand the code structure (codebase-analyzer) before evaluating plugin quality (plugin-toolkit)
- Identify complex hook scripts that need deeper analysis
- Find code duplication across Python modules

---

## Use Case 2: Pre-PR Plugin Review

**Scenario**: You've modified a plugin and want to validate changes before creating a PR.

### Workflow

```bash
# 1. Run plugin-toolkit analysis to check quality
/plugin-toolkit:analyze ~/my-plugin

# 2. Review the recommendations
cat ~/my-plugin/analysis/RECOMMENDATIONS.md

# 3. Use pr-review-toolkit for code review
/pr-review-toolkit:code-reviewer

# 4. Check for silent failures in hook scripts
/pr-review-toolkit:silent-failure-hunter
```

### Combined Agents

```
plugin-toolkit:quality-checker  →  Plugin-level quality assessment
pr-review-toolkit:code-reviewer →  Code-level issue detection
pr-review-toolkit:silent-failure-hunter → Error handling gaps
```

---

## Use Case 3: Improve Third-Party Plugin

**Scenario**: You found a useful plugin but it lacks standard utilities.

### Workflow

```bash
# 1. Analyze current state
/plugin-toolkit:analyze ~/downloaded-plugin

# Review what's missing in analysis/RECOMMENDATIONS.md

# 2. Apply standard polish
/plugin-toolkit:polish ~/downloaded-plugin

# This adds:
# - /help command (auto-generated from existing commands)
# - /status command
# - /on and /off commands (if hooks exist)
# - CHANGELOG.md
# - Error handling to hook scripts

# 3. Add custom features if needed
/plugin-toolkit:feature add ~/downloaded-plugin command "debug" "Show debug info"
```

---

## Use Case 4: Plugin Development with Context Fields

**Scenario**: Developing a new plugin with cognitive constraints active.

### Workflow

```bash
# 1. Start with planning constraint
/context-fields:planning
"I want to create a new plugin for X"

# Claude plans with:
# - Do not start executing before planning
# - What are we actually trying to achieve?
# - Identify dependencies

# 2. Switch to code constraint when implementing
/context-fields:code
"Now implement the main hook script"

# Claude codes with:
# - State assumptions before writing
# - Don't claim correctness you haven't verified
# - Don't handle only happy path

# 3. Use critic constraint for self-review
/context-fields:critic
"Review this plugin implementation"

# 4. Run plugin-toolkit analysis for external validation
/plugin-toolkit:analyze .
```

---

## Use Case 5: Reference Implementation Matching

**Scenario**: Building a plugin that should mirror another plugin's structure.

### Workflow

```bash
# 1. Analyze the reference plugin
/plugin-toolkit:analyze ~/reference-plugin

# Save the structure for comparison
cat ~/reference-plugin/analysis/ANALYSIS.md > reference-structure.md

# 2. Start your implementation
/plugin-toolkit:feature add ~/my-plugin command "feature1" "First feature"
/plugin-toolkit:feature add ~/my-plugin command "feature2" "Second feature"

# 3. Use codebase-analyzer to compare (if Python)
uv run ~/utils/codebase-analyzer/scripts/compare.py \
  --entry ~/reference-plugin/hooks/main.py \
  --entry ~/my-plugin/hooks/main.py

# 4. Re-analyze to verify parity
/plugin-toolkit:analyze ~/my-plugin
```

---

## Use Case 6: Bulk Plugin Audit

**Scenario**: Audit all plugins in your plugins directory.

### Workflow

```bash
# 1. List all plugins
ls ~/.claude/plugins/

# 2. Analyze each (run in parallel if many)
for plugin in ~/.claude/plugins/*/; do
  /plugin-toolkit:analyze "$plugin"
done

# 3. Review all recommendations
cat ~/.claude/plugins/*/analysis/RECOMMENDATIONS.md

# 4. Polish plugins that need it
/plugin-toolkit:polish ~/.claude/plugins/plugin-needing-work
```

### Automation Pattern

```bash
# Find plugins without help commands
for plugin in ~/.claude/plugins/*/; do
  if [ ! -f "$plugin/commands/help.md" ]; then
    echo "Missing help: $plugin"
  fi
done
```

---

## Use Case 7: Feature Development Integration

**Scenario**: Using feature-dev agents alongside plugin-toolkit.

### Workflow

```bash
# 1. Use code-explorer to understand existing plugin
/feature-dev:code-explorer
"Explain how the hook system works in this plugin"

# 2. Use code-architect to plan new feature
/feature-dev:code-architect
"Design a caching layer for the hook output"

# 3. Implement with plugin-toolkit
/plugin-toolkit:feature add . hook "PreToolUse" "cache-check.sh"

# 4. Review with code-reviewer
/feature-dev:code-reviewer
```

---

## Use Case 8: Plugin Structure Analysis Pipeline

**Scenario**: Understand a complex plugin with many components.

### Full Pipeline

```bash
# 1. Get high-level structure
/plugin-toolkit:analyze ~/complex-plugin

# 2. Deep dive into Python components
cd ~/complex-plugin
uv run ~/utils/codebase-analyzer/scripts/find_entries.py .
uv run ~/utils/codebase-analyzer/scripts/analyze.py . --structure --parallel 4

# 3. Trace specific execution paths
uv run ~/utils/codebase-analyzer/scripts/trace.py hooks/main-hook.py

# 4. Apply context-fields for thorough review
/context-fields:adversarial
"What could go wrong with this plugin?"

/context-fields:debug
"What are potential failure modes in the hook scripts?"
```

---

## Use Case 9: Plugin Migration

**Scenario**: Migrating a plugin to a new structure or API version.

### Workflow

```bash
# 1. Analyze current state
/plugin-toolkit:analyze ~/old-plugin

# 2. Create new plugin structure
mkdir ~/new-plugin
cp ~/old-plugin/plugin.json ~/new-plugin/

# 3. Migrate features one by one
/plugin-toolkit:feature add ~/new-plugin command "feature1" "Migrated feature"

# 4. Compare structures
diff -r ~/old-plugin/commands ~/new-plugin/commands

# 5. Validate new plugin
/plugin-toolkit:analyze ~/new-plugin
```

---

## Use Case 10: Hookify Integration

**Scenario**: Creating automatic context field activation based on plugin activity.

### Workflow

```bash
# 1. Use hookify to create rules
/hookify:hookify
"When I'm working on plugin development, auto-activate /code + /critic"

# 2. Now plugin-toolkit commands trigger context fields
/plugin-toolkit:analyze ~/my-plugin
# → Automatically has /code + /critic constraints active

# 3. Create more specific rules
/hookify:hookify
"When reviewing plugin analysis output, activate /adversarial"
```

---

## Quick Reference: Plugin Combinations

| Task | Primary Tool | Supporting Tools |
|------|--------------|------------------|
| Understand plugin structure | plugin-toolkit:analyze | codebase-analyzer (Python) |
| Add utilities | plugin-toolkit:polish | - |
| Add/remove features | plugin-toolkit:feature | - |
| Code-level review | pr-review-toolkit | context-fields:/critic |
| Plan new plugin | context-fields:/planning | feature-dev:code-architect |
| Implement plugin code | context-fields:/code | feature-dev agents |
| Debug hook issues | codebase-analyzer | context-fields:/debug |
| Find silent failures | pr-review-toolkit:silent-failure-hunter | context-fields:/adversarial |

---

## Command Cheat Sheet

```bash
# Analysis
/plugin-toolkit:analyze <path>

# Polish (add help, status, on/off, changelog)
/plugin-toolkit:polish <path>

# Add features
/plugin-toolkit:feature add <path> command <name> "<desc>"
/plugin-toolkit:feature add <path> hook <event> <script>
/plugin-toolkit:feature add <path> trait <name> "<desc>"
/plugin-toolkit:feature add <path> agent <name> "<desc>"

# Remove features
/plugin-toolkit:feature remove <path> command <name>

# Modify features
/plugin-toolkit:feature change <path> command <name> --description "<new>"

# Codebase analyzer (for Python plugins)
uv run ~/utils/codebase-analyzer/scripts/find_entries.py <path>
uv run ~/utils/codebase-analyzer/scripts/trace.py <entry>
uv run ~/utils/codebase-analyzer/scripts/analyze.py <path> --structure
uv run ~/utils/codebase-analyzer/scripts/compare.py <trace1> <trace2>
```
