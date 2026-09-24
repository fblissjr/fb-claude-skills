---
name: design-scoreboard
description: "Designs what an improvement or optimizer loop should climb for a given project and goal, and what must not get worse while it does: goal metrics measured on the real path, guardrails, and counter-checks aimed at the cheapest way to fake each gain, so no single number can be reward-hacked. Proves each proxy tracks the outcome it stands for, measures its noise, writes the scenarios as data in the loop state, and proposes the fill for AGENTS.md's Measurement section. Rerun in review mode when the goal changes. User-invoked only."
disable-model-invocation: true
argument-hint: "[goal and overrides, e.g. 'Goal: faster cold start; Focus: the CLI' or 'Existing scoreboard: review']"
---

# Design a scoreboard

<run>
This skill is a standing prompt. The procedure is in
`${CLAUDE_SKILL_DIR}/references/scoreboard-loop.md`. Read it now and execute
it as written.
</run>

<parameters>
Start from its `<parameters>` block and apply these overrides from the
invocation: $ARGUMENTS

An override that names no parameter goes under "Needs from me" rather than
being guessed into one.
</parameters>

<prerequisites>
The procedure reads the repo's AGENTS.md (North star, Where things live,
Commands, Measurement). If those sections are missing, the template is
`${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md`. Propose the missing parts under
"Needs from me" and work from the nearest thing the repo has.
</prerequisites>

<after_compaction>
Re-read the procedure file and the scenarios written so far before the next
action.
</after_compaction>
