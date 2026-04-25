---
name: sync-bundled-ref
description: >-
  Sync the working-copy best_practices.md to the plugin-bundled reference so new
  `skill-maintain init` runs pull the latest rules. Use when the user says "sync
  bundled reference", "update bundled best_practices", "sync plugin reference",
  or after editing `.skill-maintainer/best_practices.md`. Invoke with
  /skill-maintainer:sync-bundled-ref.
metadata:
  author: Fred Bliss
  version: 0.6.1
  last_verified: 2026-04-25
---

# Sync Bundled Reference

Keep `skills/skill-maintainer/references/best_practices.md` (the seed for `skill-maintain init` in new repos) aligned with `.skill-maintainer/best_practices.md` (this repo's working copy).

## Why this exists

Two copies of `best_practices.md` exist in this repo:

- `.skill-maintainer/best_practices.md` -- the working copy, read by `skill-maintain` commands.
- `skills/skill-maintainer/references/best_practices.md` -- the seed copied into new repos when someone runs `skill-maintain init`.

When rules are updated (e.g. during `/skill-maintainer:maintain` Phase 4), they land in the working copy. The bundled reference silently drifts unless someone syncs it. New repos then get stale rules. This skill closes that loop.

A PostToolUse hook also fires on Edit/Write of the working copy to do the sync automatically -- this skill is the manual / explicit counterpart for cases where the hook didn't fire (e.g. bulk rewrites done outside the Edit/Write tools).

## Step 1 -- Check both files exist

```bash
test -f .skill-maintainer/best_practices.md
test -f skills/skill-maintainer/references/best_practices.md
```

If either is missing, stop and ask the user.

## Step 2 -- Compare and report

```bash
diff -q .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md
```

If identical: report "Already in sync. No action needed." and exit.

If different: show the diff summary so the user knows what's about to be propagated:

```bash
diff .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md | head -40
```

## Step 3 -- Sync

Copy working copy -> bundled reference:

```bash
cp .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md
```

## Step 4 -- Verify and stage

```bash
md5 .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md
```

Both md5s should match. Then stage both for commit:

```bash
git add .skill-maintainer/best_practices.md skills/skill-maintainer/references/best_practices.md
```

Do NOT commit -- the user decides when.

## Step 5 -- Flag version-bump requirement

Editing the bundled reference is a change to plugin content. Per repo convention, that requires a version bump. Remind the user:

> "Bundled reference updated. Plugin content changed -- `/skill-maintainer:sync-versions skill-maintainer <next-version>` before committing, or the marketplace cache won't refresh for users installing this plugin."

## Guardrails

- **Direction is one-way**: working copy -> bundled reference. Never reverse. The working copy is authoritative.
- **No auto-commit**: show the diff, stage, report. User commits.
- **Exit quietly on no-op**: if already in sync, don't make noise -- just report and exit.
