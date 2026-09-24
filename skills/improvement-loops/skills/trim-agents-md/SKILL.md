---
name: trim-agents-md
description: "Tightens a repository's always-loaded agent instructions (AGENTS.md, CLAUDE.md, unconditional rules): every line must prevent a mistake, and each one that doesn't is moved to the narrowest home that loads when it matters (a path-scoped rule, a skill, a hook or test, the status doc, the user-level file) or cut. Fills the gaps a newcomer falls into: commands, done criteria, the stops wanted, hazards, settled decisions. Re-points everything that cited the old text, and verifies with a fresh-context diff review and spot-tested tasks. User-invoked only."
disable-model-invocation: true
argument-hint: "[overrides, e.g. 'Depth: rebuild; Hub: agents-md; Targets: CLAUDE.md, .claude/rules/general.md']"
---

# Trim agent instructions

This skill is a standing prompt. The run is in
`${CLAUDE_SKILL_DIR}/references/trim-loop.md`. Read it now and execute it as
written: it is the instruction set for this run, not background.

**Parameters.** Start from its `<parameters>` block and apply these overrides
from the invocation: $ARGUMENTS

An override that names no parameter goes under "Needs from me" rather than
being guessed into one.

**After a compaction,** re-read the run file and your placement map before the
next action. The run's instructions do not survive compaction on their own.
Keep the placement map in a file for that reason.
