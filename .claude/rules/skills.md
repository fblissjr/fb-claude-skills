---
paths:
  - "**/SKILL.md"
---

# Skill authoring rules

These rules load when working with SKILL.md files.

## Trigger phrases required -- unless the skill is user-invoked only

Every skill description must include natural language phrases users would say. Without trigger phrases, Claude won't auto-load the skill. Example: "Use when the user says 'decompose this', 'break down this workflow'..."

**Exception: skills with `disable-model-invocation: true`.** Their description never enters Claude's context, so it is never matched against a user's phrasing -- a trigger phrase there is text that provably cannot fire, and writing one to satisfy the check is satisfying a check by touching what it measures. `skill-maintain validate` enforces this automatically: it skips the WHEN check when that flag is set, and still requires the description to say WHAT the skill does, because that is what a person reads in the slash-command menu.

Write those descriptions to state the action and, where it is not obvious, that invocation is manual.

## Description limit

Keep skill descriptions under 1024 characters. The description field in frontmatter is what users see and what determines when the skill loads.

## No angle brackets in descriptions

A description containing `<` or `>` is a hard validation error upstream (skill-creator's `quick_validate.py` rejects it outright; `skill-maintain validate` only warns). This collides with path-privacy's `<HOME>/...` placeholder form, which stays legal everywhere else -- bodies, references, docs. In a description, name the location in prose instead: "the user's Claude config directory", "absolute home-directory paths under /Users or /home".

## Frontmatter hygiene

No `metadata.author` and no `metadata.version` in SKILL.md. The whole file, frontmatter included, loads into context when the skill activates -- a name or a duplicated version there is standing context cost with no runtime use. Authorship and version live in `plugin.json`; attribution detail goes in the plugin README.

Metadata values are strings. The spec defines `metadata` as a string-to-string map, so quote scalars that YAML would otherwise type as a date or number.

## Script paths

All `uv run` commands in SKILL.md must use paths relative to the project root (where `uv run` is called from), not relative to the SKILL.md file.

Correct: `skill-maintain quality`, or `uv run python tools/<pkg>/scripts/<script>.py` for a script that really is bundled.
Wrong: `uv run python scripts/<script>.py` — resolved against the SKILL.md, which is not where `uv run` starts.

The example here used to name `skill-maintainer/scripts/check_freshness.py`, a
path that has not existed since the CLI absorbed that check. A rule teaching a
command that fails is worse than a rule with no example.

## Body length limit

Keep the SKILL.md body under 500 lines. Extract verbose reference material to `references/` subdirectory and add a one-line pointer in SKILL.md. Example: "Full methodology: see `references/decomposition_methodology.md`"
