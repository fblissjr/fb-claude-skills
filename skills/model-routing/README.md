last updated: 2026-07-05

# model-routing

Opt a project into down-tier model delegation. One skill installs a `.claude/rules/model-delegation.md` file into the current project; from the next session on, Claude routes well-specified data and coding tasks to a cheaper model in a subagent and keeps judgment-heavy work in the main loop.

Why a rules file and not a hook: the rule is plain data in the target project. It keeps working if this plugin is uninstalled, it's inspectable and locally editable, and removal is deleting one file. Opt-in is per project — invoke the skill only where you want the behavior. Design rationale: [VISION.md "route to the cheapest capable model"](../../VISION.md).

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install model-routing@fb-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [model-routing](skills/model-routing/SKILL.md) | Install, update, or remove the per-project model-delegation rule. Verbatim-copies the rule template from `references/model-delegation.md`; diffs and confirms before overwriting local edits. |

## Invocation

```
/model-routing:model-routing            # install the rule in the current project
"set up model delegation here"          # natural-language trigger
"remove the model delegation rule"      # uninstall from the current project
```

## What the installed rule does

The rule states delegation criteria in terms of task properties, not a fixed model table:

- Delegate to a subagent on the cheapest capable model when a task is **well-specified**, **mechanical or pattern-bound**, and **verifiable**.
- Keep design decisions, ambiguity, user interaction, and verification of delegated results in the main loop on the strongest model.
- Current tiers (haiku for mechanical work, sonnet for standard coding/data) appear only as examples, so the rule survives model-lineup changes.
