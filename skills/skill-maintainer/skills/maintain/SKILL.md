---
name: maintain
argument-hint: "[upstream|sources|quality|all]"
description: >-
  Full maintenance pass for a skills repo: pull upstream docs, sync tracked source repos, run quality
  checks, and review best practices for updates. Use when user says "maintain", "maintenance pass",
  "check upstream", "pull sources", "review best practices", "run maintenance".
  Invoke with /skill-maintainer:maintain.
metadata:
  last_verified: "2026-07-21"
  freshness: "cascade"
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
- `metadata.last_verified` present and within that skill's own `metadata.review_interval_days` (default 30 when the field is absent). The windows are tiered by how fast each skill's source moves — a flat 30 days across the board makes the report permanently red, and a permanently-red board is an ignored board. Skills declaring `metadata.freshness: "cascade"` are exempt from the window: their source is code in the same repo, whose drift the version cascade surfaces — `last_verified` stays as the record of the last human review

### Description quality
- Description contains a WHAT verb (handles, generates, validates, designs, checks, runs, creates, builds, manages, monitors, tracks, reports)
- Description contains a WHEN trigger phrase ("use when", "when user", "when the user", "invoke with")

Output a table with one row per skill: name, valid, tokens, lines, days since verified, description quality.

## Phase 4: Observed behaviour across repos

```bash
skill-maintain tune --days 30 --repo <each repo where plugins from here are installed>
```

The other phases check what this repo *says*. This one checks what its plugins
actually *do*, in every project they run in — it reads session transcripts, so it
reports machine-wide regardless of which repo you run it from.

Deliberately part of the maintenance pass rather than a scheduled job. A cron
that quietly stops is the same never-zero-channel failure this tooling exists to
avoid, and neither built-in scheduler fits: `CronCreate` jobs are session-only
and expire after 7 days, and cloud routines cannot read local transcripts.

What to act on:

- **A hook emitting at a high rate.** Read the rate, not the count: a hook firing
  thousands of times and staying silent is nearly free, while one firing rarely
  and always speaking is not. A 100% emitter on `SessionStart` is the shape to
  question.
- **`ambiguous(...)` in the plugin column.** Two plugins sharing a hook script
  filename. Rename to `hooks/<plugin>-<purpose>.sh` — the transcript stores the
  plugin-root variable unexpanded, so a shared filename is unattributable to
  anything reading it back.
- **LSP diagnostic density above ~3 per push.** A channel that is never at zero
  is a channel that gets ignored. Fix the underlying diagnostics rather than
  suppressing them.
- **Skills at zero invocations.** Ambiguous on its own: not-needed and
  not-discoverable look identical here, and the remedies are opposite. Use
  `skill-creator`'s description-tuning harness to tell them apart before
  deleting anything.
- **Artifact drift.** Files a plugin wrote into a repo, with their staleness
  verdict. Plugin *code* cannot drift — it installs once per user — so this is
  the only place staleness hides.

## Phase 5: Controls audit (periodic, on-demand)

Where the `postmortem` plugin is installed, run `/postmortem:control-audit`
periodically: a census of everything check-shaped outside the test suite
(git hooks, Claude Code hooks, CLI validators, reminders), with live-fire
violation of any control nothing watches. Not every maintenance pass needs
it — it is listed here so the cadence has an owner, deliberately without a
scheduler (same reasoning as Phase 4). Skip and note when the plugin is not
installed or a recent audit exists.

## Phase 6: Mutation sample (scoped to changed subjects)

Red-first proves an oracle can fail on the day it is written; nothing
re-proves it after, and a test drifts toward decorative as its subject moves
while the suite stays green either way. This phase re-proves a sample each
pass:

1. Enumerate the subject modules changed since the last maintenance pass
   (git diff names the modules; the test arms that pin them are the sample
   frame).
2. Mutate a handful of those subjects — one guarded behavior each — confirm
   the pinning arm goes red, revert.
3. Report mutations-run over arms-in-frame, exposure stated: "3 of 12 arms
   in frame mutated, 3 red" — never a bare "sampled some". No changed
   subjects since the last pass is a skip-and-note, not a silent pass.

Whole-suite mutation stays `postmortem:test-audit`'s job; this phase targets
recently-changed subjects because that is where drift concentrates, at a
cost small enough to run every pass.

## Phase 7: Review and propose updates

After the preceding phases:

1. Read `references/best_practices.md` (bundled with this plugin) or `.skill-maintainer/best_practices.md` (if present in the repo)
2. Review change details from Phases 1-6
3. Determine whether `best_practices.md` needs updates based on:
   - New or changed upstream doc pages (Phase 2) that affect skill authoring rules
   - New patterns or conventions from pulled repo changes (Phase 1)
   - Quality report findings that suggest missing or outdated checklist items (Phase 3)
   - Behaviour findings from Phase 4 that point at a rule rather than a one-off
   - Controls-audit findings from Phase 5 (empty guarded-by slots, header rot) that warrant a control-authoring rule
4. If updates needed: list each proposed change with rationale. Wait for user approval before writing.
5. If no updates needed: report "best_practices.md is current -- no changes needed"

## Rules

- Never auto-write to `best_practices.md` -- always show proposed changes and wait for approval
- Run all phases even if one reports no changes; "run" honors a phase's own skip conditions (Phases 1, 2, 5, and 6 define theirs -- in particular, Phase 5's default on a routine pass is skip-and-note, never an unrequested live-fire)
- If a phase fails, report the error and continue with remaining phases
- After finishing, summarize: repos pulled, upstream pages checked, quality issues found, behaviour findings across repos, controls-audit outcome (run or skipped, and why), mutation sample (mutations-run over arms-in-frame, or the skip note), best practices edits (if any)
