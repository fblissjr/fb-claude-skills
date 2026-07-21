last updated: 2026-07-21

# Plugin versioning

The full version cascade for any plugin content change in this repo. The `/skill-maintainer:sync-versions` skill covers four sources atomically; the rest is manual.

## What counts as "plugin content"

Anything inside a plugin directory (e.g., `skills/<plugin>/`, `apps/<plugin>/`) plus any `tools/<plugin>/` source code that ships behavior the plugin advertises. Specifically:

- Hooks, scripts, directives, references inside the plugin
- Agent files in `<plugin>/agents/`
- Sub-skill SKILL.md bodies
- The plugin's `.claude-plugin/plugin.json` (description, etc.)
- Source code under `tools/<plugin>/src/...` for plugins with a CLI counterpart

If you change any of the above, `marketplace update` won't refresh the cache for installed users until the plugin version bumps.

## The cascade

As of 2026-07-21 the cascade is **three files**, regardless of how many skills a
plugin ships. `metadata.version` was removed from every SKILL.md: it duplicated
`plugin.json` and the only thing that ever read it was the check verifying it
still matched. Storing a value in N places so a hook can confirm all N agree is
work that produces no information. `plugin.json` is now the sole source.

1. `<plugin>/.claude-plugin/plugin.json` → `version`
2. Root `.claude-plugin/marketplace.json` → entry where `name == <plugin>`
3. `CHANGELOG.md` → a new entry

Plus, only when they exist:

- `tools/<plugin>/pyproject.toml` (CLI counterpart) → `[project] version`
- Root `pyproject.toml` + `uv lock` when the repo version moves

### What is NOT in the cascade

- **`metadata.version` in any SKILL.md.** Removed. Do not re-add it. The
  pre-commit hook still validates it *if present* (`[ -n "$sk_ver" ]`), so a
  stray re-addition gets caught rather than silently drifting.
- **`metadata.last_verified`.** It means "a human checked this is still
  correct", which a version bump does not establish. Bumping eight plugins for
  a mechanical hook change on 2026-07-21 would have marked 17 unreviewed skills
  freshly verified and moved staleness failures 11 → 5 on no evidence. Write it
  only when you actually reviewed the skill against its source.

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
