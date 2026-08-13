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

Otherwise, note the top-level directories touched (e.g., `skills/skill-maintainer/`, `apps/gemini-bridge/`, `tools/`, root config) -- these determine which downstream handoffs matter.

### Step 2 -- Draft session log

Delegate to the `session-log-drafter` subagent. It reads the conversation + git diff and returns a house-style draft for the repo's session log.

```
(invoke session-log-drafter agent)
```

Show the draft to the user. Two paths:

- **New session, no existing log**: resolve where this repo keeps session logs
  before writing. Look for an existing log directory and match its layout and
  filename pattern; if there is none, propose a location rather than creating
  one. `internal/log/log_YYYY-MM-DD.md` is one repo's convention, not a default
  to impose on every repo this plugin is installed in.
- **Extending today's existing log**: append under a new `## part N: <topic>` heading. Edit in place.

Do not commit -- this is a draft for review.

### Step 3 -- Check for copies that drifted

`best_practices.md` used to have a working copy and a bundled copy kept in sync by a hook, and this step verified the pair. Both the second copy and the hook were deleted on 2026-08-13: `best_practices_file()` now falls back to the bundled reference, so there is one file and nothing to compare.

Nothing replaces this step by default. If the project later accumulates a genuine "local copy / shipped copy" pair, check it here -- but first apply the rule in the root CLAUDE.md: a copy earns its place only if it has a consumer other than the check confirming it is a copy. The pair that prompted this step failed that test.

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
  Session log:   <resolved log path> (part <N>)
  Bundled refs:  in sync  (or: synced via hook)
  Version bumps: <plugin>@<v>  <plugin>@<v>  (or: none needed)
  Quality:       30/30 valid, 0 over budget, 0 stale

Next: /commit-commands:commit (or git add + commit manually)
```
