---
name: quality
description: >-
  Run the skill quality report for this repo — spec compliance, token budget,
  description quality, version alignment. Use when the user says "check
  quality", "quality report", "check my skills", "are my skills ok", "skill health",
  or names a specific skill to check.
argument-hint: "[skill names to filter, space-separated]"
---

# Skill quality report

```bash
uv run skill-maintain quality $ARGUMENTS
```

`$ARGUMENTS` filters to matching skills by substring (`path` matches
`path-privacy`); omit it to check everything.

Run the command and report what it found. Do not re-implement the checks by
reading files yourself — the thresholds, the verb list, and the discovery rules
live in the tool, and a hand-run version drifts from it silently.

Related commands, all `uv run skill-maintain <cmd>`: `validate` (spec only),
`measure` (token budget only), `test` (the full
red/green suite including repo hygiene).

## Acting on the results

- **Token budget** — over budget usually means the body is carrying reference
  material. Move it to `references/` and leave a pointer.
- **Description quality** — lead with words a request would actually contain.
  The listing truncates at 1,536 characters.
