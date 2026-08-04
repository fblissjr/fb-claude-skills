---
name: finish-session
argument-hint: "[skip-log]"
description: >-
  Orchestrate end-of-session cleanup: draft a session log entry, sync bundled
  references, and flag any plugin-content changes that need a version bump
  before commit. Use when the user says "finish session", "wrap up", "end of
  session cleanup", "close out this session", or before committing a substantive
  work session. Invoke with /skill-maintainer:finish-session.
metadata:
  last_verified: "2026-07-21"
  freshness: "cascade"
---
# Finish Session

Composed end-of-session workflow. Runs three handoffs in order; the user reviews each output before moving to the next.

## When to use

- Substantive working session about to end (commit imminent)
- User says "finish", "wrap up", or similar
- Before any `/commit-commands:commit` invocation when plugin content was touched

## When NOT to use

- Mid-task iterations
- Read-only sessions (no files changed)
- Quick one-off fixes with no design decisions worth logging

## Running it

The step-by-step procedure is in `references/workflow.md` — draft the session
log, sync the bundled reference, then flag every plugin-content change that
still needs a version bump before commit.

## Guardrails

- **Never commit.** This skill ends at the pre-commit boundary.
- **One draft pass.** If the user rejects the session-log draft, let them edit rather than calling the drafter again with a different prompt -- they'll iterate faster on the file directly.
- **Version bumps are interactive.** Never auto-bump. Users need control over semver.
- **Exit early on empty sessions.** If `git status` is clean, report and exit in step 1 -- don't march through every step.

## Related skills

- `session-log-drafter` (agent, same plugin) -- does the actual log drafting.
- `sync-versions` (same plugin) -- atomic version bump across all sources.
- `quality` (same plugin) -- pre-commit quality scan.
