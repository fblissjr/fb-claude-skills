---
description: Pull sources, check for upstream changes, and review best practices for updates
---

# /maintain

Orchestrate a full maintenance pass for the skill ecosystem. Run each phase in order, report results, and assist with updating `.skill-maintainer/best_practices.md` if anything changed.

## Phase 1: Pull local sources

```bash
skill-maintain sources
```

Read the output. Note which repos show CHANGED or NEW. If all are UP_TO_DATE, say so and continue to Phase 2.

## Phase 2: Check upstream docs

```bash
skill-maintain upstream
```

Read the output. Note which pages show CHANGED or NEW. If none changed, say so and continue to Phase 3.

## Phase 3: Quality report

```bash
skill-maintain quality
```

Read the output. Note any validation failures, over-budget skills, or stale skills (last_verified > 30 days). Summarize findings.

## Phase 4: Review and propose updates

After all three commands have run, do the following:

1. Read the current `.skill-maintainer/best_practices.md`
2. Read any change details from Phases 1-3 (commit logs, changed pages, quality issues)
3. Determine whether `best_practices.md` needs updates based on:
   - New or changed upstream doc pages (Phase 2) that affect skill authoring rules
   - New patterns or conventions visible in pulled repo changes (Phase 1)
   - Quality report findings that suggest missing or outdated checklist items (Phase 3)
4. If updates are needed:
   - List each proposed change with rationale (what changed upstream, what the edit is)
   - Wait for user approval before writing any changes to `best_practices.md`
   - Update `last updated:` date at the top of the file after edits
5. If no updates are needed, report "best_practices.md is current -- no changes needed"

## Rules

- Never auto-write to `best_practices.md` -- always show proposed changes and wait for approval
- Run all three commands even if one reports no changes (the quality report may find issues independent of upstream)
- If a command fails, report the error and continue with remaining phases
- After finishing, summarize: repos pulled, upstream pages checked, quality issues found, best practices edits (if any)
