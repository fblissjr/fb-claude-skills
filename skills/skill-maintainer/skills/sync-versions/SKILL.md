---
name: sync-versions
description: >-
  Bump a plugin's version across all sources (plugin.json, marketplace.json,
  CHANGELOG.md, pyproject.toml) atomically. SKILL.md is deliberately NOT one of
  them. Use when the user says "sync versions",
  "bump version", "align versions", or "/sync-versions <plugin> <version>".
  Pass plugin name and target version as arguments.
metadata:
  author: fblissjr
  last_verified: 2026-07-21
  review_interval_days: 365
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

The cascade is three files. It does **not** scale with how many skills a plugin
ships, because SKILL.md no longer carries a version.

### 3a. plugin.json

`<plugin>/.claude-plugin/plugin.json`:
```json
"version": "X.Y.Z"
```

### 3b. marketplace.json

Root `.claude-plugin/marketplace.json` -- find the entry by plugin name:
```json
"version": "X.Y.Z"
```

### 3c. CHANGELOG.md

Add an entry describing what changed and why. Semver only, no dates.

### 3d. pyproject.toml (only if present)

`tools/<plugin>/pyproject.toml` for plugins with a CLI counterpart, and the root
`pyproject.toml` when the repo version moves (then `uv lock`):
```toml
version = "X.Y.Z"
```

## Step 4 -- Do NOT touch SKILL.md

`metadata.version` was removed from every SKILL.md on 2026-07-21. It duplicated
`plugin.json`, and the only thing that read it was the check confirming the
duplicate still matched -- work that produced no information and forced up to
six file edits per bump. Do not re-add it. The pre-commit hook still validates
the field *if present*, so a stray re-addition is caught rather than drifting.

Do not touch `metadata.last_verified` either. It asserts that a human reviewed
the skill against its source, which a version bump does not establish. Write it
only when you actually did that review.

## Step 5 -- Report

List exactly what was changed:

```
Version bumped: mece-decomposer 0.3.0 -> 0.4.0

Updated files:
  - apps/mece-decomposer/.claude-plugin/plugin.json
  - .claude-plugin/marketplace.json (mece-decomposer entry)
  - apps/mece-decomposer/pyproject.toml
  - CHANGELOG.md

Skipped (not found):
  - (none)
```

## Guardrails

- **Atomic** -- update all sources or none (if any edit fails, stop and report)
- **No major bumps** without explicit user confirmation
- **Do not commit** -- the user decides when to commit
- **Equal version allowed** -- passing the current version re-syncs all sources without bumping (fixes drift)
