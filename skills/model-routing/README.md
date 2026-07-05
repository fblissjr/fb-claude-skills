last updated: 2026-07-05

# model-routing

Opt a project into down-tier model delegation. One skill installs a `.claude/rules/model-delegation.md` file into the current project; from the next session on, Claude routes well-specified data and coding tasks to a cheaper model in a subagent and keeps judgment-heavy work in the main loop.

The install is layered, and the base rule is fully **standalone** — no external tool, no CLI:

- **Base rule** (always): the delegation behavior. Complete on its own.
- **Agents** (opt-in): pre-shaped `.claude/agents/` definitions — `fast-executor` (haiku, mechanical work) and `task-coder` (sonnet, standard coding/data) — so delegation targets carry tailored execute-to-spec system prompts instead of a bare model override.
- **Feedback** (opt-in): an `agent-state` outcome-recording section appended to the rule. Only worth adding where the `agent-state` CLI is installed — it's kept out of the base because it's always-loaded text that only pays off with the CLI present.

Why a rules file and not a hook: the rule is plain data in the target project. It keeps working if this plugin is uninstalled, it's inspectable and locally editable, and removal is deleting one file. Opt-in is per project — invoke the skill only where you want the behavior. Design rationale: [VISION.md "route to the cheapest capable model"](../../VISION.md).

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install model-routing@fb-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [model-routing](skills/model-routing/SKILL.md) | Install, update, or remove the per-project model-delegation rule (standalone base), optionally with the `fast-executor` / `task-coder` agent definitions and an agent-state feedback layer. Verbatim-copies templates from `references/`; diffs and confirms before overwriting local edits. |

## Invocation

```
/model-routing:model-routing            # install the standalone base rule
"set up model delegation here"          # natural-language trigger
"set up model delegation with agents"   # base rule + fast-executor / task-coder agents
"set up model delegation with feedback" # base rule + agent-state recording layer
"remove the model delegation rule"      # uninstall from the current project
```

## What the installed rule does

The rule states delegation criteria in terms of task properties, not a fixed model table:

- Delegate to a subagent on the cheapest capable model when a task is **well-specified**, **mechanical or pattern-bound**, and **verifiable**.
- Keep design decisions, ambiguity, user interaction, and verification of delegated results in the main loop on the strongest model.
- Current tiers (haiku for mechanical work, sonnet for standard coding/data) appear only as examples, so the rule survives model-lineup changes.
- Prefer the pre-shaped `fast-executor` / `task-coder` agents when the project has them installed.

With the optional **feedback layer** added, the rule also records each verified delegation via `agent-state delegation record ...`, and `agent-state delegation stats` shows acceptance rates per model/domain — the loop for tuning what gets delegated. The `agent-state` package lives in this repo under `tools/agent-state/`; without it installed, leave the feedback layer off.
