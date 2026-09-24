---
name: improve
description: "Runs one improvement pass over a project toward its north star (its VISION.md: purpose, long-term direction, principles), without breaking what the README, docs and tests say it does today: faster in real use, less code, a truer account of what it does, rules that now run as checks. State carries between runs in a ledger, bookmarks and a scoreboard; each change lands as its own commit with evidence on a worktree branch; read-only reviewers work one lens each; the report leads with what needs the owner. User-invoked only, because a run spends hours and many subagents."
disable-model-invocation: true
argument-hint: "[overrides, e.g. 'Goal: breakthrough; Focus: the export path; Run budget: 2 hours']"
---

# Improve

This skill is a standing prompt. The loop is in
`${CLAUDE_SKILL_DIR}/references/improvement-loop.md`. Read it now and execute
it as written: it is the instruction set for this run, not background.

**Parameters.** Start from the loop's `<parameters>` block and apply these
overrides from the invocation: $ARGUMENTS

Write the resolved parameter block at the top of the run record before the
loop's first step. An override that names no parameter goes under "Needs from
me" rather than being guessed into one.

**After a compaction, or when resuming in a new session,** re-read the loop
file and your run state (the ledger and the current run record) before the
next action. The loop's instructions do not survive compaction on their own;
the files do.
