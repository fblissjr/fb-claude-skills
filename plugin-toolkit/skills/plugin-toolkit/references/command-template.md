# Command Template

Boilerplate templates for common plugin commands.

---

## Standard Command Structure

```markdown
---
description: [Brief description of what this command does]
argument-hint: [optional hint for arguments]
---

[Command content - instructions, constraints, or output]

$ARGUMENTS
```

---

## /help Command Template

```markdown
---
description: List all available commands with descriptions
---

# [Plugin Name] - Quick Reference

## What is [Plugin Name]?

[Brief description of the plugin's purpose]

---

## Commands

| Command | Purpose |
|---------|---------|
| `/[name]` | [description] |

---

## Usage Examples

[Common usage patterns]
```

---

## /status Command Template

```markdown
---
description: Show current [plugin-name] status
---

# [Plugin Name] Status

## Auto-Activation

[Explain how to check if auto-activation is enabled]

**To toggle:**
- Disable: `/[plugin]:off`
- Enable: `/[plugin]:on`

---

## Current State

[Describe what state information is relevant]

---

## Available Commands

[List commands briefly]

Use `/[plugin]:help` for full descriptions.
```

---

## /off Command Template

```markdown
---
description: Disable auto-activation of [Plugin Name]
---

[Plugin Name] auto-activation has been **disabled**.

From now on, [plugin features] will only be applied when explicitly invoked.

To re-enable: `/[plugin]:on`

**What this changes:**
- [Change 1]
- [Change 2]
```

---

## /on Command Template

```markdown
---
description: Enable auto-activation of [Plugin Name]
---

[Plugin Name] auto-activation has been **enabled**.

[Describe what auto-activation does]

To disable: `/[plugin]:off`
```

---

## Feature Command Template

```markdown
---
description: [What this feature does]
argument-hint: [expected input]
---

# [Feature Name]

## Purpose

[Detailed explanation]

## Usage

[How to use this command]

## Examples

[Concrete examples]

$ARGUMENTS
```

---

## Constraint-Based Command Template

For plugins using inhibition-based patterns (like context-fields):

```markdown
---
description: [What constraints this applies]
argument-hint: [your request]
---

Apply these constraints:

```
Do not [blocker 1].
Do not [blocker 2].
Do not [blocker 3].
[Forcing function question]?
```

$ARGUMENTS
```
