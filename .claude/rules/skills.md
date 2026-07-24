---
paths:
  - "**/SKILL.md"
---

# Skill authoring rules

These rules load when working with SKILL.md files.

## Trigger phrases required

Every skill description must include natural language phrases users would say. Without trigger phrases, Claude won't auto-load the skill. Example: "Use when the user says 'decompose this', 'break down this workflow'..."

## Description limit

Keep skill descriptions under 1024 characters. The description field in frontmatter is what users see and what determines when the skill loads.

## Frontmatter hygiene

No `metadata.author` and no `metadata.version` in SKILL.md. The whole file, frontmatter included, loads into context when the skill activates -- a name or a duplicated version there is standing context cost with no runtime use. Authorship and version live in `plugin.json`; attribution detail goes in the plugin README.

## Script paths

All `uv run` commands in SKILL.md must use paths relative to the project root (where `uv run` is called from), not relative to the SKILL.md file.

Correct: `skill-maintain freshness` or `uv run python skill-maintainer/scripts/check_freshness.py`
Wrong: `uv run python scripts/check_freshness.py`

## Body length limit

Keep the SKILL.md body under 500 lines. Extract verbose reference material to `references/` subdirectory and add a one-line pointer in SKILL.md. Example: "Full methodology: see `references/decomposition_methodology.md`"
