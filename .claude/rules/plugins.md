---
paths:
  - "**/.claude-plugin/**"
  - "**/plugin.json"
---

# Plugin authoring rules

These rules load when working with plugin manifests and .claude-plugin/ directories.

## After creating a new plugin -- required checklist

1. `uv run agentskills validate <plugin>/skills/<skill>/SKILL.md`
2. Add plugin entry to root `.claude-plugin/marketplace.json`
3. Add repo to `tracked_repos` in `.skill-maintainer/config.json` if watching upstream
4. Bump root `pyproject.toml` + add a `CHANGELOG.md` entry
5. Update root `README.md`: plugins table, install list, invocation list
6. Append session entry to `internal/log/log_YYYY-MM-DD.md`

## Version cascade -- three files

A plugin content change bumps `<plugin>/.claude-plugin/plugin.json`, the root
`marketplace.json` entry, and `CHANGELOG.md`. Plus `tools/<plugin>/pyproject.toml`
and root `pyproject.toml` + `uv lock` only where those exist.

**Do NOT put a version in SKILL.md.** `metadata.version` was removed from every
SKILL.md on 2026-07-21: it duplicated `plugin.json`, and its only reader was the
check confirming the duplicate matched. The pre-commit still validates the field
*if present*, so a re-addition is caught rather than drifting.

**Do NOT bump `metadata.last_verified` as part of a cascade.** It asserts a human
reviewed the skill against its source; a version bump does not establish that.

## Deprecating a plugin

Move it under `apps/_deprecated/` (in `SKIP_DIRS`, so it stops being scanned),
drop it from `marketplace.json` `plugins[]` and the uv workspace, and add
`"renames": {"<plugin>": null}` so existing installs get a removal notice instead
of `plugin-not-found`. The `renames` map is append-only.

## Auto-discovery

Components in default directories (`skills/`, `agents/`) are auto-discovered. Do not list them in `plugin.json`.

## plugin.json fields

Upstream requires only `name`, and the manifest itself is optional. This repo
additionally requires the following, enforced by our own test suite:

- `name`: plugin name (matches directory name)
- `version`: semver (e.g., "0.1.0")
- `description`: one-line description
- `author`: author name or handle
- `repository`: full GitHub URL

## Hooks use exec form

A hook running a bundled script sets `args`, and names the interpreter as
`command`: `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]`.
Shell form hands the whole string to `sh -c`, so a plugin root containing a
space breaks it. Full rationale: `docs/internals/plugin-patterns.md`.
