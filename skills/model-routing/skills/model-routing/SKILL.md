---
name: model-routing
argument-hint: "[install | remove]"
description: Install, update, or remove the per-project down-tier model-delegation rule (.claude/rules/model-delegation.md), optionally with fast-executor / task-coder agent definitions. Installation is currently paused pending measurement, and this skill is user-invoked only -- it will not load on its own judgment.
disable-model-invocation: true
---

> **Status: installation paused (2026-08-01).**
>
> The rule was removed from all eight repos that had it, and should not be
> reinstalled for now. It is 1,885 characters of always-loaded text asserting
> that down-tier delegation improves cost without hurting quality — a claim
> nothing has measured. Until there is evidence, installing it spends context
> budget on an unfalsified belief.
>
> **If invoked, say this and confirm before writing anything.** The removal was
> deliberate and recent; a reinstall silently undoes it.
>
> Removal still works normally and needs no confirmation.
>
> To resume: delete this block and `disable-model-invocation` from the
> frontmatter. What would justify resuming is in
> [docs/internals/model_routing_flywheel.md](https://github.com/fblissjr/fb-claude-skills/blob/main/docs/internals/model_routing_flywheel.md)
> — the rule needs a definition of a good delegation outcome and a way to
> observe one before it earns its place in every session.

Install, update, or remove a per-project model-delegation rule. The rule is a plain `.claude/rules/` file: it loads at session start in that project only, needs no plugin installed to keep working, and is removed by deleting the file.

The install has two independent layers. The **base rule** is standalone — no external tool, no CLI. One layer is opt-in: pre-shaped **agents**. The base is complete on its own.

A third layer, an `agent-state` feedback section, was removed in 0.5.0. It told Claude to record each delegation outcome via a CLI, into a table that never existed in the live database (the whole package was retired on 2026-08-02) — and the outcome it recorded was the orchestrator grading its own delegation. Delegation data is now recovered observationally from session transcripts instead. If a project still carries that section in its installed rule, delete it.

Design rationale: [architecture.md "route to the cheapest capable model"](https://github.com/fblissjr/fb-claude-skills/blob/main/docs/internals/architecture.md) — decomposition quality and model tiering are complements; well-scoped leaf tasks don't need the frontier model.

## Install

1. Determine the project root: the git repository root, or the working directory if not in a git repo. If the user names a different target project, use that.
2. **Base rule (always).** Read `references/model-delegation.md` (relative to this skill) and write its content **verbatim** to `<project-root>/.claude/rules/model-delegation.md`, creating `.claude/rules/` if needed. Verbatim copy keeps installs identical across projects — do not regenerate or paraphrase the rule text. This layer is fully standalone; nothing below is required for it to work.
3. If the target file already exists and differs, show the user the diff and ask before overwriting — it may carry local edits.
4. **Agents layer (opt-in).** Ask whether to also install the pre-shaped delegation agents (or install without asking if the user said "with agents"). If yes, copy verbatim `references/agents/fast-executor.md` and `references/agents/task-coder.md` to `<project-root>/.claude/agents/`, same diff-and-confirm treatment. These give delegation targets tailored execute-to-spec system prompts instead of a bare model override; the rule prefers them automatically when present.
5. Tell the user which layers were installed: the rule (and any agents) load automatically at the next session start. For the current session, adopt the rule's behavior immediately since you have just read it.

## Update

Same as install; step 3's diff-and-confirm handles the existing files. If the installed rule still carries the removed agent-state feedback section (a `## Record outcomes` block invoking `agent-state delegation record`), delete that section as part of the update.

## Remove

Delete `<project-root>/.claude/rules/model-delegation.md`, and `<project-root>/.claude/agents/fast-executor.md` / `task-coder.md` if they were installed. Nothing else to clean up.

## What the rule says

Delegation criteria in brief (full text in `references/model-delegation.md`): route tasks that are well-specified, mechanical, and verifiable to the cheapest capable model in a subagent; keep design, ambiguity, user interaction, and verification of returned work in the main loop on the strongest model. Tiers are named only as examples so the rule survives model-lineup changes. The base rule stops there — no external dependency.
