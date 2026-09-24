last updated: 2026-09-24

# model-routing

Opt a project into down-tier model delegation. One skill installs a `.claude/rules/model-delegation.md` file into the current project; from the next session on, Claude routes well-specified data and coding tasks to a cheaper model in a subagent and keeps judgment-heavy work in the main loop.

> **Installation is paused as of 2026-08-01.** The rule was removed from all
> eight repos that had it. It is ~1,885 characters of always-loaded text
> asserting a cost/quality tradeoff that has never been measured. The feedback
> layer meant to measure it asked the agent to grade its own work, and was
> removed in 0.5.0.
>
> The skill is now `disable-model-invocation: true`, so it cannot load on
> Claude's judgment — only an explicit `/model-routing:model-routing` reaches it,
> and if invoked it will explain the pause and confirm before writing. Removal
> is unaffected.
>
> What would justify resuming: a definition of a good delegation outcome and a
> way to observe one, per
> [docs/internals/model_routing_flywheel.md](../../docs/internals/model_routing_flywheel.md).

The install is layered, and the base rule is fully **standalone** — no external tool, no CLI:

- **Base rule** (always): the delegation behavior. Complete on its own.
- **Agents** (opt-in): pre-shaped `.claude/agents/` definitions — `fast-executor` (haiku, mechanical work) and `task-coder` (sonnet, standard coding/data) — so delegation targets carry tailored execute-to-spec system prompts instead of a bare model override.

Why a rules file and not a hook: the rule is plain data in the target project. It keeps working if this plugin is uninstalled, it's inspectable and locally editable, and removal is deleting one file. Opt-in is per project — invoke the skill only where you want the behavior. Design rationale: [architecture.md "route to the cheapest capable model"](../../docs/internals/architecture.md).

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install model-routing@fb-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [model-routing](skills/model-routing/SKILL.md) | Install, update, or remove the per-project model-delegation rule (standalone base), optionally with the `fast-executor` / `task-coder` agent definitions. Verbatim-copies templates from `references/`; diffs and confirms before overwriting local edits. |

## Invocation

```
/model-routing:model-routing            # invoke the skill (install is paused, see below)
/model-routing:model-routing remove     # uninstall from the current project
```

Natural-language phrases such as "set up model delegation here" no longer
trigger this skill. It sets `disable-model-invocation: true`, so its description
is not in Claude's context and only an explicit slash command reaches it.

## What the installed rule does

The rule states delegation criteria in terms of task properties, not a fixed model table:

- Delegate to a subagent on the cheapest capable model when a task is **well-specified**, **mechanical or pattern-bound**, and **verifiable**.
- Keep design decisions, ambiguity, user interaction, and verification of delegated results in the main loop on the strongest model.
- Current tiers (haiku for mechanical work, sonnet for standard coding/data) appear only as examples, so the rule survives model-lineup changes.
- Prefer the pre-shaped `fast-executor` / `task-coder` agents when the project has them installed.

The **agent-state feedback layer was removed in 0.5.0.** It appended an outcome-recording section to the rule, telling Claude to run `agent-state delegation record` after verifying each delegation. Three things were wrong with it: the table it wrote to has never existed in the live database, nothing had written to that database since 2026-03-12 (the package was retired outright on 2026-08-02), and the outcome it captured was the orchestrator grading its own delegation. Delegation data is now recovered observationally from session transcripts, which needs no cooperation from the party being measured and backfills retroactively. If a project still carries the section, delete it.

## Related

This plugin routes *down*: well-specified mechanical work goes to a cheaper model in a subagent. Routing *up*, a higher-tier model advising on the current session, is Claude Code's built-in [`/advisor`](https://code.claude.com/docs/en/advisor). This repo's own `advisor` plugin was retired on 2026-09-24 in its favour.
