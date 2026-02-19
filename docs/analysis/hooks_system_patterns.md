last updated: 2026-02-19

# Claude Code Hooks System: Patterns and Reference

This document provides a comprehensive analysis of the Claude Code hooks system --
the event-driven extension mechanism that gives users deterministic control over
Claude Code's behavior at every point in its lifecycle. It covers all event types,
hook types, matcher patterns, resolution flow, decision control, security patterns,
automation patterns, plugin hooks, skill/agent frontmatter hooks, async hooks,
MCP tool hooks, anti-patterns, and a design checklist.

---

## 1. Overview

Hooks are user-defined handlers that execute automatically at specific points in
Claude Code's lifecycle. Unlike skills (which give Claude instructions) or plugins
(which package extensions), hooks provide **deterministic control**: they guarantee
that certain actions always happen rather than relying on the LLM to choose them.

The hook system is event-driven. Claude Code emits events at defined lifecycle
points -- before a tool runs, after a file is written, when a session starts, when
Claude stops responding, and so on. Users register handlers that match specific
events and execute shell commands, LLM prompts, or subagents in response.

Why hooks matter:

- **Determinism**: Hooks fire every time their conditions match. There is no
  probabilistic element.
- **Enforcement**: Block destructive commands, protect sensitive files, validate
  inputs -- all without relying on the model to remember rules.
- **Automation**: Auto-format code after edits, send notifications, inject context,
  run test suites in the background.
- **Composition**: Multiple hooks can fire on the same event. They run in parallel,
  are deduplicated automatically, and combine their decisions.

The mental model: hooks are **interceptors in an event pipeline**. Each lifecycle
event passes through zero or more registered hooks before (or after) the underlying
action executes. Hooks can observe, modify, block, or augment that action.

---

## 2. Event Types

Claude Code defines 14 hook events spanning the full session lifecycle. Events
fall into three categories: session-level events, agentic-loop events, and team
events.

### Session-Level Events

| Event | When It Fires | Can Block? |
|-------|--------------|------------|
| `SessionStart` | Session begins or resumes | No |
| `PreCompact` | Before context compaction | No |
| `SessionEnd` | Session terminates | No |

### Agentic-Loop Events

| Event | When It Fires | Can Block? |
|-------|--------------|------------|
| `UserPromptSubmit` | User submits a prompt, before Claude processes it | Yes |
| `PreToolUse` | Before a tool call executes | Yes |
| `PermissionRequest` | When a permission dialog appears | Yes |
| `PostToolUse` | After a tool call succeeds | No (tool already ran) |
| `PostToolUseFailure` | After a tool call fails | No (tool already failed) |
| `Notification` | When Claude Code sends a notification | No |
| `SubagentStart` | When a subagent is spawned | No |
| `SubagentStop` | When a subagent finishes | Yes |
| `Stop` | When Claude finishes responding (main agent) | Yes |

### Team Events

| Event | When It Fires | Can Block? |
|-------|--------------|------------|
| `TeammateIdle` | Agent team teammate is about to go idle | Yes |
| `TaskCompleted` | Task is being marked as completed | Yes |

Events that can block allow hooks to prevent the action from proceeding. Events
that cannot block still allow hooks to observe, log, inject context, or provide
feedback.

### Event-Specific Input Fields

Every event receives the common fields (`session_id`, `transcript_path`, `cwd`,
`permission_mode`, `hook_event_name`) plus event-specific fields:

| Event | Additional Fields |
|-------|------------------|
| `SessionStart` | `source`, `model`, optionally `agent_type` |
| `UserPromptSubmit` | `prompt` |
| `PreToolUse` | `tool_name`, `tool_input`, `tool_use_id` |
| `PermissionRequest` | `tool_name`, `tool_input`, `permission_suggestions` |
| `PostToolUse` | `tool_name`, `tool_input`, `tool_response`, `tool_use_id` |
| `PostToolUseFailure` | `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt` |
| `Notification` | `message`, `title`, `notification_type` |
| `SubagentStart` | `agent_id`, `agent_type` |
| `SubagentStop` | `agent_id`, `agent_type`, `agent_transcript_path`, `last_assistant_message`, `stop_hook_active` |
| `Stop` | `stop_hook_active`, `last_assistant_message` |
| `TeammateIdle` | `teammate_name`, `team_name` |
| `TaskCompleted` | `task_id`, `task_subject`, `task_description`, `teammate_name`, `team_name` |
| `PreCompact` | `trigger`, `custom_instructions` |
| `SessionEnd` | `reason` |

---

## 3. Hook Types

There are three handler types. Each fills a different niche:

### Command Hooks (`type: "command"`)

Shell commands that receive JSON on stdin, return results via exit code and stdout.
This is the most common type and the only type that supports async execution.

```json
{
  "type": "command",
  "command": "/path/to/script.sh",
  "timeout": 600,
  "async": false
}
```

Command hooks are appropriate when:
- The logic is deterministic (regex match, file existence check, pattern block).
- You need to run external tools (formatters, linters, notification commands).
- You need background execution (`async: true`).

### Prompt Hooks (`type: "prompt"`)

Single-turn LLM evaluation. Claude Code sends the hook input plus your prompt to
a fast model (Haiku by default). The model returns `{"ok": true}` or
`{"ok": false, "reason": "..."}`.

```json
{
  "type": "prompt",
  "prompt": "Evaluate if all tasks are complete: $ARGUMENTS",
  "model": "claude-haiku-4-5-20250315",
  "timeout": 30
}
```

Prompt hooks are appropriate when:
- The decision requires judgment, not a deterministic rule.
- The hook input data alone is sufficient to make the decision.
- You want lightweight LLM evaluation without tool access.

### Agent Hooks (`type: "agent"`)

Multi-turn subagent with tool access (Read, Grep, Glob). Spawns a subagent that
can inspect the codebase for up to 50 turns before returning a decision.

```json
{
  "type": "agent",
  "prompt": "Verify all unit tests pass. Run tests and check results. $ARGUMENTS",
  "timeout": 120
}
```

Agent hooks are appropriate when:
- Verification requires inspecting actual files, running commands, or checking
  code state.
- The hook input data alone is not sufficient -- the agent needs to explore.

### Supported Events by Hook Type

| Hook Type | Supported Events |
|-----------|-----------------|
| `command` | All 14 events |
| `prompt` | PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, UserPromptSubmit, Stop, SubagentStop, TaskCompleted |
| `agent` | Same as prompt hooks |

`TeammateIdle` does not support prompt or agent hooks. `SessionStart`,
`SessionEnd`, `PreCompact`, `Notification`, and `SubagentStart` only support
command hooks.

---

## 4. Matcher Patterns

Matchers filter when hooks fire. Without a matcher, a hook fires on every
occurrence of its event. Matchers are regex strings applied to an event-specific
field.

### Matcher Fields by Event

| Event | Matched Field | Example Patterns |
|-------|--------------|-----------------|
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest` | `tool_name` | `Bash`, `Edit\|Write`, `mcp__.*`, `Notebook.*` |
| `SessionStart` | `source` | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | `reason` | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` |
| `Notification` | `notification_type` | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` |
| `SubagentStart`, `SubagentStop` | `agent_type` | `Bash`, `Explore`, `Plan`, custom agent names |
| `PreCompact` | `trigger` | `manual`, `auto` |
| `UserPromptSubmit`, `Stop`, `TeammateIdle`, `TaskCompleted` | (none) | Always fires; matchers are silently ignored |

### Regex Capabilities

Matchers support full regex syntax:

- `Edit|Write` -- match either tool
- `Notebook.*` -- match any tool starting with "Notebook"
- `mcp__memory__.*` -- match all tools from the memory MCP server
- `mcp__.*__write.*` -- match any write-related tool from any MCP server
- `*`, `""`, or omitted -- match all occurrences

### Wildcard and Omission Semantics

- `"matcher": "*"` -- matches everything
- `"matcher": ""` -- matches everything
- Omitting `matcher` entirely -- matches everything

All three are equivalent. Hooks only skip when a matcher is defined and does not
match the event's filter field.

---

## 5. Resolution Flow

When a hook event fires, Claude Code resolves handlers through this sequence:

1. **Event fires**: Claude Code reaches a lifecycle point (e.g., about to run a
   tool).

2. **Matcher evaluation**: For each registered hook group on that event, Claude
   Code checks the matcher regex against the event's filter field (e.g.,
   `tool_name` for `PreToolUse`).

3. **Handler collection**: All matching hook groups contribute their handlers to
   the execution set.

4. **Deduplication**: Identical handler commands are automatically deduplicated.

5. **Parallel execution**: All matching handlers run in parallel.

6. **Result aggregation**: Claude Code collects exit codes, stdout, and stderr
   from all handlers.

7. **Decision application**: Claude Code applies the combined decisions. For
   blocking events, any single "deny" or "block" decision prevents the action.

### Hook Source Resolution Order

Hooks are collected from multiple sources:

| Source | Scope |
|--------|-------|
| `~/.claude/settings.json` | User-global |
| `.claude/settings.json` | Project, committable |
| `.claude/settings.local.json` | Project, gitignored |
| Managed policy settings | Organization-wide |
| Plugin `hooks/hooks.json` | Per-plugin, when enabled |
| Skill/agent frontmatter | Per-component, while active |

All hooks from all sources are merged and evaluated together. There is no
priority ordering between sources -- if any hook blocks, the action is blocked.

### Snapshot Behavior

Claude Code captures a snapshot of hooks at startup. Direct edits to settings
files during a session do not take effect immediately. If hooks are modified
externally, Claude Code warns the user and requires review in the `/hooks` menu
before changes apply. This prevents malicious or accidental hook modifications
from taking effect mid-session.

---

## 6. Exit Codes and Decision Control

Hooks communicate results through two mechanisms: exit codes for simple allow/block
decisions, and structured JSON on stdout for fine-grained control.

### Exit Code Semantics

| Exit Code | Meaning | Behavior |
|-----------|---------|----------|
| `0` | Success | Action proceeds. Stdout parsed for optional JSON. |
| `2` | Blocking error | Action blocked. Stderr fed back as feedback/error message. |
| Any other | Non-blocking error | Action proceeds. Stderr shown in verbose mode only. |

**Critical rule**: JSON output is only processed on exit 0. If you exit 2, any
JSON on stdout is ignored. Choose one approach per hook: exit codes alone, or
exit 0 with JSON.

### Exit Code 2 Behavior Per Event

| Event | Effect of Exit 2 |
|-------|-----------------|
| `PreToolUse` | Blocks the tool call |
| `PermissionRequest` | Denies the permission |
| `UserPromptSubmit` | Blocks prompt processing, erases the prompt |
| `Stop` | Prevents Claude from stopping, continues conversation |
| `SubagentStop` | Prevents subagent from stopping |
| `TeammateIdle` | Prevents teammate from going idle |
| `TaskCompleted` | Prevents task from being marked completed |
| `PostToolUse` | Shows stderr to Claude (tool already ran) |
| `PostToolUseFailure` | Shows stderr to Claude (tool already failed) |
| `Notification`, `SubagentStart`, `SessionStart`, `SessionEnd`, `PreCompact` | Shows stderr to user only |

### JSON Decision Patterns

Different events use different JSON structures for decision control:

**Universal fields** (all events):

| Field | Default | Description |
|-------|---------|-------------|
| `continue` | `true` | If `false`, Claude stops entirely. Overrides all other decisions. |
| `stopReason` | none | Message shown to user when `continue` is `false` |
| `suppressOutput` | `false` | If `true`, hides stdout from verbose mode |
| `systemMessage` | none | Warning message shown to user |

**Top-level decision pattern** (UserPromptSubmit, PostToolUse, PostToolUseFailure,
Stop, SubagentStop):

```json
{
  "decision": "block",
  "reason": "Explanation shown to Claude"
}
```

**PreToolUse hookSpecificOutput pattern**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Reason text",
    "updatedInput": { "command": "modified command" },
    "additionalContext": "Extra context for Claude"
  }
}
```

Three outcomes: `"allow"` bypasses permission system, `"deny"` prevents the tool
call, `"ask"` prompts the user to confirm.

**PermissionRequest hookSpecificOutput pattern**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow|deny",
      "updatedInput": { "command": "npm run lint" },
      "updatedPermissions": [{ "type": "toolAlwaysAllow", "tool": "Bash" }],
      "message": "Deny reason (deny only)",
      "interrupt": false
    }
  }
}
```

**TeammateIdle and TaskCompleted**: Exit code only, no JSON decision control.

---

## 7. Security Patterns

### Blocking Destructive Commands

The canonical security hook: block `rm -rf`, `DROP TABLE`, or other dangerous
shell commands before they execute.

```bash
#!/bin/bash
# .claude/hooks/block-destructive.sh
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

DANGEROUS_PATTERNS=("rm -rf" "drop table" "truncate table" "format c:" "mkfs")
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qi "$pattern"; then
    echo "Blocked: matches dangerous pattern '$pattern'" >&2
    exit 2
  fi
done

exit 0
```

Register as a `PreToolUse` hook with matcher `Bash`.

### Protecting Sensitive Files

Prevent Claude from reading or writing files that should not be touched:

```bash
#!/bin/bash
# .claude/hooks/protect-files.sh
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/" "credentials" "secrets")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done

exit 0
```

Register as a `PreToolUse` hook with matcher `Edit|Write|Read`.

### Secret Detection

Scan file contents before writes to catch accidentally committed secrets:

```bash
#!/bin/bash
INPUT=$(cat)
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')

if echo "$CONTENT" | grep -qE '(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{48}|ghp_[a-zA-Z0-9]{36})'; then
  echo "Blocked: content appears to contain API keys or tokens" >&2
  exit 2
fi

exit 0
```

Register as a `PreToolUse` hook with matcher `Write`.

### Path Traversal Prevention

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if echo "$FILE_PATH" | grep -q '\.\.'; then
  echo "Blocked: path traversal detected in $FILE_PATH" >&2
  exit 2
fi

exit 0
```

### Security Best Practices Checklist

- Always quote shell variables: `"$VAR"` not `$VAR`.
- Validate and sanitize all input from stdin.
- Use absolute paths for scripts; reference `$CLAUDE_PROJECT_DIR` for project-relative paths.
- Check for `..` in file paths to block traversal.
- Skip `.env`, `.git/`, key files, and credential files.
- Hooks run with the user's full system permissions -- review all hook scripts
  before deployment.

---

## 8. Automation Patterns

### Auto-Format on Save

Run Prettier (or any formatter) after every file edit:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

### Desktop Notifications

Alert the user when Claude needs attention:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

### Context Injection After Compaction

Re-inject critical context that compaction might lose:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use uv, not pip. Run tests before committing. Current sprint: auth refactor.'"
          }
        ]
      }
    ]
  }
}
```

For `SessionStart` and `UserPromptSubmit`, stdout text is added directly to
Claude's context. You can also use the `additionalContext` JSON field for more
structured injection.

### Environment Variable Persistence

`SessionStart` hooks have exclusive access to `CLAUDE_ENV_FILE`. Write `export`
statements to this file and they persist for all subsequent Bash commands in the
session:

```bash
#!/bin/bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
  echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
fi
exit 0
```

### Command Logging

Log every Bash command Claude executes:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' >> ~/.claude/command-log.txt"
          }
        ]
      }
    ]
  }
}
```

### Quality Gate on Stop

Prevent Claude from finishing until all tasks are verified:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete: $ARGUMENTS. Respond with {\"ok\": false, \"reason\": \"what remains\"} if incomplete."
          }
        ]
      }
    ]
  }
}
```

---

## 9. Plugin Hooks

Plugins can bundle hooks in `hooks/hooks.json` at the plugin root. When a plugin
is enabled, its hooks merge with user and project hooks.

### hooks.json Format

```json
{
  "description": "Automatic code formatting",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The optional top-level `description` field documents the plugin's hooks.

### `${CLAUDE_PLUGIN_ROOT}` Variable

Always use `${CLAUDE_PLUGIN_ROOT}` for paths to scripts bundled with a plugin.
This variable resolves to the absolute path of the plugin directory regardless of
installation location.

Installed plugins are copied to `~/.claude/plugins/cache`, so relative paths or
paths that traverse outside the plugin directory (`../shared-utils`) will not work
after installation. If a plugin needs external files, create symbolic links within
the plugin directory -- symlinks are honored during the copy process.

### Plugin Hook Behavior

- Plugin hooks appear as `[Plugin]` in the `/hooks` menu and are read-only.
- Plugin hooks are merged with user, project, and managed hooks.
- Plugin hooks follow the same snapshot behavior as all other hooks.
- Hooks can also be defined inline in `plugin.json` under the `hooks` key, or
  referenced via a path string in `plugin.json`.

### Environment Variables for Scripts

| Variable | Description |
|----------|-------------|
| `${CLAUDE_PLUGIN_ROOT}` | Plugin root directory (for plugin hooks) |
| `$CLAUDE_PROJECT_DIR` | Project root directory (for project hooks) |
| `$CLAUDE_CODE_REMOTE` | Set to `"true"` in remote web environments |
| `$CLAUDE_ENV_FILE` | Path for persisting env vars (SessionStart only) |

---

## 10. Skill and Agent Frontmatter Hooks

Skills and subagents can define hooks directly in their YAML frontmatter. These
hooks are scoped to the component's lifecycle and only run while that component
is active.

### Skill Frontmatter Example

```yaml
---
name: secure-operations
description: Perform operations with security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

### Agent Frontmatter Example

Agents use the same format. One key difference: `Stop` hooks in agent frontmatter
are automatically converted to `SubagentStop` since that is the event that fires
when a subagent completes.

### The `once` Field

Skill frontmatter hooks support a `once` field. When set to `true`, the hook runs
only once per session and is then removed. This is useful for one-time setup or
validation. The `once` field is available for skills only, not agents.

### Lifecycle Scoping

- Hooks defined in frontmatter are registered when the skill or agent activates.
- They are cleaned up when the component finishes.
- All hook events are supported in frontmatter.
- The same configuration format used in settings files applies.

---

## 11. Async Hooks

By default, hooks block Claude's execution until they complete. For long-running
operations, set `"async": true` to run the hook in the background.

### Configuration

```json
{
  "type": "command",
  "command": "/path/to/run-tests.sh",
  "async": true,
  "timeout": 300
}
```

### Execution Model

1. Claude Code starts the hook process and continues immediately.
2. The hook receives the same JSON input via stdin as a synchronous hook.
3. When the background process exits, if it produced `systemMessage` or
   `additionalContext` in its JSON output, that content is delivered on the
   next conversation turn.
4. If the session is idle, delivery waits until the next user interaction.

### Constraints

- Only `type: "command"` hooks support `async`. Prompt and agent hooks cannot
  run asynchronously.
- Async hooks cannot block or return decisions. The triggering action has already
  proceeded by the time the hook completes.
- Each execution creates a separate background process with no deduplication
  across multiple firings.
- Default timeout is 10 minutes (same as sync hooks) unless overridden.

### Use Case: Background Test Suite

```bash
#!/bin/bash
# .claude/hooks/run-tests-async.sh
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" != *.ts && "$FILE_PATH" != *.js ]]; then
  exit 0
fi

RESULT=$(npm test 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "{\"systemMessage\": \"Tests passed after editing $FILE_PATH\"}"
else
  echo "{\"systemMessage\": \"Tests failed after editing $FILE_PATH: $RESULT\"}"
fi
```

---

## 12. MCP Tool Hooks

MCP (Model Context Protocol) server tools appear as regular tools in tool events,
using the naming pattern `mcp__<server>__<tool>`. Hooks can match them the same
way they match built-in tools.

### Naming Pattern

| MCP Tool | Server | Tool |
|----------|--------|------|
| `mcp__memory__create_entities` | memory | create_entities |
| `mcp__filesystem__read_file` | filesystem | read_file |
| `mcp__github__search_repositories` | github | search_repositories |

### Matcher Patterns

- `mcp__memory__.*` -- all tools from the memory server
- `mcp__.*__write.*` -- any write-related tool from any server
- `mcp__github__.*` -- all GitHub server tools
- `mcp__.*` -- all MCP tools from any server

### Example: Log and Validate MCP Operations

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__memory__.*",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Memory operation initiated' >> ~/mcp-operations.log"
          }
        ]
      },
      {
        "matcher": "mcp__.*__write.*",
        "hooks": [
          {
            "type": "command",
            "command": "/home/user/scripts/validate-mcp-write.py"
          }
        ]
      }
    ]
  }
}
```

### PostToolUse MCP Output Modification

`PostToolUse` hooks for MCP tools support `updatedMCPToolOutput`, which replaces
the tool's output with the provided value. This is unique to MCP tools and not
available for built-in tools.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "updatedMCPToolOutput": "Sanitized output here"
  }
}
```

---

## 13. Anti-Patterns

### Infinite Stop Hook Loops

A `Stop` hook that always blocks creates an infinite loop where Claude never stops.
Always check `stop_hook_active`:

```bash
#!/bin/bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0  # Allow Claude to stop on the second pass
fi
# ... actual validation logic
```

### Mixing Exit Codes and JSON

Exiting with code 2 and printing JSON to stdout is contradictory. Claude Code
ignores JSON on exit 2 and only reads stderr. Pick one approach:
- Exit 2 + stderr message for simple blocking.
- Exit 0 + JSON stdout for structured decisions.

### Shell Profile Pollution

If `~/.zshrc` or `~/.bashrc` contains unconditional `echo` statements, they
pollute hook stdout and break JSON parsing:

```
Shell ready on arm64
{"decision": "block", "reason": "Not allowed"}
```

Fix: wrap echo statements in an interactive-shell guard:

```bash
if [[ $- == *i* ]]; then
  echo "Shell ready"
fi
```

### Using PermissionRequest in Non-Interactive Mode

`PermissionRequest` hooks do not fire in headless/non-interactive mode (`claude -p`).
Use `PreToolUse` hooks instead for automated permission decisions.

### Blocking on Non-Blockable Events

Returning exit 2 from `PostToolUse`, `Notification`, `SubagentStart`,
`SessionStart`, `SessionEnd`, or `PreCompact` does not block anything -- the
action has already happened or cannot be prevented. The stderr is shown to the
user or to Claude, but the action proceeds regardless.

### Heavyweight Sync Hooks

Running a full test suite synchronously on every `PostToolUse` event blocks
Claude from continuing. Use `async: true` for long-running operations, or
limit the matcher to specific tools to reduce frequency.

### Unquoted Variables

Using `$FILE_PATH` instead of `"$FILE_PATH"` in shell scripts causes word
splitting on paths with spaces. Always double-quote shell variable expansions.

### Relying on Matcher for Security

Matchers are convenience filters, not security boundaries. A matcher like `Bash`
filters the tool name, but the tool name comes from Claude's internal event -- it
is not user-controlled. However, tool *inputs* (like the `command` field) should
always be validated within the hook script itself.

---

## 14. Design Checklist

Use this checklist when designing a new hook:

### Purpose

- [ ] Is this logic deterministic (use command hook) or judgment-based (use
      prompt/agent hook)?
- [ ] Does the hook need to block an action, or just observe/log?
- [ ] If blocking, is the event actually blockable? (See the "Can Block?" column
      in section 2.)

### Configuration

- [ ] Is the event type correct? (`PreToolUse` for before, `PostToolUse` for
      after, etc.)
- [ ] Is the matcher pattern specific enough to avoid unnecessary firings?
- [ ] Is the matcher pattern broad enough to catch all relevant cases?
- [ ] Does the hook need to run on all occurrences, or should it use `once: true`?

### Implementation

- [ ] Does the script read from stdin (not command-line arguments)?
- [ ] Does the script use `jq` (or equivalent) for JSON parsing?
- [ ] Are all shell variables double-quoted?
- [ ] Does the script use absolute paths or `$CLAUDE_PROJECT_DIR` /
      `${CLAUDE_PLUGIN_ROOT}`?
- [ ] Does the script validate inputs before acting on them?
- [ ] Does the script handle the case where expected fields are missing
      (`// empty` in jq)?

### Exit Code / Output

- [ ] Does exit 0 mean "allow"?
- [ ] Does exit 2 write a reason to stderr?
- [ ] If using JSON output, does the script exit 0 (not 2)?
- [ ] Is stdout clean (no stray echo statements from the shell profile)?
- [ ] For `Stop`/`SubagentStop` hooks: does it check `stop_hook_active` to
      prevent infinite loops?

### Performance

- [ ] Is the hook fast enough for synchronous execution, or should it use
      `async: true`?
- [ ] Is the timeout set appropriately? (Defaults: 600s command, 30s prompt,
      60s agent.)
- [ ] Will the hook fire too frequently? (e.g., on every tool call vs. only
      on file writes.)

### Scope

- [ ] Should this hook be user-global (`~/.claude/settings.json`), project-level
      (`.claude/settings.json`), or local (`.claude/settings.local.json`)?
- [ ] If bundled with a plugin, is the path using `${CLAUDE_PLUGIN_ROOT}`?
- [ ] If defined in skill/agent frontmatter, is it scoped correctly to the
      component's lifecycle?

### Security

- [ ] Does the hook validate file paths for traversal (`..`)?
- [ ] Does the hook skip sensitive files (`.env`, credentials, `.git/`)?
- [ ] Has the hook script been reviewed and tested manually?

---

## 15. Cross-References

### Within This Repository

- `docs/claude-docs/claude_docs_hooks_reference.md` -- Full upstream hooks
  reference (event schemas, JSON formats, advanced features).
- `docs/claude-docs/claude_docs_hooks-guide.md` -- Upstream hooks guide
  (getting started, common use cases, troubleshooting).
- `docs/claude-docs/claude_docs_plugins-reference.md` -- Plugin system reference
  including plugin hooks, `hooks.json` format, and `${CLAUDE_PLUGIN_ROOT}`.
- `docs/claude-docs/claude_docs_settings.md` -- Settings file resolution and
  configuration scopes.
- `docs/claude-docs/claude_docs_permissions.md` -- Permission modes referenced
  by the `permission_mode` input field.
- `docs/claude-docs/claude_docs_sub-agents.md` -- Subagent system, relevant to
  `SubagentStart`/`SubagentStop` hooks and agent-based hooks.
- `docs/claude-docs/claude_docs_mcp.md` -- MCP server integration, relevant to
  MCP tool hook matchers.

### External References

- [Hooks Reference](https://code.claude.com/docs/en/hooks) -- Canonical upstream
  documentation.
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide) -- Upstream
  getting-started guide.
- [Bash Command Validator](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py) --
  Reference implementation from Anthropic.

### Related Concepts

- **Skills vs. Hooks**: Skills give Claude instructions and executable commands.
  Hooks enforce behavior deterministically. Use skills when you want Claude to
  learn a pattern; use hooks when you want to guarantee an action always happens.
- **Plugins vs. Hooks**: Plugins package skills, agents, hooks, MCP servers, and
  LSP servers into distributable units. Hooks are one component of a plugin.
- **CLAUDE.md vs. SessionStart hooks**: CLAUDE.md provides static context loaded
  every session. SessionStart hooks provide dynamic context that requires script
  execution (e.g., `git log`, API calls, environment setup).
- **PreToolUse vs. PermissionRequest**: Both fire before a tool runs, but
  `PreToolUse` fires on every tool call regardless of permission status.
  `PermissionRequest` fires only when a permission dialog is about to be shown.
  Use `PreToolUse` for headless/non-interactive environments.

---

## Appendix: Tool Input Schemas for PreToolUse

For reference, the tool input fields available in `PreToolUse` hooks for each
built-in tool:

| Tool | Key Fields |
|------|------------|
| `Bash` | `command`, `description`, `timeout`, `run_in_background` |
| `Write` | `file_path`, `content` |
| `Edit` | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Read` | `file_path`, `offset`, `limit` |
| `Glob` | `pattern`, `path` |
| `Grep` | `pattern`, `path`, `glob`, `output_mode`, `-i`, `multiline` |
| `WebFetch` | `url`, `prompt` |
| `WebSearch` | `query`, `allowed_domains`, `blocked_domains` |
| `Task` | `prompt`, `description`, `subagent_type`, `model` |
