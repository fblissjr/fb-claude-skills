---
paths:
  - "**/.claude-plugin/**"
  - "**/plugin.json"
---

# Plugin authoring rules

These rules load when working with plugin manifests and .claude-plugin/ directories.

## After creating a new plugin -- required checklist

1. `uv run agentskills validate <plugin-name>/skills/<skill-name>/SKILL.md`
2. Add plugin entry to root `.claude-plugin/marketplace.json`
3. Add repo to `TRACKED_REPOS` in `skill-maintainer/scripts/pull_sources.py` if watching upstream
4. Bump version in both `pyproject.toml` and `CHANGELOG.md`
5. Update root `README.md` plugins table and installation section
6. Append session entry to `internal/log/log_YYYY-MM-DD.md`

## Auto-discovery

Components in default directories (`skills/`, `agents/`) are auto-discovered. Do not list them in `plugin.json`.

## plugin.json required fields

- `name`: plugin name (matches directory name)
- `version`: semver (e.g., "0.1.0")
- `description`: one-line description
- `author`: author name or handle
- `repository`: full GitHub URL
