---
name: sync-versions
argument-hint: "[plugin] [version]"
arguments:
  - plugin
  - version
description: >-
  Bump a plugin's version across all sources (plugin.json, marketplace.json,
  CHANGELOG.md, pyproject.toml) atomically. SKILL.md is deliberately NOT one of
  them. Use when the user says "sync versions",
  "bump version", "align versions", or "/sync-versions path-privacy 0.9.0".
  Pass plugin name and target version as arguments.
---

# Sync versions

Bump a plugin's version in every file that tracks it, all or none.

<parameters>
`<plugin-name> <version>`, e.g. `/skill-maintainer:sync-versions path-privacy 0.7.4`.
With no arguments, list each plugin's current version from its
`.claude-plugin/plugin.json` and ask which plugin and which version.
</parameters>

<scope>
The target version is valid semver, and higher than the current one in the
plugin's `plugin.json`, or equal to it: an equal version re-syncs every source
without bumping, which is how drift gets fixed.

A major bump is the one stop: confirm it with the user before editing, because
it is a compatibility claim the user makes, not one the diff can settle.

Commits are the user's; this skill ends with the edits in the working tree.
</scope>

<procedure>
Update every source below, or none: if any edit fails, stop and report which
ones landed.

1. `<plugin>/.claude-plugin/plugin.json` — `"version"`.
2. Root `.claude-plugin/marketplace.json` — the `"version"` of the entry with
   this plugin's name.
3. `CHANGELOG.md` — an entry saying what changed and why. Semver only, no dates.
4. `tools/<plugin>/pyproject.toml`, only when the CLI ships with the plugin.
   Read the plugin's marketplace `source` first: if it does not include
   `tools/`, the CLI is a separate artifact on its own version line, and
   setting it to the plugin's number is often a downgrade. Bump the two
   independently in that case and say so in the changelog entry. A root
   `pyproject.toml` that is a virtual workspace root carries no version and is
   never bumped; if a real repo-level version moves, run `uv lock` after.

SKILL.md is not a version source. Leave it alone: a `metadata.version` there
only duplicates `plugin.json`, and its only reader would be the check
confirming the duplicate matched.
</procedure>

<report>
The bump (`<plugin> <old> -> <new>`), each file updated, and each source
skipped with the reason (absent, or the CLI versions independently).
</report>
