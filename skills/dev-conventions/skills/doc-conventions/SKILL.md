---
name: doc-conventions
description: >-
  Documentation conventions: last-updated dates, lowercase filenames, internal/ subfolder for non-shared docs,
  session logs, and documenting the "why". Use when creating or updating documentation, READMEs, or
  design docs. Invoke with /dev-conventions:doc-conventions. Triggers on "write docs", "update README",
  "document this", "add a design doc", "session log".
metadata:
  author: Fred Bliss
  version: 0.5.0
  last_verified: 2026-04-13
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

## Dependency change tracking

When a session adds, removes, or bumps package versions, include a dependency changes section in the session log. This is the only place dependency changes are recorded outside the source-of-truth files (pyproject.toml, package.json, uv.lock, bun.lockb).

### Format

```markdown
## Dependency changes

| Action | Package | Old | New | Type |
|--------|---------|-----|-----|------|
| added | httpx | -- | 0.27.2 | direct |
| bumped | orjson | 3.10.0 | 3.10.5 | direct |
| removed | requests | 2.31.0 | -- | direct |
```

### How to generate

- Python: `git diff pyproject.toml` for direct deps, `git diff uv.lock` for transitives
- JavaScript: `git diff package.json` for direct deps
- If many transitive changes, summarize with count: "12 transitive dependencies updated (see uv.lock diff)"

### What NOT to do

- Do NOT create a `deps.md`, `dependencies.json`, or any separate manifest
- Do NOT dump full `uv tree` or `bun pm ls` output -- only report changes
- The source of truth is always pyproject.toml / package.json / lock files
