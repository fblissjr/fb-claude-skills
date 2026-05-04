last updated: 2026-05-04

# Plugin versioning

The full version cascade for any plugin content change in this repo. The `/skill-maintainer:sync-versions` skill covers four sources atomically; the rest is manual.

## What counts as "plugin content"

Anything inside a plugin directory (e.g., `skills/<plugin>/`, `apps/<plugin>/`) plus any `tools/<plugin>/` source code that ships behavior the plugin advertises. Specifically:

- Hooks, scripts, directives, references inside the plugin
- Agent files in `<plugin>/agents/`
- Sub-skill SKILL.md bodies (any change beyond `metadata.version` / `metadata.last_verified`)
- The plugin's `.claude-plugin/plugin.json` (description, etc.)
- Source code under `tools/<plugin>/src/...` for plugins with a CLI counterpart

If you change any of the above, `marketplace update` won't refresh the cache for installed users until the plugin version bumps.

## The cascade

1. **Plugin version sources (covered by `/skill-maintainer:sync-versions`):**
   - `<plugin>/.claude-plugin/plugin.json` → `version`
   - Root `.claude-plugin/marketplace.json` → entry where `name == <plugin>`, `version`
   - Plugin's primary SKILL.md frontmatter → `metadata.version` (only for plugins with a SKILL.md whose dirname matches the plugin name)
   - `tools/<plugin>/pyproject.toml` (if a CLI counterpart exists) → `[project] version`

2. **Sub-skill metadata (manual — pre-commit hard-blocks on drift):**
   - For every `<plugin>/skills/<skill>/SKILL.md`: bump both `metadata.version` (must match `plugin.json`) and `metadata.last_verified` (today's date).
   - Pre-commit hook reads each sub-skill's `metadata.version` and compares to `plugin.json`. Drift = block, not warning.
   - Example: `skill-maintainer` has 6 sub-skills (`finish-session`, `init-maintenance`, `maintain`, `quality`, `sync-bundled-ref`, `sync-versions`). All six must move together with the plugin.

3. **Repo-level (manual):**
   - Root `pyproject.toml` → `version` (every plugin bump pairs with a root version bump)
   - `CHANGELOG.md` → new entry under root version
   - `uv lock` → refresh `uv.lock` (else `uv lock --check` fails in CI)

## Worked example: `skill-maintainer 0.6.3 → 0.6.4` (May 2026)

Files touched in one commit:

- `skills/skill-maintainer/agents/session-log-drafter.md` — content change (the trigger)
- `skills/skill-maintainer/.claude-plugin/plugin.json` → `0.6.4`
- `.claude-plugin/marketplace.json` → `skill-maintainer` entry version `0.6.4`
- `tools/skill-maintainer/pyproject.toml` → `0.6.4`
- 6 × `skills/skill-maintainer/skills/*/SKILL.md` → `metadata.version: 0.6.4`, `metadata.last_verified: 2026-05-04`
- `pyproject.toml` (root) → `0.24.4`
- `CHANGELOG.md` — new `## 0.24.4` entry
- `uv.lock` — refreshed via `uv lock`

13 files in one commit. Pre-commit validates each SKILL.md and confirms version alignment before allowing the commit.

## Common mistakes

- **Forgetting `uv lock`.** Local commit succeeds (the hook doesn't run lock check); CI later fails on `uv lock --check`.
- **Bumping plugin.json but missing a sub-skill.** Pre-commit blocks with a `VERSION MISMATCH` line per drift. Re-stage the missed sub-skill and retry.
- **Editing `tools/<plugin>/` source without bumping plugin version.** The hook only warns (no version-bearing file is staged inside the plugin directory), so it's easy to miss. Treat `tools/<plugin>/` source as plugin content.
- **Major bump without a CHANGELOG entry.** No mechanical block; reviewer catches it. Always pair the version bump with the changelog narrative.

## Why the cascade exists

Version-bumping every plugin source preserves three guarantees:

1. `marketplace update` correctly refreshes cached plugin content for installed users.
2. `/plugin install <name>@<version>` resolves to a deterministic snapshot.
3. Users running `skill-maintain quality` see the version they actually have, not the version that was running before they pulled.

Skipping any one source means at least one of these guarantees breaks for someone downstream.
