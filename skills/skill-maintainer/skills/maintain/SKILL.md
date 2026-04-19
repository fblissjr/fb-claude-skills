---
name: maintain
description: >-
  Full maintenance pass for a skills repo: pull upstream docs, sync tracked source repos, run quality
  checks, and review best practices for updates. Use when user says "maintain", "maintenance pass",
  "check upstream", "pull sources", "review best practices", "run maintenance".
  Invoke with /skill-maintainer:maintain.
metadata:
  author: Fred Bliss
  version: 0.5.1
  last_verified: 2026-04-19
---

# Full Maintenance Pass

Run each phase in order. Report results after each phase. Continue even if one phase has no changes.

## Phase 1: Pull local sources

If `skill-maintain` CLI is available:

```bash
skill-maintain sources
```

If CLI is not available, check for tracked repos in `.skill-maintainer/config.json` under `tracked_repos`. For each repo path that exists:

1. Record the current HEAD SHA: `git -C <path> rev-parse HEAD`
2. Pull: `git -C <path> pull --ff-only`
3. Compare new HEAD to old. Report CHANGED (with `git -C <path> log --oneline <old>..<new>`) or UP_TO_DATE.

If no config file exists, skip this phase and note "no .skill-maintainer/config.json found -- skip source pull (run /skill-maintainer:init-maintenance to set up)".

## Phase 2: Check upstream docs

If `skill-maintain` CLI is available:

```bash
skill-maintain upstream
```

If CLI is not available, check `.skill-maintainer/config.json` for `llms_full_url` and `upstream_urls`. Fetch the llms-full.txt URL using WebFetch, split by `Source: <url>` delimiters, and compare each watched page's content against stored hashes in `.skill-maintainer/state/upstream_hashes.json`.

If no config file exists, skip and note "no config -- skip upstream check".

## Phase 3: Quality report

If `skill-maintain` CLI is available:

```bash
skill-maintain quality
```

If CLI is not available, perform the checks manually. For every SKILL.md found in the repo:

### Spec compliance
- Frontmatter has `name` and `description` fields
- `name` is kebab-case, matches directory name
- No disallowed frontmatter fields (allowed: name, description, license, allowed-tools, metadata, compatibility)

### Token budget
- Count total chars in the skill directory (`.md` files only), divide by 4
- Warn if over 4,000 tokens, critical if over 8,000

### Body size
- SKILL.md under 500 lines

### Freshness
- `metadata.last_verified` present and within 30 days of today

### Description quality
- Description contains a WHAT verb (handles, generates, validates, designs, checks, runs, creates, builds, manages, monitors, tracks, reports)
- Description contains a WHEN trigger phrase ("use when", "when user", "when the user", "invoke with")

Output a table with one row per skill: name, valid, tokens, lines, days since verified, description quality.

## Phase 4: Review and propose updates

After all three phases:

1. Read `references/best_practices.md` (bundled with this plugin) or `.skill-maintainer/best_practices.md` (if present in the repo)
2. Review change details from Phases 1-3
3. Determine whether `best_practices.md` needs updates based on:
   - New or changed upstream doc pages (Phase 2) that affect skill authoring rules
   - New patterns or conventions from pulled repo changes (Phase 1)
   - Quality report findings that suggest missing or outdated checklist items (Phase 3)
4. If updates needed: list each proposed change with rationale. Wait for user approval before writing.
5. If no updates needed: report "best_practices.md is current -- no changes needed"

## Rules

- Never auto-write to `best_practices.md` -- always show proposed changes and wait for approval
- Run all phases even if one reports no changes
- If a phase fails, report the error and continue with remaining phases
- After finishing, summarize: repos pulled, upstream pages checked, quality issues found, best practices edits (if any)
