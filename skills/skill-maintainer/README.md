last updated: 2026-07-26

# skill-maintainer

Maintenance tools for any Claude Code skills repo. Validates skills against the Claude Code skill schema (a superset of the Agent Skills spec, so Claude Code frontmatter fields are accepted), checks token budgets, tracks freshness against each skill's own `metadata.review_interval_days` window, detects upstream doc changes (with per-page content snapshots and line/char deltas), checks plugin.json/marketplace.json version alignment repo-wide, reviews best practices, and orchestrates end-of-session workflow (log drafting, bundled-reference sync, version-bump detection).

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install skill-maintainer@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/skills/skill-maintainer
```

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `maintain` | `/skill-maintainer:maintain` | Full maintenance pass: upstream checks, source pulls, quality report, best practices review |
| `quality` | `/skill-maintainer:quality` | Quick quality check: spec compliance, token budget, freshness, description quality |
| `init-maintenance` | `/skill-maintainer:init-maintenance` | Set up persistent maintenance config and state in a repo |
| `sync-versions` | `/skill-maintainer:sync-versions <plugin> <ver>` | Bump a plugin's version across `plugin.json`, `marketplace.json`, and `pyproject.toml` atomically. No longer touches SKILL.md -- `metadata.version` was removed from skill frontmatter, and `plugin.json` is the sole version source |
| `finish-session` | `/skill-maintainer:finish-session` | Orchestrate end-of-session cleanup: draft log, sync refs, flag version bumps, quality scan |

## agents

| Agent | Where | What it does |
|-------|-------|--------------|
| `session-log-drafter` | forked subagent | Reads conversation + `git diff` and drafts a house-style entry for `internal/log/log_YYYY-MM-DD.md`. Invoked by `finish-session`. |

## hooks

| Event | What | When |
|-------|------|------|
| `Stop` | `maybe-draft-session-log.sh` | When the session touched >= 3 substantive files (excluding logs, lock files, `.skill-maintainer/state/`) AND today's `internal/log/log_YYYY-MM-DD.md` doesn't exist or wasn't modified today, prints a one-line stderr nudge pointing at `/skill-maintainer:finish-session`. Honors `stop_hook_active=true`; never blocks; exit 0 always. |

## usage examples

```
# quick health check on all skills in the repo
/skill-maintainer:quality

# full maintenance pass (upstream + sources + quality + best practices review)
/skill-maintainer:maintain

# set up maintenance config in a new skills repo
/skill-maintainer:init-maintenance

# bump path-privacy's version across plugin.json, marketplace.json, pyproject.toml
# (SKILL.md no longer carries a version field -- plugin.json is the sole source)
/skill-maintainer:sync-versions path-privacy 0.7.4

# sync working copy -> bundled reference manually (hook does this automatically on Edit)

# end-of-session cleanup before committing a substantive working session
/skill-maintainer:finish-session
```

## relationship to the CLI package

The `skill-maintainer` Python package at `tools/skill-maintainer/` provides the `skill-maintain` CLI for CI/headless use. This plugin is the primary interface for interactive use within Claude Code -- it embeds the same knowledge (thresholds, rules, checks) directly in the skills so no Python package installation is required. If the CLI is available, the `/maintain` skill will use it for upstream and source checks; otherwise it performs equivalent checks using WebFetch and Bash.

## references

- `references/best_practices.md` -- machine-parseable checklist used by the quality checks

## `tune` — observed behaviour, not declared behaviour

`skill-maintain tune` reads session transcripts and reports how plugins actually
behave in every project they run in: how often each hook fired versus spoke,
bytes emitted by channel, LSP diagnostic density, skill invocation counts, and
drift in files plugins wrote into repos. It runs as Phase 4 of
`/skill-maintainer:maintain` rather than on a schedule — a cron that quietly
stops is the failure this tooling exists to avoid, and neither built-in
scheduler fits (session-only jobs, or cloud routines with no local transcripts).
