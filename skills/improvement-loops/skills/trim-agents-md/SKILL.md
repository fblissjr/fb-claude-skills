---
name: trim-agents-md
description: "Trims a repository's always-loaded agent instructions (AGENTS.md, CLAUDE.md, unconditional rules) to what an agent needs on its first edit, without losing a rule. Finds everything that cites or reads the file before cutting, judges each line by whether the model could learn it from the repo, moves what is still true to the narrowest home that loads when it matters, re-points the checks and citations that pointed at the old text, and has a fresh-context reviewer confirm no rule was lost. User-invoked only."
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
