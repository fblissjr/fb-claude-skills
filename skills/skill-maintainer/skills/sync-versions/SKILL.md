---
name: sync-versions
description: >-
  Bump a plugin's version across all sources (plugin.json, marketplace.json,
  SKILL.md, pyproject.toml) atomically. Use when the user says "sync versions",
  "bump version", "align versions", or "/sync-versions <plugin> <version>".
  Pass plugin name and target version as arguments.
metadata:
  author: fblissjr
  version: 0.5.0
  last_verified: 2026-04-19
---

# Sync Versions

Bump a plugin's version atomically across all locations where version is tracked.

## Usage

```
/skill-maintainer:sync-versions <plugin-name> <version>
```

Examples:
```
/skill-maintainer:sync-versions tui-design 0.3.0
/skill-maintainer:sync-versions skill-dashboard 1.1.0
/skill-maintainer:sync-versions          # interactive: pick plugin + version
```

## Step 1 -- Determine target plugin and version

If arguments were passed, parse `<plugin-name> <version>` from them.

Otherwise, run the skill-dashboard version alignment check or list all plugins with their current versions, then ask:
1. Which plugin to bump
2. What version to bump to

Read the current version from the plugin's `.claude-plugin/plugin.json` to confirm the starting point.

## Step 2 -- Validate

- Version must be valid semver (X.Y.Z)
- Version must be higher than current (or equal, to force re-sync without bump)
- Do NOT bump major version without explicit user confirmation
- Confirm the plugin directory exists

## Step 3 -- Find and update all version sources

For the target plugin, update version in every file that tracks it:

### 3a. plugin.json

The plugin's `.claude-plugin/plugin.json`:
```json
"version": "X.Y.Z"
```

### 3b. marketplace.json

Root `.claude-plugin/marketplace.json` -- find the entry by plugin name:
```json
"version": "X.Y.Z"
```

### 3c. Primary SKILL.md

The skill whose directory name matches the plugin name (e.g., `skills/<plugin>/skills/<plugin>/SKILL.md` or `apps/<plugin>/skills/<plugin>/SKILL.md`). Update `metadata.version` in frontmatter:
```yaml
metadata:
  version: X.Y.Z
```

### 3c-alt. Sub-skill SKILL.md files (for multi-skill plugins)

Some plugins ship multiple sub-skills under `<plugin>/skills/<sub-skill>/` rather than (or in addition to) a primary SKILL.md matching the plugin name. Each sub-skill has its own `metadata.version` + `metadata.last_verified` that also must be bumped, or version alignment checks will flag drift.

Discover them:

```bash
find skills/<plugin>/skills apps/<plugin>/skills -name "SKILL.md" 2>/dev/null
```

For every SKILL.md found, update `metadata.version` AND `metadata.last_verified` in frontmatter. The primary SKILL.md is the one whose directory name matches the plugin name (if it exists); all others are sub-skills.

**Plugins known to have sub-skills (as of 2026-04-19)**: skill-maintainer (4 sub-skills: init-maintenance, maintain, quality, sync-versions, sync-bundled-ref, finish-session), dev-conventions (5 sub-skills), mlx-skills (4 sub-skills), env-forge, mece-decomposer, document-skills.

If the plugin has no sub-skills (single SKILL.md matching plugin name), this step is a no-op.

### 3d. pyproject.toml (if present)

If the plugin has a `pyproject.toml`, update:
```toml
version = "X.Y.Z"
```

## Step 4 -- Update last_verified

Set `metadata.last_verified` to today's date (YYYY-MM-DD) in the primary SKILL.md AND every sub-skill SKILL.md discovered in step 3c-alt.

## Step 5 -- Report

List exactly what was changed:

```
Version bumped: mece-decomposer 0.3.0 -> 0.4.0

Updated files:
  - apps/mece-decomposer/.claude-plugin/plugin.json
  - .claude-plugin/marketplace.json (mece-decomposer entry)
  - apps/mece-decomposer/skills/mece-decomposer/SKILL.md (metadata.version, last_verified)
  - apps/mece-decomposer/pyproject.toml

Skipped (not found):
  - (none)
```

## Guardrails

- **Atomic** -- update all sources or none (if any edit fails, stop and report)
- **No major bumps** without explicit user confirmation
- **Do not commit** -- the user decides when to commit
- **Equal version allowed** -- passing the current version re-syncs all sources without bumping (fixes drift)
