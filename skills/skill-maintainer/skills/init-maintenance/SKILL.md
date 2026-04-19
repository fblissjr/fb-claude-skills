---
name: init-maintenance
description: >-
  Set up persistent maintenance config and state tracking in a skills repo. Creates
  .skill-maintainer/ directory with config, state, and best practices checklist. Use when user says
  "init maintenance", "set up maintenance", "initialize skill-maintainer", "configure maintenance",
  "add maintenance to this repo". Invoke with /skill-maintainer:init-maintenance.
metadata:
  author: Fred Bliss
  version: 0.5.2
  last_verified: 2026-04-19
---

# Initialize Maintenance

Set up persistent maintenance infrastructure in a skills repo. All steps are optional -- ask the user which ones to perform.

## Target directory

If `$ARGUMENTS` is non-empty, use it as the target directory path (resolve relative to cwd). Otherwise, use the current working directory.

Examples:
- `/skill-maintainer:init-maintenance` -- initialize in cwd
- `/skill-maintainer:init-maintenance ~/claude/mlx-skills` -- initialize in mlx-skills

All paths in the steps below are relative to the target directory.

## Steps

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

### 5. Optional: pre-commit hook for skills-ref validation

Ask the user if they want a pre-commit hook that validates SKILL.md files on commit. If yes, write `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
set -euo pipefail

staged=$(git diff --cached --name-only --diff-filter=ACM | grep 'SKILL\.md$' || true)
[ -z "$staged" ] && exit 0

for f in $staged; do
  dir=$(dirname "$f")
  echo "Validating $dir..."
  uv run agentskills validate "$dir" || exit 1
done
```

Then: `chmod +x .git/hooks/pre-commit`

Only offer this if `uv` and `agentskills` (skills-ref) are available. Check with: `uv run agentskills --version 2>/dev/null`

## After setup

Report what was created:
- Config file path
- State directory path
- Whether .gitignore was updated
- Whether pre-commit hook was installed

Suggest next steps:
- Run `/skill-maintainer:quality` for an initial health check
- Add tracked repos to `config.json` if needed
- Run `/skill-maintainer:maintain` for a full maintenance pass
