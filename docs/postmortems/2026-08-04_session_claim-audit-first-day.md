---
mode: session
scope: claim-audit-first-day
date: 2026-08-04
summary: The audit family's first day was spent catching its own builder — claim-audit's first run corrected the changelog that shipped it, and the owner's "how do we know" converted two more asserted universals into derived claims and a new pin-mutation rule.
artifacts:
  - CHANGELOG.md
  - docs/internals/claim_audit_design.md
  - docs/internals/control_audit_design.md
  - docs/internals/plugin-patterns.md
  - docs/internals/gotchas.md
  - docs/internals/maintenance.md
  - apps/gemini-bridge/tests/test_adhoc.py
  - tools/skill-maintainer/tests/test_changelog_claims.py
  - .claude/rules/general.md
  - VISION.md
  - CLAUDE.md
  - session log 2026-08-04 (private, not published)
  - internal/memo_claims_reminder_exposure.md
---

# Session postmortem: claim-audit's first day

Session scope as it actually unfolded: "where we left off" became the queued
claim-audit build plus a gemini-bridge extension in parallel, then the 08-03
follow-up board, a retirement, two design notes' worth of decisions, two
cross-repo memos, and a closing stretch of the instruments being turned on
this session's own output.

## 1. What went well

- **The queue-memory mechanism worked end to end.** Set 2026-08-03, it
  surfaced the claim-audit build at session start, its verify-then-act
  instruction was followed (the design note still said "not started"), the
  build landed by mid-morning (`9d85970`), and the memory was deleted per
  its own instruction. Second successful use of the pattern; a third
  (`project_next_session_queue`) is now set on the same template.
- **Claim-audit paid for itself the hour it shipped.** Its first run, on
  this session's own two changelog entries, caught "Eighteen new test arms,
  recorded red first" when seventeen went red (`52e8c1a` corrects
  CHANGELOG.md). The specimen matches the design note's founding class:
  freshest summary prose, wrong count.
- **Red-first held under a full-speed session.** 17 of 18 gemini-bridge
  arms recorded red before implementation (`apps/gemini-bridge/tests/test_adhoc.py`),
  both skill-maintain window defects red first
  (`tools/skill-maintainer/tests/test_changelog_claims.py`), both 0.7.1
  arms red first. Every arm carries a recorded claim per the house rule.
- **Verify-before-trust was applied to every cross-session and cross-repo
  report, and twice it mattered.** Mitate's "memo folded in" summary was
  verified against their working-plan row rather than accepted (it was
  faithful); the other session's retirement sweep was re-verified (agents
  dir, tree, memory — clean). The one report NOT initially verified — my
  own memory index — was the one that was wrong (below).
- **The sweep-first retirement discipline produced a
  deliberately-left list.** heylook-monitor's removal (`d14aec0`) sorted
  every hit before deletion; the `tune --project heylook` CLI example was
  correctly kept as third-party (names the external server repo).
- **Two sessions shared main all day without a collision.** Pathspec
  commits throughout; `docs/internals/control_audit_design.md` was edited
  from both ends (their shipped-status header, this session's two
  annotations) and all three edits survived.

## 2. What did not go well

- **The builder's own summary prose drifted twice on launch day.** The
  changelog miscount (above), then the end-of-day universals ("one copy of
  everything, every deferred obligation written down") which the owner's
  "how do we know" exposed as generalized from two verified pairs and an
  unverifiable enumeration. Structural version: **summary prose drifts even
  when its author built the anti-drift instrument that morning; only
  mechanical discipline transfers, so the discipline is now a memory and
  the claims got derived** (mutations, re-runs, pair diff).
- **A stale memory index produced a wrong claim to the owner.** MEMORY.md's
  screenwright line said retirement was pending while the memory body said
  done; the index line was relayed as fact ("no trigger yet") and had to be
  corrected after reading the body. Structural version: an index is a copy;
  reading the index without the body is trusting a copy nobody watches.
- **Untracked debris impersonated live units twice.**
  `skills/explainer-video/` and `apps/agent-state-mcp/` both listed like
  live units and both were cache/`.DS_Store` remains of completed
  retirements — `git rm` clears the index, every sweep reads the index, and
  `ls` reads the disk. Both deleted; the gotcha and the dangling-refs
  next-release step are filed (`docs/internals/gotchas.md`).
- **Small tool fumbles cost minutes each**: `python3` heredoc used directly
  once (house rule is `uv run python`); a `git add -A ':!internal'`
  pathspec error aborted a commit; two MEMORY.md appends landed without a
  leading newline and concatenated onto the previous line. None escaped;
  all were caught in-turn.
- **Stale pytest garbage in the system temp polluted every early test run**
  until `--basetemp` pointed at the scratchpad. Environment noise, not
  code, but it obscured the first red-run's output.

## 3. Deviations from the plan

| Planned | Shipped | Verdict |
|---|---|---|
| Claim-audit built from the design note, fresh session | 0.1.0 as designed: own plugin, no shipped agent, portability via local drift records (`9d85970`) | As planned |
| Gemini-bridge: recipe-free calls, all params as flags | 0.7.0, plus the recorded scan gap (schema, labels) closed unasked; 0.7.1 same day closed the bypass-warning trio | Better than planned |
| heylook-monitor: align bind/CORS (08-03 follow-up) | Retired entirely at the owner's call (`d14aec0`) | Better — closed by deletion, not patch |
| Control-audit: design note only, build next session | Note written and interviewed; the build landed same day in a parallel session (`docs/internals/control_audit_design.md` flipped to shipped) | Overtaken positively by the concurrent session |
| CLAUDE.md trim (surfaced late) | Deliberately not done; case queued with specifics (watch item 7) | Scoped down honestly |
| "Quick" postmortem at day end | This file | As planned |

## 4. Escapes (tests)

- **The "18 red first" claim escaped into commit `6a059b9`'s message and
  the changelog before being caught.** Which test should have caught it:
  none existed — `check_changelog_claims` audits version claims, not
  counts. The catching instrument was claim-audit itself, run minutes
  later; the commit message is immutable, the changelog was corrected. Not
  green-but-blind; genuinely uncovered class, now covered by the instrument
  built for it.
- **The claims-window defects (fenced `##` boundary, Unreleased stealing
  the window) shipped in skill-maintain 0.25.0 with no covering tests** and
  sat until the refactor read the code. Missing, not green-but-blind. Four
  arms now pin the window (`test_changelog_claims.py`), defects recorded
  red first.
- **One pin arm was born green with no fallibility proof** — surfaced by
  the owner's challenge, not by any check. Retroactive mutation proved it
  can fail (silent-fallback mutation went red); the general fix is the new
  TDD rule in `.claude/rules/general.md` (pins get one mutation at birth).
  Single instance; no green-but-blind repetition, so no whole-suite
  test-audit trigger yet — the filed mutation-sample maintain phase
  (`docs/internals/maintenance.md`) is the standing version.

## 5. Forward items

1. **Next session executes the queue** (`project_next_session_queue`
   memory): CLAUDE.md trim with claim-audit over the diff and the census
   after. Checkable: trim commit exists citing both instruments' outputs.
2. **Mitate adoption of the second memo
   (`internal/memo_claims_reminder_exposure.md`) confirmed against their
   working-plan file by ~2026-08-08**, else re-raised; window closes
   2026-08-24. Checkable: their registration text carries the exposure
   amendment, verified not reported.

   *Annotation 2026-08-04, same day:* the ~08-08 date was arbitrary and
   the owner challenged the class; the trigger is now event-based — check
   at the next session in this repo, raise if unconfirmed. The 08-24
   window close is the only real date: it bounds when amendment is
   legitimate. Queue memory updated to match.
3. **Gemini-bridge live smoke run**: one real ad-hoc call. Checkable: a
   ledger entry with `recipe: adhoc` and `status: completed` exists.

   *Annotation 2026-08-04, third session: DONE with the owner's go. Run
   `20260804T135757-adhoc`, gemini-3.6-flash, thinking minimal, 17 tokens
   total, 1629ms; ledger entry matches the checkable exactly
   (`recipe: "adhoc"`, `status: "completed"`, `prompt_scanned: true`);
   run dir carries prompt.md / request.json / response.md / usage.json
   and `stats` reads it back. 0.7.x has now touched the real API once.*
4. **The four release-time obligations fire at their releases** (claim-audit
   "where available" pointer; dangling-refs disk step; maintain
   mutation-sample; dev-conventions broadcast pin rule). Checkable per
   release changelog entry; the invalidation pass covers forgetting.
5. **The unpushed stack (12 at writing) reaches origin.** Checkable:
   `git log origin/main..HEAD` empty.

## Routing

Everything routable already routed during the session itself: the
derive-or-label memory, the pin rule in `.claude/rules/general.md`, the
verify-by-construction section in `VISION.md`, the watch list in that day's
session log (private, not published), and the release obligations in their own
docs (`docs/internals/plugin-patterns.md`, `docs/internals/gotchas.md`,
`docs/internals/maintenance.md`, `docs/internals/claim_audit_design.md`).
Nothing new earned promotion from this file.
