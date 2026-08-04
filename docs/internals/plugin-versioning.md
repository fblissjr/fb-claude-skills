last updated: 2026-08-04

# Plugin versioning

The full version cascade for any plugin content change in this repo.

## What counts as "plugin content"

Anything inside a plugin directory (e.g., `skills/<plugin>/`, `apps/<plugin>/`) plus any `tools/<plugin>/` source code that ships behavior the plugin advertises. Specifically:

- Hooks, scripts, directives, references inside the plugin
- Agent files in `<plugin>/agents/`
- Sub-skill SKILL.md bodies
- The plugin's `.claude-plugin/plugin.json` (description, etc.)
- A skill plugin's shipped subdirs — `templates/`, `references/`, `examples/` — not just SKILL.md prose. Specimen: the 2026-07-21 explainer-video 0.5.1→0.6.0 bump was mostly template and reference work (references + templates ≈ 1,600 changed lines vs. 195 in SKILL.md), and required the full cascade. (The plugin has since been retired; the specimen stands.)
- Source code under `tools/<plugin>/src/...` — but only **when the plugin bundles that tool**; see below.

If you change any of the above, `marketplace update` won't refresh the cache for installed users until the plugin version bumps.

The boundary is what the marketplace `source` actually ships, so check the
`source` entry before cascading. `skill-maintainer`'s source is
`./skills/skill-maintainer`, which carries no code from
`tools/skill-maintainer` — a CLI change there reaches nobody through a plugin
bump, so plugin and CLI version independently (plugin 0.17.0 / CLI 0.19.0 as
of 2026-08-01, correctly). When the plugin does bundle the tool, a
`tools/<plugin>/src/` edit is plugin content and triggers the cascade.

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
- `uv lock` when a `tools/*` package version changed, so the lock matches

The root `pyproject.toml` is a **virtual workspace root with no version** — a
plugin collection has no single repo version, so there is nothing to bump. The
CHANGELOG's top `## X.Y.Z` is a standalone narrative marker, not a shadow of a
package version.

### What is NOT in the cascade

- **`metadata.version` in any SKILL.md.** Removed. Do not re-add it. The
  pre-commit hook still validates it *if present* (`[ -n "$sk_ver" ]`), so a
  stray re-addition gets caught rather than silently drifting.
- **`metadata.author` in any SKILL.md.** Removed 2026-07-24 (all 30 remaining
  instances swept in one pass). The whole SKILL.md, frontmatter included,
  loads into context when the skill activates, so an author name there is
  standing context cost with no runtime use. Attribution lives in
  `plugin.json` and the plugin README, which are never context-loaded. Do not
  re-add it.
- **`metadata.last_verified`.** It means "a human checked this is still
  correct", which a version bump does not establish. Bumping eight plugins for
  a mechanical hook change on 2026-07-21 would have marked 17 unreviewed skills
  freshly verified and moved staleness failures 11 → 5 on no evidence. Write it
  only when you actually reviewed the skill against its source.

## Worked example: `skill-maintainer 0.6.3 → 0.6.4`

Files touched in one commit:

- `skills/skill-maintainer/agents/session-log-drafter.md` — content change (the trigger)
- `skills/skill-maintainer/.claude-plugin/plugin.json` → `0.6.4`
- `.claude-plugin/marketplace.json` → `skill-maintainer` entry version `0.6.4`
- `tools/skill-maintainer/pyproject.toml` → `0.6.4`
- `CHANGELOG.md` — a new `## X.Y.Z` entry at the top (its own narrative number)
- `uv.lock` — refreshed via `uv lock`

Six files. The root `pyproject.toml` is not touched: it is a virtual workspace
root with no version. **No SKILL.md is touched** — `metadata.version` was removed from
every SKILL.md on 2026-07-21 and must not be re-added; see above. An earlier
version of this example listed six SKILL.md edits and a `last_verified` bump,
which is now exactly the wrong thing to copy.

## Common mistakes

- **Forgetting `uv lock`.** Local commit succeeds (the hook doesn't run lock check); CI later fails on `uv lock --check`.
- **Re-adding `metadata.version` to a SKILL.md.** Pre-commit still validates the field *if present*, so a stray re-addition is caught rather than drifting silently. It should not be there at all.
- **Malformed changelog insert.** `check_changelog_version` validates that the top `## X.Y.Z` heading is well-formed and that no entry landed above it. It compares against a root version only when the root declares one; the virtual root does not, so here the check is format and insert-integrity only.
- **Editing `tools/<plugin>/` source without bumping plugin version.** The hook only warns (no version-bearing file is staged inside the plugin directory), so it's easy to miss. Treat `tools/<plugin>/` source as plugin content.
- **Major bump without a CHANGELOG entry.** No mechanical block; reviewer catches it. Always pair the version bump with the changelog narrative.

## Copies: the two-question test

Some duplication is load-bearing (the cascade itself synchronizes three real
copies of a version). The test for any duplicated field or component, settled
2026-08-04 when the repo-local `control-builder` agent was retired in favor of
the copy the postmortem plugin ships: **name the copy's consumer, and name
what watches the pair — if either answer is "nothing", delete the copy or
demote it to data the shipped mechanism cites at dispatch.** The earlier
one-question form — a copy earns its place only if it has a consumer other
than the check that confirms it is a copy — is the first half of the same
test.

How the known pairs scored:

- `plugin.json` and `marketplace.json` versions **pass**: each has a real
  consumer (deterministic install resolution; marketplace cache refresh) and
  a pre-commit check watches the pair.
- SKILL.md `metadata.version` **failed** the consumer question — its only
  reader was the check confirming it matched `plugin.json`. Removed
  2026-07-21.
- Per-unit `CHANGELOG.md` files **failed both**, hence the one-changelog rule
  (root only). `apps/readwise-reader` was the only first-party exception, and
  it drifted five versions behind its own `pyproject.toml` before anyone
  noticed. Removed 2026-07-26.

Every pair that legitimately remains passes one of three ways:

1. **Mechanical mirror** — something watches the pair by construction.
   `.skill-maintainer/best_practices.md` is the working copy; a PostToolUse
   hook mirrors it into `skills/skill-maintainer/references/best_practices.md`
   (repo invariant 3).
2. **Designed handoff** — the local copy is authoritative and the shipped one
   self-silences. dev-conventions' ambient blocks detect ground coverage in
   `.claude/rules/` and stay quiet in this repo (repo invariant 6).
3. **Data vs. mechanism** — local evidence is quoted into a dispatch of the
   shipped mechanism at use time, never welded into a second copy of the
   mechanism itself.

Local copies of components this repo's own plugins ship (agents, skills,
procedure prose) get the test with full force: an unwatched local variant
splits dogfooding from what installs actually run, so defects in the shipped
copy stop being noticed here first.

## Why the cascade exists

Version-bumping every plugin source preserves three guarantees:

1. `marketplace update` correctly refreshes cached plugin content for installed users.
2. `/plugin install <name>@<version>` resolves to a deterministic snapshot.
3. Users running `skill-maintain quality` see the version they actually have, not the version that was running before they pulled.

Skipping any one source means at least one of these guarantees breaks for someone downstream.
