<!-- source: https://code.claude.com/docs/en/skills -->
<!-- fetched: 2026-02-14 -->

# Extend Claude with skills

> Create, manage, and share skills to extend Claude's capabilities in Claude Code. Includes custom slash commands.

Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with `/skill-name`.

> **Note:** Custom slash commands have been merged into skills. A file at `.claude/commands/review.md` and a skill at `.claude/skills/review/SKILL.md` both create `/review` and work the same way. Your existing `.claude/commands/` files keep working. Skills add optional features: a directory for supporting files, frontmatter to control invocation, and automatic loading when relevant.

Claude Code skills follow the [Agent Skills](https://agentskills.io) open standard, which works across multiple AI tools.

## Getting started

### Create your first skill

```bash
mkdir -p ~/.claude/skills/explain-code
```

Create `~/.claude/skills/explain-code/SKILL.md`:

```yaml
---
name: explain-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
---

When explaining code, always include:

1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
3. **Walk through the code**: Explain step-by-step what happens
4. **Highlight a gotcha**: What's a common mistake or misconception?
```

Test by asking "How does this code work?" or invoke directly with `/explain-code src/auth/login.ts`.

### Where skills live

| Location   | Path                                     | Applies to                     |
| :--------- | :--------------------------------------- | :----------------------------- |
| Enterprise | See managed settings                     | All users in your organization |
| Personal   | `~/.claude/skills/<name>/SKILL.md`       | All your projects              |
| Project    | `.claude/skills/<name>/SKILL.md`         | This project only              |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`        | Where plugin is enabled        |

Priority: enterprise > personal > project. Plugin skills use `plugin-name:skill-name` namespace (no conflicts).

Each skill is a directory with `SKILL.md` as the entrypoint:

```
my-skill/
+-- SKILL.md           # Main instructions (required)
+-- template.md        # Template for Claude to fill in
+-- examples/
|   +-- sample.md      # Example output showing expected format
+-- scripts/
    +-- validate.sh    # Script Claude can execute
```

## Configure skills

### Frontmatter reference

```yaml
---
name: my-skill
description: What this skill does
disable-model-invocation: true
allowed-tools: Read, Grep
---
```

| Field                      | Required    | Description                                                                      |
| :------------------------- | :---------- | :------------------------------------------------------------------------------- |
| `name`                     | No          | Display name. If omitted, uses directory name. Kebab-case, max 64 chars.         |
| `description`              | Recommended | What the skill does and when to use it. Claude uses this for automatic loading.  |
| `argument-hint`            | No          | Hint shown during autocomplete (e.g., `[issue-number]`).                         |
| `disable-model-invocation` | No          | `true` prevents Claude from auto-loading. Manual `/name` only. Default: `false`. |
| `user-invocable`           | No          | `false` hides from `/` menu. Background knowledge only. Default: `true`.         |
| `allowed-tools`            | No          | Tools Claude can use without asking permission when skill is active.             |
| `model`                    | No          | Model to use when this skill is active.                                          |
| `context`                  | No          | Set to `fork` to run in a forked subagent context.                               |
| `agent`                    | No          | Which subagent type to use when `context: fork` is set.                          |
| `hooks`                    | No          | Hooks scoped to this skill's lifecycle.                                          |

### String substitutions

| Variable               | Description                                    |
| :--------------------- | :--------------------------------------------- |
| `$ARGUMENTS`           | All arguments passed when invoking the skill.  |
| `$ARGUMENTS[N]`        | Specific argument by 0-based index.            |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`.                 |
| `${CLAUDE_SESSION_ID}` | The current session ID.                        |

### Add supporting files

Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files.

```
my-skill/
+-- SKILL.md (overview and navigation)
+-- reference.md (detailed API docs - loaded when needed)
+-- examples.md (usage examples - loaded when needed)
+-- scripts/
    +-- helper.py (utility script - executed, not loaded)
```

Reference from SKILL.md: `For complete API details, see [reference.md](reference.md)`

### Control who invokes a skill

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context                                     |
| :------------------------------- | :------------- | :---------------- | :----------------------------------------------------------- |
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | Description not in context, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

### Restrict tool access

```yaml
---
name: safe-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

### Pass arguments to skills

```yaml
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---

Fix GitHub issue $ARGUMENTS following our coding standards.
```

`/fix-issue 123` -> Claude receives "Fix GitHub issue 123 following our coding standards."

Positional access: `$ARGUMENTS[0]`, `$ARGUMENTS[1]` or shorthand `$0`, `$1`.

## Advanced patterns

### Inject dynamic context

The `` !`command` `` syntax runs shell commands before the skill content is sent to Claude:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`
```

### Run skills in a subagent

Add `context: fork` to run in isolation. The skill content becomes the prompt that drives the subagent.

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

The `agent` field options: built-in agents (`Explore`, `Plan`, `general-purpose`) or custom subagents from `.claude/agents/`. Default: `general-purpose`.

### Restrict Claude's skill access

Three ways to control which skills Claude can invoke:

- **Disable all skills**: deny `Skill` tool in `/permissions`
- **Allow/deny specific**: `Skill(commit)`, `Skill(deploy *)`
- **Hide individual**: `disable-model-invocation: true` in frontmatter

## Share skills

- **Project skills**: Commit `.claude/skills/` to version control
- **Plugins**: Create a `skills/` directory in your plugin
- **Managed**: Deploy organization-wide through managed settings

## Troubleshooting

### Skill not triggering

1. Check the description includes keywords users would naturally say
2. Verify the skill appears in `What skills are available?`
3. Try rephrasing your request to match the description
4. Invoke directly with `/skill-name`

### Skill triggers too often

1. Make the description more specific
2. Add `disable-model-invocation: true` for manual-only invocation

### Claude doesn't see all my skills

Skill descriptions may exceed the character budget (2% of context window, fallback 16,000 chars). Run `/context` to check. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var.
