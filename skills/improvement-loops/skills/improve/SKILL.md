---
name: improve
description: "Runs one improvement pass over a project in the direction its north star points, without breaking what it does today: faster in real use, less code, a truer account of what it does, rules that now run as checks. Works with the repo's AGENTS.md sections (North star, Measurement, Reporting, Loop state); state carries between runs in a ledger, bookmarks and a scoreboard; each change lands as its own commit with evidence on a worktree branch; the report leads with what needs the owner. User-invoked only, because a run spends hours and many subagents."
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_state.py *)
argument-hint: "[overrides, e.g. 'Goal: breakthrough; Focus: the export path; Run budget: 2 hours']"
---

# Improve

<run>
This skill is a standing prompt. The loop is in
`${CLAUDE_SKILL_DIR}/references/improvement-loop.md`. Read `common.md`, then the loop file, and execute
it as written: it is the instruction set for this run, not background.
</run>

<paths>
- Plugin root: `${CLAUDE_PLUGIN_ROOT}`
- This session's id: `${CLAUDE_SESSION_ID}`
- Shared rules: `${CLAUDE_PLUGIN_ROOT}/references/common.md`. Read it before the loop file.
- Loop-state script: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/loop_state.py`
- AGENTS.md template: `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md`
</paths>

<parameters>
Start from the loop's `<parameters>` block and apply these overrides from the
invocation: $ARGUMENTS

Write the resolved block at the top of the run record before the loop's first
step. An override that names no parameter goes under "Needs from me" rather
than being guessed into one.
</parameters>

<prerequisites>
- The loop cites sections of the repo's AGENTS.md by name. If the repo lacks
  them, the template is at the path above. Propose the
  missing sections under "Needs from me" rather than writing the repo's
  AGENTS.md yourself; its North star is the owner's to set.
- A loop needs things to climb. If the loop state has no scenarios, or the
  run's goal differs from the one they were chosen for, say so under "Needs
  from me" and recommend `/design-scoreboard` before the next run. Build only
  what this run's first ideas need.
</prerequisites>

<after_compaction>
Re-read the loop file and the run state (the ledger and the current run
record) before the next action. The loop's instructions do not survive
compaction on their own; the files do.
</after_compaction>
