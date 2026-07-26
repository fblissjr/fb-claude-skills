---
name: quality
description: >-
  Run the skill quality report for this repo — spec compliance, token budget,
  freshness, description quality, version alignment. Use when the user says "check
  quality", "quality report", "check my skills", "are my skills ok", "skill health",
  or names a specific skill to check.
argument-hint: "[skill names to filter, space-separated]"
metadata:
  last_verified: "2026-07-26"
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
`freshness` (staleness only), `measure` (token budget only), `test` (the full
red/green suite including repo hygiene).

## Acting on the results

- **Staleness** — `last_verified` means a human reviewed the skill against its
  source. Never bump it to clear a red row; that is the one edit that makes the
  signal lie. Re-tier `review_interval_days` if the window is wrong for how fast
  that source actually moves.
- **Token budget** — over budget usually means the body is carrying reference
  material. Move it to `references/` and leave a pointer.
- **Description quality** — lead with words a request would actually contain.
  The listing truncates at 1,536 characters.
