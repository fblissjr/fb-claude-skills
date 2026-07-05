---
name: model-routing
description: Opt the current project into down-tier model delegation by installing a .claude/rules/model-delegation.md rule, optionally with pre-shaped .claude/agents/ definitions (fast-executor, task-coder). The rule tells Claude to route well-specified data and coding tasks to a cheaper model in a subagent, keeping judgment-heavy work in the main loop, and to record outcomes via agent-state when available. Use when the user says "set up model routing", "set up model delegation", "use cheaper models for subagents", "delegate to a lower-power model", or wants to remove or update that rule.
metadata:
  author: Fred Bliss
  version: 0.2.0
  last_verified: 2026-07-05
---

Install, update, or remove a per-project model-delegation rule. The rule is a plain `.claude/rules/` file: it loads at session start in that project only, needs no plugin installed to keep working, and is removed by deleting the file.

Design rationale: [VISION.md "route to the cheapest capable model"](https://github.com/fblissjr/fb-claude-skills/blob/main/VISION.md) — decomposition quality and model tiering are complements; well-scoped leaf tasks don't need the frontier model.

## Install

1. Determine the project root: the git repository root, or the working directory if not in a git repo. If the user names a different target project, use that.
2. Read `references/model-delegation.md` (relative to this skill) and write its content **verbatim** to `<project-root>/.claude/rules/model-delegation.md`, creating `.claude/rules/` if needed. Verbatim copy keeps installs identical across projects — do not regenerate or paraphrase the rule text.
3. If the target file already exists and differs, show the user the diff and ask before overwriting — it may carry local edits.
4. Ask the user whether to also install the pre-shaped delegation agents (or install them without asking if they said "with agents"). If yes, copy verbatim: `references/agents/fast-executor.md` and `references/agents/task-coder.md` to `<project-root>/.claude/agents/`, same diff-and-confirm treatment for existing files. These give delegation targets tailored system prompts (execute-to-spec, report deviations, don't expand scope) instead of a bare model override; the rule prefers them automatically when present.
5. Tell the user: the rule loads automatically at the next session start in that project (agent definitions also load at session start). For the current session, adopt the rule's behavior immediately since you have just read it.

## Update

Same as install; step 3's diff-and-confirm handles the existing files.

## Remove

Delete `<project-root>/.claude/rules/model-delegation.md`, and `<project-root>/.claude/agents/fast-executor.md` / `task-coder.md` if they were installed. Nothing else to clean up.

## What the rule says

Delegation criteria in brief (full text in `references/model-delegation.md`): route tasks that are well-specified, mechanical, and verifiable to the cheapest capable model in a subagent; keep design, ambiguity, user interaction, and verification of returned work in the main loop on the strongest model. Tiers are named only as examples so the rule survives model-lineup changes. If the `agent-state` CLI is available, verified outcomes are recorded (`agent-state delegation record ...`) so acceptance rates per model/domain can tune the criteria over time — recording is optional and never blocks work.
