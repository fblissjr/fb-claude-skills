---
name: init-maintenance
description: >-
  Set up persistent maintenance config and state tracking in a skills repo. Creates
  .skill-maintainer/ directory with config, state, and best practices checklist. Use when user says
  "init maintenance", "set up maintenance", "initialize skill-maintainer", "configure maintenance",
  "add maintenance to this repo". Invoke with /skill-maintainer:init-maintenance.
metadata:
  author: Fred Bliss
  version: 0.9.0
  last_verified: 2026-07-21
  review_interval_days: 365
---

# Initialize Maintenance

Set up persistent maintenance infrastructure in a skills repo: config, state directory, best-practices checklist, gitignore entries, and the pre-commit git hook.

## Target directory

If `$ARGUMENTS` is non-empty, use it as the target directory path (resolve relative to cwd). Otherwise, use the current working directory.

Examples:
- `/skill-maintainer:init-maintenance` -- initialize in cwd
- `/skill-maintainer:init-maintenance ./other-repo` -- initialize in `./other-repo`

All paths in the steps below are relative to the target directory.

## The fast path: `skill-maintain init`

If the `skill-maintainer` CLI is installed (workspace `uv sync --all-packages` or `uv add git+...`), run:

```bash
uv run skill-maintain init [--dir <path>]
```

This single command performs steps 1, 2, 3, and 5 below atomically. Re-running is idempotent: existing config and existing pre-commit hook are preserved untouched. To replace an existing pre-commit hook (e.g., after the bundled sample is updated upstream), pass `--force-hook` -- the prior hook is saved as `.git/hooks/pre-commit.local` before the new one is written.

If the CLI isn't available, follow the manual steps below.

## Manual steps

### 1. Create config directory

```bash
mkdir -p .skill-maintainer/state
```

### 2. Create config.json

Write `.skill-maintainer/config.json` with defaults:

```json
{
  "upstream_urls": [
    "https://code.claude.com/docs/en/skills",
    "https://code.claude.com/docs/en/plugins",
    "https://code.claude.com/docs/en/plugins-reference",
    "https://code.claude.com/docs/en/discover-plugins",
    "https://code.claude.com/docs/en/plugin-marketplaces",
    "https://code.claude.com/docs/en/hooks-guide",
    "https://code.claude.com/docs/en/hooks",
    "https://code.claude.com/docs/en/sub-agents",
    "https://code.claude.com/docs/en/memory"
  ],
  "tracked_repos": [],
  "llms_full_url": "https://code.claude.com/docs/llms-full.txt"
}
```

Ask the user if they have local git repos to track (e.g., `coderef/` directories). Add paths to `tracked_repos`.

### 3. Copy best practices checklist

Copy `references/best_practices.md` (bundled with this plugin) to `.skill-maintainer/best_practices.md`. This checklist is the reference used by `/skill-maintainer:maintain` Phase 4.

### 4. Update .gitignore

Check if `.gitignore` exists. If it does, check if `.skill-maintainer/state/` is already ignored. If not, append:

```
# skill-maintainer state (auto-generated, not tracked)
.skill-maintainer/state/
```

### 5. Pre-commit hook

The bundled pre-commit hook validates staged SKILL.md files via `agentskills`, checks plugin version alignment, warns on unbumped plugin content changes, and warns on CLAUDE.md size creep. The hook degrades gracefully in non-plugin repos (skips the version checks if no `plugin.json` is found).

If `skill-maintain init` is unavailable, copy the sample manually:

```bash
cp tools/skill-maintainer/src/skill_maintainer/templates/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The sample requires `jq` and `uv` available on PATH; the hook is bash-3.2 portable.

## After setup

Report what was created:
- Config file path
- State directory path
- Whether .gitignore was updated
- Pre-commit hook status (`installed`, `already up to date`, or `skipped: not a git repo`)

Suggest next steps:
- Run `/skill-maintainer:quality` for an initial health check
- Add tracked repos to `config.json` if needed
- Run `/skill-maintainer:maintain` for a full maintenance pass
