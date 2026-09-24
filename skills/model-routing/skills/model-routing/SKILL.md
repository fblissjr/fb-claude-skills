---
name: model-routing
argument-hint: "[install | remove]"
description: Install, update, or remove the per-project down-tier model-delegation rule (.claude/rules/model-delegation.md), optionally with fast-executor / task-coder agent definitions. Installation is currently paused pending measurement, and this skill is user-invoked only -- it will not load on its own judgment.
disable-model-invocation: true
---

<paused>
Installation is paused. The rule is always-loaded text asserting that
down-tier delegation lowers cost without hurting quality, a claim nothing has
measured, so installing it spends context on an unfalsified belief. It was
removed deliberately from every repo that had it.

On an install or update request, say this and wait for the user to confirm
before writing anything, since a reinstall silently undoes that removal.
Removal needs no confirmation.

What would justify resuming (a definition of a good delegation outcome, and a
way to observe one) is in
[docs/internals/model_routing_flywheel.md](https://github.com/fblissjr/fb-claude-skills/blob/main/docs/internals/model_routing_flywheel.md).
To resume, delete this block and `disable-model-invocation` from the
frontmatter.
</paused>

Install, update, or remove a per-project model-delegation rule. The rule is a
plain `.claude/rules/` file: it loads at session start in that project only,
needs no plugin installed to keep working, and is removed by deleting the file.
Two independent layers: the base rule, standalone and complete on its own, and
opt-in pre-shaped agents.

<install>
1. The project root is the git repository root, or the working directory
   outside a git repo, unless the user names a different target project.
2. Base rule (always). Copy `references/model-delegation.md` (relative to this
   skill) verbatim to `<project-root>/.claude/rules/model-delegation.md`,
   creating `.claude/rules/` if needed. Verbatim keeps installs identical
   across projects, so the rule text is never regenerated or paraphrased.
3. If the target file exists and differs, show the diff and ask before
   overwriting; it may carry local edits.
4. Agents (opt-in). Install them when the user said "with agents"; otherwise
   ask. Copy `references/agents/fast-executor.md` and
   `references/agents/task-coder.md` verbatim to `<project-root>/.claude/agents/`,
   with the same diff-and-confirm. They give delegation targets
   execute-to-spec system prompts instead of a bare model override, and the
   rule prefers them when present.
5. Tell the user which layers were installed; they load at the next session
   start. Adopt the rule's behavior for the current session now, since you
   have just read it.
</install>

<update>
Same as install; step 3's diff-and-confirm handles existing files. If the
installed rule carries a `## Record outcomes` block invoking
`agent-state delegation record`, delete that section: the feedback layer it
belongs to was removed and its CLI no longer exists.
</update>

<remove>
Delete `<project-root>/.claude/rules/model-delegation.md`, and
`<project-root>/.claude/agents/fast-executor.md` / `task-coder.md` if they were
installed. Nothing else to clean up.
</remove>

The rule in brief (full text in `references/model-delegation.md`): route
well-specified, mechanical, verifiable tasks to the cheapest capable model in
a subagent; keep design, ambiguity, user interaction, and verification of
returned work in the main loop. Tiers are named only as examples so the rule
survives model-lineup changes.
