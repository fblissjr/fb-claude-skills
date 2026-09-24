---
paths:
  - "**/.claude-plugin/**"
  - "**/plugin.json"
---

# Plugin authoring rules

## After creating a new plugin

1. `uv run skill-maintain validate <plugin>/skills/<skill>` (the skill directory)
2. Add the plugin entry to root `.claude-plugin/marketplace.json`
3. Add the repo to `tracked_repos` in `.skill-maintainer/config.json` if watching upstream
4. Complete the rest of AGENTS.md invariant 1's cascade (`CHANGELOG.md` entry)
5. Update root `README.md`: plugins table, install list, invocation list
6. Append a session entry to `internal/log/log_YYYY-MM-DD.md`

## Removing a plugin

Delete the directory. Git history is the archive; a parallel `_deprecated/` tree
is a second place to maintain that nobody reads.

Then: drop it from `marketplace.json` `plugins[]` and the uv workspace, add
`"renames": {"<plugin>": null}` so existing installs get a removal notice instead
of `plugin-not-found`, sweep the README (plugins table, install list, invocation
list) and any doc or SKILL.md that used it as an example, and write a CHANGELOG
entry. The `renames` map is append-only -- keep old entries forever, since
Claude Code follows rename chains.

## Auto-discovery

Leave components in default directories (`skills/`, `agents/`) out of
`plugin.json`; they are auto-discovered.

## plugin.json fields

Upstream requires only `name`, and the manifest itself is optional. This repo's
test suite additionally requires:

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
