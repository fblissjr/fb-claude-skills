---
name: session-log-drafter
description: >-
  Drafts a session log entry at internal/log/log_YYYY-MM-DD.md from the current
  conversation, following this repo's house style (what changed, why, findings,
  follow-ups). Use when the user says "draft session log", "write up this
  session", "log today's work", or at the end of a substantive working session.
metadata:
  author: Fred Bliss
  version: 0.1.0
---

# Session Log Drafter

Forked subagent that reads the active conversation context and drafts an entry for `internal/log/log_YYYY-MM-DD.md` in this repo's house style.

## Why this exists

This repo's conventions (CLAUDE.md + `.claude/rules/general.md`) require updating `internal/log/` at the end of every working session. Writing the log manually at the end is tedious and often skipped; the author just did the work and is fatigued. Delegating to a forked subagent keeps the main conversation focused on the task while the log gets drafted in parallel.

## House style (follow exactly)

1. **First line**: `last updated: YYYY-MM-DD` (today's ISO date).
2. **Heading**: `# session log YYYY-MM-DD`.
3. **Sections for substantive work**: lowercase headers, e.g. `## maintenance pass`, `## part 2: gap analysis + improvements`, `## findings`.
4. **Narrative tone, not a transcript**. Don't quote the user or recite prompts. Describe what changed and why.
5. **Explain WHY, not just WHAT**. A reader six months from now should understand the motivation. Git log shows what changed; the session log explains why.
6. **Include a `## follow-ups` section** at the bottom with concrete next steps or open questions. Never empty -- if there are no follow-ups, say "None identified."
7. **No emojis. No filler.** Direct language.
8. **Explicit file paths** for changes, e.g. `tools/skill-maintainer/src/skill_maintainer/upstream.py`, not "the upstream module".
9. **Date-stamp any relative time references.** "Next week" -> "2026-04-26".

## What to include

- New files created (with one-line purpose each).
- Files modified (with a one-line summary of the change).
- Design decisions that weren't obvious -- include the alternatives considered.
- Findings that came up during the work and didn't get addressed -- these become follow-ups.
- Version bumps with old -> new.
- Test runs that proved the change works (one line, e.g. "Verified: tamper + re-run produces +2/-0 delta as expected").
- If commits were made, reference them by short sha + subject.

## What to exclude

- Conversation dialogue or prompts.
- Obvious things a diff already shows (formatting changes, renamed variables, etc.).
- Speculation about future features that wasn't discussed in the session.
- Boilerplate.

## Process

1. Read `internal/log/log_YYYY-MM-DD.md` if it exists for today's date. If it does, you're extending it under a new `## part N: <topic>` heading, not replacing.
2. Read recent sections of the conversation (last ~20 turns) to understand what was actually accomplished.
3. Spot-check file changes with `git diff HEAD` or `git status --short` to confirm the log reflects reality, not just what was discussed.
4. Draft the entry. Return the draft as your output -- do NOT write to disk. The main session writes or edits once it approves.

## Output format

Return only the markdown content of the session log section (or full file if creating new). No preamble, no commentary about the draft itself. Just the content, ready to paste or pipe.

Keep the draft tight: aim for 40-120 lines for a single focused session, longer only if multiple distinct topics were tackled.
