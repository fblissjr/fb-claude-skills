---
name: optimize
description: "Speeds up a codebase as far as it will go in one session, against a hard target (every primary benchmark at least 1.2x faster than the base commit by default) without regressing correctness, output quality or safety. Base and branch worktrees, exact counts proven against wall-clock time, read-only reviewers one lens each, a re-check of every headline result on the final commit. User-invoked only, because a run spends hours and many subagents."
disable-model-invocation: true
argument-hint: "[overrides, e.g. 'Target: 1.5x; Reviewers: 8; Other sessions: mrblue on main']"
---

# Optimize

This skill is a standing prompt. The campaign is in
`${CLAUDE_SKILL_DIR}/references/optimizer-loop.md`. Read it now and execute it
as written: it is the instruction set for this run, not background.

**Parameters.** Start from the campaign's `<parameters>` block and apply these
overrides from the invocation: $ARGUMENTS

Record the resolved parameter block at the top of `PERF_LOG.md` with the
baseline. An override that names no parameter goes under "Needs from me"
rather than being guessed into one.

**After a compaction,** re-read the campaign file and `PERF_LOG.md` before the
next action. The campaign's instructions do not survive compaction on their
own; the log does.
