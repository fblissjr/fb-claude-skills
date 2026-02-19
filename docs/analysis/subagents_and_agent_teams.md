last updated: 2026-02-19

# Subagents and Agent Teams

Reference for Claude Code's delegation architecture: subagents (single-session delegation), custom agent creation, tool control, hooks, persistent memory, and agent teams (multi-session coordination).

---

## 1. Overview

Subagents are specialized AI assistants that run in isolated context windows with custom system prompts, specific tool access, and independent permissions. When Claude encounters a task matching a subagent's description, it delegates. The subagent works independently and returns results.

**Why subagents exist.** The core problem is context management. A single conversation accumulates tool output and intermediate reasoning that dilutes signal-to-noise. Subagents preserve context (verbose output stays isolated), enforce constraints (restricted tool access), reuse configurations (user-level agents across projects), specialize behavior (focused system prompts), and control costs (routing to cheaper models for read-only work).

**The delegation model.** Claude uses each subagent's `description` field to decide when to delegate. The subagent runs in its own context window with its own system prompt, works over many tool-use turns, then returns results. Key constraint: **subagents cannot spawn other subagents**. Chain them from the main conversation or use skills instead.

**Subagents vs. agent teams.** Subagents operate within a single session. Agent teams (experimental) coordinate across separate sessions, each with an independent context window. Use subagents for tasks within a conversation; agent teams for sustained parallelism exceeding a single context window.

---

## 2. Built-in Agents

Claude Code includes built-in subagents that it uses automatically. Each inherits parent permissions with additional tool restrictions.

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| **Explore** | Haiku | Read-only (Write/Edit denied) | File discovery, code search, codebase exploration. Specifies thoroughness: `quick`, `medium`, or `very thorough` |
| **Plan** | Inherits | Read-only (Write/Edit denied) | Codebase research for planning. Prevents infinite nesting while gathering context |
| **General-purpose** | Inherits | All tools | Complex research, multi-step operations, code modifications |
| **Bash** | Inherits | Bash | Running terminal commands in a separate context |
| **statusline-setup** | Sonnet | -- | Configuring status line via `/statusline` |
| **Claude Code Guide** | Haiku | -- | Answering questions about Claude Code features |

**Why Explore uses Haiku**: Read-only exploration does not need deep reasoning. Haiku is cheaper and faster, and context isolation keeps verbose search results out of the main window.

---

## 3. Creating Custom Agents

Subagents are Markdown files with YAML frontmatter (configuration) and a body (system prompt). The subagent receives only this system prompt plus basic environment details, not the full Claude Code system prompt.

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---
You are a code reviewer. Analyze code and provide actionable feedback.
```

**File locations** (higher priority wins when names collide):

| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag (JSON) | Current session only | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All your projects | 3 |
| Plugin's `agents/` directory | Where plugin is enabled | 4 (lowest) |

**CLI-defined agents** are passed as JSON via `--agents`:

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

They exist only for that session. The `prompt` field equals the markdown body in file-based agents. The `/agents` command provides an interactive interface for creating, editing, and managing agents. Subagents load at session start; manual file additions require a restart or `/agents` to take effect.

---

## 4. Agent Frontmatter Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Unique identifier (lowercase letters and hyphens) |
| `description` | Yes | string | When Claude should delegate. Used for auto-delegation decisions |
| `tools` | No | string/array | Tools the subagent can use. Inherits all if omitted. Supports `Task(agent_type)` syntax |
| `disallowedTools` | No | string/array | Tools to deny. Removed from inherited or specified list |
| `model` | No | string | `sonnet`, `opus`, `haiku`, or `inherit` (default) |
| `permissionMode` | No | string | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, or `plan` |
| `maxTurns` | No | integer | Maximum agentic turns before the subagent stops |
| `skills` | No | array | Skills injected into context at startup. Full content loaded, not just referenced |
| `mcpServers` | No | object/array | MCP servers available. Server name references or inline definitions |
| `hooks` | No | object | Lifecycle hooks scoped to this subagent |
| `memory` | No | string | Persistent memory scope: `user`, `project`, or `local` |

---

## 5. Tool Control

**Allowlist**: The `tools` field defines available tools. If omitted, inherits all from main conversation (including MCP tools).

**Denylist**: `disallowedTools` removes tools from whatever set the subagent would otherwise have.

**Filtering order**: (1) Start with `tools` or inherited set. (2) Remove `disallowedTools`. (3) Result is the final tool set.

**Restricting subagent spawning**: When an agent runs as main thread via `claude --agent`, `Task(worker, researcher)` in `tools` restricts which subagent types can be spawned (allowlist). `Task` without parentheses allows all. Omitting `Task` prevents all spawning. This only applies to `--agent` mode; regular subagents cannot spawn other subagents.

**Disabling agents via permissions**: Add `Task(Explore)` or `Task(my-agent)` to `permissions.deny` in settings, or use `--disallowedTools "Task(Explore)"` on the CLI.

**Conditional validation**: For finer control, use `PreToolUse` hooks. This example allows Bash but blocks SQL write operations:

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
```

The hook receives JSON on stdin with `tool_input.command`, validates the command, and exits with code 2 to block (stderr becomes Claude's feedback) or code 0 to allow.

---

## 6. Model Selection

| Value | Behavior | Use case |
|-------|----------|----------|
| `haiku` | Fastest, cheapest | Read-only exploration, scanning, simple searches |
| `sonnet` | Balanced capability/speed | Code analysis, suggestions, moderate reasoning |
| `opus` | Highest capability, slower | Deep reasoning, complex multi-step problem solving |
| `inherit` | Same as main conversation | Default; use when task complexity matches parent |

`CLAUDE_CODE_SUBAGENT_MODEL` overrides the model for all subagents regardless of individual settings.

---

## 7. Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Standard permission checking with prompts |
| `acceptEdits` | Auto-accept file edits |
| `dontAsk` | Auto-deny prompts (explicitly allowed tools still work) |
| `bypassPermissions` | Skip all checks (use in sandboxed environments only) |
| `plan` | Read-only exploration, no modifications |

**Inheritance**: If the parent uses `bypassPermissions`, it takes precedence and cannot be overridden. For all other parent modes, the subagent's `permissionMode` takes effect.

**Background subagents**: Before launching, Claude Code prompts for all needed permissions upfront. Once running, the subagent auto-denies anything not pre-approved. MCP tools are unavailable in background subagents. Failed background agents can be resumed in the foreground.

---

## 8. Skills Injection

The `skills` field injects full skill content into the subagent's system prompt at startup. Subagents do not inherit skills from the parent conversation; list them explicitly.

```yaml
skills:
  - api-conventions
  - error-handling-patterns
```

This is the inverse of `context: fork` in a skill. With `skills` in a subagent, the subagent controls the system prompt and loads skill content. With `context: fork`, the skill injects content into the specified agent.

Use when: the subagent needs conventions or domain knowledge from the start, or you want to avoid spending turns discovering skill files.

---

## 9. Persistent Memory

The `memory` field gives a subagent a persistent directory that survives across conversations.

| Scope | Location | Use when |
|-------|----------|----------|
| `user` | `~/.claude/agent-memory/<name>/` | Knowledge persists across all projects (recommended default) |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, shareable via version control |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, not checked in |

**Runtime behavior**: (1) System prompt includes memory read/write instructions. (2) First 200 lines of `MEMORY.md` are included in prompt. (3) Read, Write, Edit tools are auto-enabled for memory management.

**Tip**: Include maintenance instructions in the system prompt so the agent proactively updates its knowledge base with codepaths, patterns, and architectural decisions.

---

## 10. Hooks for Agents

Two distinct hook surfaces exist for agents.

### Hooks in subagent frontmatter

Run only while the specific subagent is active. Cleaned up when it finishes. All standard hook events are supported. `Stop` hooks in frontmatter are converted to `SubagentStop` at runtime.

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
```

### Project-level subagent lifecycle hooks

Configured in `settings.json`. Fire in the main session.

| Event | Matcher input | When it fires |
|-------|---------------|---------------|
| `SubagentStart` | Agent type name | When a subagent begins execution |
| `SubagentStop` | Agent type name | When a subagent completes |

Example: set up a database connection when `db-agent` starts, clean up when any agent stops:

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db-connection.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup-db-connection.sh" }
        ]
      }
    ]
  }
}
```

Use cases: resource setup/teardown, audit logging, output validation, external notifications.

---

## 11. Agent Teams (Experimental)

Agent teams coordinate across separate sessions, each with its own independent context window. Distinct from subagents, which work within a single session.

**Enable**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

**Key concepts**:
- **Teammates**: Separate Claude Code sessions with independent context, tools, and working directory
- **Shared task list**: `CLAUDE_CODE_TASK_LIST_ID` set to the same value across instances coordinates tasks
- **Team name**: `CLAUDE_CODE_TEAM_NAME` identifies team membership
- **Teammate mode**: `--teammate-mode` controls display (`auto`, `in-process`, `tmux`)
- **Plan approval**: `CLAUDE_CODE_PLAN_MODE_REQUIRED` auto-set on teammates requiring plan approval

| Criterion | Subagents | Agent Teams |
|-----------|-----------|-------------|
| Context isolation | Separate context window, shared session | Fully separate sessions |
| Parallelism | Background possible, shared lifecycle | True independent parallelism |
| Communication | Return results to main conversation | Shared task list |
| Context limits | Constrained by parent's budget | Full context per teammate |

### TeammateIdle hook

Fires when a teammate is about to go idle after finishing its turn. Use this to enforce quality gates.

- No matcher support (fires on every occurrence)
- Does not support prompt-based or agent-based hook types
- Exit code 2 prevents idling and feeds stderr as feedback
- Input includes `teammate_name` and `team_name`

```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/check-build-artifact.sh" }
        ]
      }
    ]
  }
}
```

### TaskCompleted hook

Fires when a task is marked completed, including when a teammate finishes with in-progress tasks. Exit code 2 prevents the task from being marked complete and feeds stderr as feedback to the model.

---

## 12. Real Implementation Analysis

The `plugin-toolkit` plugin provides two agents that demonstrate real-world patterns.

### plugin-scanner (`plugin-toolkit/agents/plugin-scanner.md`)

**Purpose**: Scan a plugin directory and return a structured inventory of commands, traits, hooks, skills, agents, and configuration.

**Process**: Seven sequential steps -- verify plugin structure, scan plugin.json, inventory commands (glob `commands/*.md`, extract frontmatter), inventory traits, inventory hooks (read hooks.json), inventory skills (glob `skills/*/SKILL.md`), inventory agents (glob `agents/*.md`).

**Output contract**: Standardized markdown with metadata section, directory tree, and one table per component type (commands, traits, hooks, skills, agents), plus an observations section.

**Strengths**:
- Single responsibility: scan only, no evaluation or recommendations
- Consistent output format that downstream consumers can parse
- Defined input/output contract (plugin path in, structured markdown out)
- Reused by three skill commands (`analyze`, `polish`, `feature`)

**Gaps**:
- No YAML frontmatter (`name`, `description`, `tools`, `model`). Claude cannot auto-discover or auto-delegate to it. It functions as a documented process rather than a true subagent definition
- No tool restrictions. A read-only scanner should explicitly deny Write and Edit
- No model specification. A scanner could use Haiku for cost efficiency

### quality-checker (`plugin-toolkit/agents/quality-checker.md`)

**Purpose**: Evaluate a plugin against quality criteria. Produces 1-10 category ratings, overall weighted score, and prioritized recommendations.

**Scoring model**: Six categories with explicit weights:

| Category | Weight |
|----------|--------|
| Commands | 25% |
| Hooks | 20% |
| Documentation | 20% |
| Skills/Agents | 15% |
| Code Quality | 10% |
| Integration | 10% |

Rating scale maps scores to labels: 9-10 Excellent, 7-8 Good, 5-6 Adequate, 3-4 Needs Work, 1-2 Poor.

**Strengths**:
- Depends on plugin-scanner output, creating a clean pipeline
- Reproducible evaluation with explicit weights and criteria
- Priority-grouped recommendations (Critical/High/Medium/Low)
- External reference to `quality-checklist.md` keeps the agent prompt focused

**Gaps**:
- Same frontmatter issue as plugin-scanner: not auto-discoverable
- No tool restrictions (should deny Write/Edit)
- Could benefit from `memory: project` to track quality scores over time

### Pipeline pattern

```
plugin-scanner  -->  quality-checker  -->  analysis output
(scan structure)     (evaluate quality)    (SKILL_REVIEW.md)
```

The skill (`SKILL.md`) orchestrates this: it knows *what* to do, the agents know *how*.

---

## 13. Delegation Design Patterns

**Delegate when**: verbose output (test suites, logs), enforcing tool restrictions, self-contained work returning a summary, parallel independent research.

**Keep inline when**: frequent back-and-forth, shared context across phases, quick targeted changes, latency-sensitive work.

**Task granularity**: Too broad ("fix all bugs") drowns the subagent. Too narrow ("read line 42") wastes delegation overhead. Right size: "Run tests and report only failures with error messages."

**Result patterns**:

- **Summarize**: The most common. Subagent does verbose work and returns a condensed summary.

  ```
  Use a subagent to run the test suite and report only failing tests with error messages
  ```

- **Parallel then synthesize**: Multiple subagents for independent research, then combine.

  ```
  Research the authentication, database, and API modules in parallel using separate subagents
  ```

- **Chain**: Sequential subagents building on previous results.

  ```
  Use the code-reviewer to find performance issues, then use the optimizer to fix them
  ```

**Resumption**: Ask Claude to resume an existing subagent to continue with full context history. Resumed subagents retain all tool calls and reasoning. Transcripts stored at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`, persisting independently of main conversation compaction.

**Auto-compaction**: Subagents support auto-compaction at ~95% capacity (configurable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`). This applies independently of the main conversation.

**Context budget**: Many subagents returning detailed results consume main conversation context. For sustained parallelism, use agent teams instead.

---

## 14. Agent Design Checklist

### Identity and discovery

- [ ] `name` uses lowercase letters and hyphens only
- [ ] `description` clearly states when Claude should delegate
- [ ] `description` includes natural trigger phrases users would say
- [ ] `description` is under 1024 characters

### Tool access

- [ ] `tools` explicitly set if the agent should be restricted
- [ ] Read-only agents deny Write and Edit
- [ ] Bash agents have `PreToolUse` hooks for command validation if needed
- [ ] MCP servers listed in `mcpServers` if needed

### Model selection

- [ ] Read-only exploration agents use `haiku`
- [ ] Agents requiring reasoning use `sonnet` or `inherit`
- [ ] `opus` reserved for deep multi-step reasoning
- [ ] Model choice documented with rationale

### Permission and safety

- [ ] `permissionMode` set intentionally (not left to default when specific mode needed)
- [ ] `bypassPermissions` only used in sandboxed environments
- [ ] Background execution pre-approval considered
- [ ] `maxTurns` set if unbounded execution is a risk

### System prompt quality

- [ ] Describes agent's role and expertise
- [ ] Includes clear process (numbered steps)
- [ ] Specifies expected output format
- [ ] Focused on one concern, not a kitchen sink

### Integration and testing

- [ ] Correct directory for scope (project, user, or plugin)
- [ ] Works with other agents in the pipeline
- [ ] Skills listed if agent needs domain knowledge
- [ ] Memory scope set if cross-session learning is beneficial
- [ ] Manually invoked to verify behavior
- [ ] Output consistent and parseable by downstream consumers

---

## 15. Cross-references

**Within this repo**:
- `docs/analysis/claude_skills_best_practices_guide_full_report.md` -- Skills best practices intersecting with agent design
- `docs/analysis/abstraction_analogies.md` -- "Selection under constraint" framework applies to delegation
- `plugin-toolkit/agents/plugin-scanner.md` -- Real scanner agent
- `plugin-toolkit/agents/quality-checker.md` -- Real quality evaluator agent
- `plugin-toolkit/skills/plugin-toolkit/SKILL.md` -- Skill orchestrating the agent pipeline

**External documentation**:
- [Subagents](https://code.claude.com/docs/en/sub-agents), [Agent Teams](https://code.claude.com/docs/en/agent-teams), [Hooks](https://code.claude.com/docs/en/hooks), [Permissions](https://code.claude.com/docs/en/permissions), [Skills](https://code.claude.com/docs/en/skills), [Settings](https://code.claude.com/docs/en/settings), [Plugins Reference](https://code.claude.com/docs/en/plugins-reference)

**Captured docs**: `docs/claude-docs/claude_docs_sub-agents.md`, `claude_docs_settings.md`, `claude_docs_permissions.md`, `claude_docs_hooks-guide.md`, `claude_docs_hooks_reference.md`, `claude_docs_plugins-reference.md`, `claude_docs_cli-reference_reference.md`
