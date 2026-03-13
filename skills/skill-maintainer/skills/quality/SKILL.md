---
name: quality
description: >-
  Quick quality check for all skills in a repo: spec compliance, token budget, body size, freshness,
  and description quality. Use when user says "check quality", "quality report", "check my skills",
  "validate skills", "skill health", "are my skills ok". Invoke with /skill-maintainer:quality.
metadata:
  author: Fred Bliss
  version: 0.2.0
  last_verified: 2026-03-13
---

# Quality Check

Discover all SKILL.md files in the repo and check each one. Output a summary table.

## Scope

If `$ARGUMENTS` is non-empty, filter discovered skills to those whose directory name matches any of the space-separated arguments. Matching is substring: `tui` matches `tui-design`. If no skills match, report an error and exit.

Examples:
- `/skill-maintainer:quality` -- check all skills
- `/skill-maintainer:quality tui-design` -- check only tui-design
- `/skill-maintainer:quality mlx fast` -- check skills matching "mlx" or "fast"

## Discovery

Find all files matching `**/skills/*/SKILL.md` in the current repo. Skip directories named `node_modules`, `.git`, `.venv`, `__pycache__`, `state`, `dist`, `build`. Then apply the scope filter from `$ARGUMENTS` if provided.

## Checks per skill

### 1. Spec compliance

Read the SKILL.md frontmatter (between `---` delimiters). Check:
- `name` field exists and is non-empty
- `name` is kebab-case (lowercase letters, digits, single hyphens, no leading/trailing hyphens)
- `name` matches the containing directory name
- `description` field exists and is non-empty
- `description` is under 1024 characters
- `description` has no XML angle brackets (< >)
- No disallowed frontmatter fields (allowed: name, description, license, allowed-tools, metadata, compatibility)

Mark as PASS or FAIL.

### 2. Token budget

Count total characters across all `.md` files in the skill directory (SKILL.md + any references/ content). Divide by 4 for token estimate.

- Under 4,000: OK
- 4,000-8,000: WARN
- Over 8,000: CRITICAL

### 3. Body size

Count lines in SKILL.md (excluding frontmatter).

- Under 500: OK
- 500+: OVER

### 4. Freshness

Read `metadata.last_verified` from frontmatter. Calculate days since that date.

- Within 30 days: FRESH
- Over 30 days: STALE
- Missing: MISSING

### 5. Description quality

Check the `description` field for:
- **WHAT verb**: contains at least one action verb (handles, generates, validates, designs, checks, runs, creates, builds, manages, monitors, tracks, reports, maintains, pulls, syncs, detects, reviews, measures, discovers, enforces, guides, orchestrates, breaks, exports, searches, browses)
- **WHEN trigger**: contains at least one trigger phrase ("use when", "when user", "when the user", "invoke with", "use after", "use before")

Both present: GOOD. One missing: PARTIAL. Both missing: POOR.

### 6. Cross-references

Scan all `.md` files in each skill directory (SKILL.md + references/) for the pattern `load the \`X\` skill` (where X is a backtick-quoted skill name). This is the canonical cross-reference directive; do not match descriptive mentions like "the \`X\` skill covers..." which are not actionable references.

For each referenced skill name `X`, verify that a skill directory named `X` exists in the repo (i.e., there is a `skills/X/SKILL.md` somewhere). Mark as PASS if all references resolve, FAIL if any reference points to a non-existent skill, SKIP if no cross-references found.

### 7. Reference file dates

For each skill that has a `references/` directory, check every `.md` file in it for a `last updated: YYYY-MM-DD` line (case-insensitive, anywhere in the file). Mark as PASS if all reference files have dates, WARN if any are missing, SKIP if no references/ directory.

## Output format

```
Skill Quality Report
====================

| Skill | Spec | Tokens | Lines | Freshness | Description | XRefs | RefDates |
|-------|------|--------|-------|-----------|-------------|-------|----------|
| name  | PASS | 1,234  | 45    | FRESH (3d)| GOOD        | PASS  | PASS     |
| name  | FAIL | 9,012  | 520   | STALE (45d)| PARTIAL    | FAIL  | WARN     |

Summary: X skills checked, Y pass all checks, Z have issues

SKIP counts as PASS for the summary count (the check was not applicable, not failed).
```

If any skill fails spec compliance, note it prominently at the end.

## Thresholds reference

| Check | OK | Warn | Critical |
|-------|-------|------|----------|
| Token budget | under 4,000 | 4,000-8,000 | over 8,000 |
| Body lines | under 500 | -- | 500+ |
| Freshness | under 30 days | -- | over 30 days or missing |
| Description | WHAT + WHEN | one missing | both missing |
| Cross-refs | all resolve or SKIP | -- | dangling reference |
| Ref dates | all present or SKIP | some missing | -- |
