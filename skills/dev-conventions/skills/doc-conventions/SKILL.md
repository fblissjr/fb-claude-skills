---
name: doc-conventions
description: >-
  Documentation conventions: last-updated dates, lowercase filenames, internal/ subfolder for non-shared docs,
  session logs, and documenting the "why". Use when creating or updating documentation, READMEs, or
  design docs. Invoke with /dev-conventions:doc-conventions. Triggers on "write docs", "update README",
  "document this", "add a design doc", "session log".
metadata:
  author: Fred Bliss
  version: 0.4.0
  last_verified: 2026-04-02
---

# Documentation Conventions

## File standards

- **Last updated date** at the top of every document (format: `YYYY-MM-DD` or `last updated: YYYY-MM-DD`).
- **Lowercase filenames** with underscores. No spaces, no camelCase. Example: `design_decisions.md`, not `DesignDecisions.md`.
- **Organize into subfolders** by topic rather than flat directories.

## Content standards

- Document research, design decisions, alternatives considered, and the "why".
- Don't just describe what was built. Explain why it was built that way and what else was considered.
- Keep docs close to the code they describe.

## Internal documentation

Use `./internal/` for documentation that isn't meant to be shared (design notes, debugging logs, scratch work). This directory should be in `.gitignore`.

## Session logs

Daily session logs go in `./internal/log/log_YYYY-MM-DD.md`. These capture what was done, decisions made, and open questions. Useful for continuity across sessions.
