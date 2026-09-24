---
name: optimize
description: "Speeds up a codebase as far as it will go in one session, against a hard target (every primary benchmark at least 1.2x faster than the base commit by default) without regressing correctness, output quality or safety. Works with the repo's AGENTS.md sections (North star, Measurement, Loop state); base and branch worktrees, exact counts proven against wall-clock time, read-only reviewers one lens each, a re-check of every headline result on the final commit. User-invoked only, because a run spends hours and many subagents."
disable-model-invocation: true
argument-hint: "[overrides, e.g. 'Target: 1.5x; Reviewers: 8; Other sessions: mrblue on main']"
---

# Optimize

<run>
This skill is a standing prompt. The campaign is in
`${CLAUDE_SKILL_DIR}/references/optimizer-loop.md`. Read it now and execute it
as written: it is the instruction set for this run, not background.
</run>

<parameters>
Start from the campaign's `<parameters>` block and apply these overrides from
the invocation: $ARGUMENTS

Record the resolved block at the top of the run record with the baseline. An
override that names no parameter goes under "Needs from me" rather than being
guessed into one.
</parameters>

<prerequisites>
- The campaign cites sections of the repo's AGENTS.md by name, above all
  Measurement (real path, primary benchmarks, instruments, hazards). If they
  are missing, the template is `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md`;
  propose the fill under "Needs from me" rather than writing it yourself.
- If the primary benchmarks are unnamed, or their guardrails and
  counter-checks are, recommend `/design-scoreboard` first. A speed target with
  no quality guardrail is a number the campaign can reach by breaking things.
</prerequisites>

<after_compaction>
Re-read the campaign file and the run record before the next action. The
campaign's instructions do not survive compaction on their own; the record
does.
</after_compaction>
