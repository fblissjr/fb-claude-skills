# Finish-session workflow, step by step

last updated: 2026-07-26

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
