---
name: finish-session
description: >-
  Orchestrate end-of-session cleanup: draft a session log entry, sync bundled
  references, and flag any plugin-content changes that need a version bump
  before commit. Use when the user says "finish session", "wrap up", "end of
  session cleanup", "close out this session", or before committing a substantive
  work session. Invoke with /skill-maintainer:finish-session.
metadata:
  author: Fred Bliss
  version: 0.5.2
  last_verified: 2026-04-19
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

## Workflow

### Step 1 -- Inventory what changed

Run in parallel:

```bash
git status --short
git diff --stat HEAD
```

If no changes, stop and report "Nothing to wrap up -- clean tree." Exit.

Otherwise, note the top-level directories touched (e.g., `skills/skill-maintainer/`, `apps/agent-state-mcp/`, `tools/`, root config) -- these determine which downstream handoffs matter.

### Step 2 -- Draft session log

Delegate to the `session-log-drafter` subagent. It reads the conversation + git diff and returns a house-style draft for `internal/log/log_YYYY-MM-DD.md`.

```
(invoke session-log-drafter agent)
```

Show the draft to the user. Two paths:

- **New session, no existing log**: write the draft directly to `internal/log/log_YYYY-MM-DD.md`.
- **Extending today's existing log**: append under a new `## part N: <topic>` heading. Edit in place.

Do not commit -- this is a draft for review.

### Step 3 -- Sync bundled references

If `.skill-maintainer/best_practices.md` was modified in this session, the PostToolUse hook should have already mirrored it to `skills/skill-maintainer/references/best_practices.md`. Verify:

```bash
cmp -s .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md && echo "in sync" || echo "DRIFT"
```

If drift reported, run `/skill-maintainer:sync-bundled-ref`.

Similar pattern for any other "working copy / bundled copy" pairs the project might accumulate.

### Step 4 -- Flag version bumps

For every plugin directory under `skills/` or `apps/` that had content changes, the plugin version must bump or `marketplace update` won't refresh the cache.

Detect affected plugins:

```bash
git diff --name-only HEAD | grep -E '^(skills|apps)/[^/]+/' | cut -d/ -f1-2 | sort -u
```

For each affected plugin, show the current version from `<plugin>/.claude-plugin/plugin.json` and ask the user: "Bump `<plugin>` to `<next>`?" with a sensible default (patch bump for small changes, minor for new features).

Do NOT auto-bump. The user decides.

If the user confirms, invoke `/skill-maintainer:sync-versions <plugin> <version>` for each. Note that sync-versions handles sub-skill SKILL.md files too (step 3c-alt in that skill).

### Step 5 -- Pre-commit checks (optional)

If the user plans to commit immediately, run a final sanity pass:

```bash
skill-maintain quality
```

Report any new drift (stale dates, budget violations, missing WHAT verbs) introduced this session.

### Step 6 -- Hand off to commit

Do not commit. Report what's staged, what's left unstaged, and suggest the next command (typically `/commit-commands:commit` or manual `git add` + commit).

Final output to user:

```
Session wrap complete. Summary:

  Files changed: <N>  (across <X> plugins, <Y> tools)
  Session log:   internal/log/log_YYYY-MM-DD.md (part <N>)
  Bundled refs:  in sync  (or: synced via hook / via sync-bundled-ref)
  Version bumps: <plugin>@<v>  <plugin>@<v>  (or: none needed)
  Quality:       30/30 valid, 0 over budget, 0 stale

Next: /commit-commands:commit (or git add + commit manually)
```

## Guardrails

- **Never commit.** This skill ends at the pre-commit boundary.
- **One draft pass.** If the user rejects the session-log draft, let them edit rather than calling the drafter again with a different prompt -- they'll iterate faster on the file directly.
- **Version bumps are interactive.** Never auto-bump. Users need control over semver.
- **Exit early on empty sessions.** If `git status` is clean, report and exit in step 1 -- don't march through every step.

## Related skills

- `session-log-drafter` (agent, same plugin) -- does the actual log drafting.
- `sync-bundled-ref` (same plugin) -- manual bundled-reference sync fallback.
- `sync-versions` (same plugin) -- atomic version bump across all sources.
- `quality` (same plugin) -- pre-commit quality scan.
