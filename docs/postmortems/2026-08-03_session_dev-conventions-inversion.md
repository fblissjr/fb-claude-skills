---
mode: session
scope: dev-conventions-inversion
date: 2026-08-03
summary: The pre-push review out-yielded the session's own testing on work already tested — a third independent sample of the instrument ordering — and the session committed the exact compression-drift specimen it spent the day building defenses against, in the paragraph arguing those defenses work.
artifacts:
  - CHANGELOG.md
  - CLAUDE.md
  - docs/internals/gotchas.md
  - docs/internals/plugin-patterns.md
  - docs/internals/claim_audit_design.md
  - skills/dev-conventions/hooks/dev-conventions-session-start.sh
  - skills/dev-conventions/hooks/directives/
  - skills/dev-conventions/skills/init/SKILL.md
  - tools/skill-maintainer/tests/test_dev_conventions_directives.py
  - tools/skill-maintainer/src/skill_maintainer/tests.py
  - .skill-maintainer/best_practices.md
  - .skill-maintainer/state/pages/hooks.md
  - session log 2026-08-03 (private, not published)
---

# Postmortem: the dev-conventions inversion session (second session of 2026-08-03)

Started as a brainstorm over a sibling repo's context-binding memo (mitate;
its content is (reported) here — the memo itself lives in that repo's
internal tree). Ended having shipped five commits (`41a42cf`, `630e833`,
`7684a29`, `ecae5e3`, `f5d3f5b`): dev-conventions 0.14.0 → 0.15.1
(muting, then the scaffolder inversion, then review fixes), skill-maintainer
0.18.0/0.18.1, postmortem 0.6.1, skill-maintain 0.25.1, a design note, and
two pattern-doc sections. Ran concurrently with another session in this repo
for most of the afternoon.

## 1. What went well

- **Verify-don't-inherit caught a load-bearing error at the first hop.** A
  docs-research subagent reported that PreToolUse hooks cannot emit
  `additionalContext` — which would have invalidated the sibling repo's
  verified hook design. Checked against `.skill-maintainer/state/pages/hooks.md`
  (this repo's 2026-07-21 upstream snapshot): the snapshot says the opposite,
  twice. The one load-bearing claim checked against a primary source was the
  one the subagent had wrong. Structural version: a research agent's report
  is mechanism-1 prose like any other; verify the claim the design rests on,
  not a sample of convenience.
- **Testing the unhappy arm before shipping caught two real bugs pre-commit.**
  The all-muted-plus-rules[] arm caught the empty-context exit running before
  rules were appended (fixed inside `41a42cf`, recorded in CHANGELOG 1.3.0);
  the scratch battery's regression arm confirmed no-config behavior after the
  coverage rewrite (`7684a29`). Neither bug would have surfaced from the
  happy-path arms alone.
- **The cross-repo feedback loop worked with verification at every hop.**
  Outbound: this session's review of the sibling repo's claims-reminder
  apparatus (four findings, each grounded in the current hooks doc) landed
  there as their fix commit, which this session then re-verified by reading
  the changed files and running their bracket rather than trusting the
  report. Inbound: their friction report drove 0.14.0, and their granularity
  flag — auto-silence must check ground per block, not file existence —
  became 0.15.0's central design decision (`7684a29`,
  `skills/dev-conventions/hooks/dev-conventions-session-start.sh`).
- **Deferring the claim-audit build cost nothing because the spec was written
  first.** `docs/internals/claim_audit_design.md` captured the yield table,
  the six-step procedure, and the build decisions while all of it was
  context-resident (`630e833`). The build waits for a fresh session by
  design, not by loss.
- **Pathspec discipline held under real concurrency.** Two sessions, one
  branch, interleaved commits. Every commit here was staged by explicit
  pathspec; `.claude-plugin/marketplace.json` was partial-staged once so the
  other session's in-flight postmortem bump stayed theirs. Zero conflicts,
  zero swept files; their changelog-claims check
  (`tools/skill-maintainer/src/skill_maintainer/tests.py`) later ran green
  against this session's entries on its first execution.

## 2. What did not go well

- **The session committed the day's failure class, in the paragraph about
  defending against it.** `ecae5e3` wrote into `docs/internals/gotchas.md`
  that the live-repo silence was "pinned by a test arm" — no such arm
  existed; the verification had been a one-off scratch command. Written by
  the session that had spent the day cataloguing exactly this
  write-from-memory drift, minutes after re-reading the sibling repo's
  specimens of it. Caught by the pre-push review, fixed in `f5d3f5b` by
  writing the arm (`test_this_repo_stays_fully_covered`) rather than
  weakening the prose. Structural version: proximity to the lesson provides
  no protection; only a mechanism does — which is the sibling memo's binding-
  failure thesis, now with a specimen from this repo.
- **The ground patterns shipped over-matching, past a green pinning test.**
  0.15.0's patterns matched token mentions ("distributed via npm", the bare
  `last updated:` stamp) as ground coverage, wrongly silencing blocks with no
  recovery path, because mute could only force silence
  (`skills/dev-conventions/hooks/directives/`, fixed in `f5d3f5b`). The
  pinning test passed throughout — see Escapes.
- **The changelog was contended state under concurrency.** This session's
  1.4.0 entry collided with the other session taking 1.4.0 and 1.5.0
  mid-write (one Edit rejected on a modified file; renumbered to 1.6.0). The
  window in which this session's partial-staged marketplace held postmortem
  at 0.5.0 while their changelog entry claimed 0.6.0 became the founding
  specimen of their claims check (their CHANGELOG 1.5.0 entry). Cost was
  minutes, but the coordination was luck plus politeness, not mechanism —
  the sibling repo's claims-file convention exists for exactly this and was
  noted to the owner, not adopted.
- **A stale environment cost a detour.** Bare `pytest` from the repo root
  fails collection on the `coderef/` foreign clones (pre-existing; observed,
  not fixed). The first run also failed on a desynced venv until
  `uv sync --all-packages`. Neither is this session's defect; both cost time
  and neither is written down anywhere a fresh session would look.

## 3. Deviations from the plan

The stated task at session start: read the sibling repo's context-binding
memo and brainstorm "specific skills or plugins we can create that might help
mitigate some of this," plus check current docs.

| Planned | Shipped | Verdict |
|---|---|---|
| Brainstorm plugin candidates | Four candidates ranked, with evidence and sequencing | as planned |
| Check current Claude docs | Done, with the subagent's key claim refuted against the snapshot | as planned, with a correction the plan didn't anticipate |
| — (not planned) | dev-conventions 0.14.0: muting, property-not-form rules (`41a42cf`) | owner-directed expansion, driven by the sibling repo's field report |
| — (not planned) | The scaffolder inversion, 0.15.0/0.15.1 (`7684a29`, `f5d3f5b`) | owner-directed; grew from "what would make it frictionless ever" — the largest artifact of the session and not imagined at start |
| — (not planned) | Borrow docs: control-authoring checklist, bracket-the-hook (`630e833`, `.skill-maintainer/best_practices.md`, `docs/internals/plugin-patterns.md`) | as recommended, owner-approved |
| Build claim-audit (candidate #1) | Design note only (`docs/internals/claim_audit_design.md`); build parked with trigger | scoped down honestly, on the record |
| Package the provenance plugin | Not packaged; gated on the sibling repo's 2026-08-24 measurement | correctly not done — packaging before the pilot's own retirement test would ship an unvalidated control |

## 4. Escapes (tests)

- **Green-but-blind: the granularity pin pinned the friendly specimen.**
  `test_architecture_only_claude_md_stays_loud` was written with a CLAUDE.md
  hand-authored to contain no ground tokens — by the same mind that authored
  the patterns. It passed while five real-world token mentions silenced
  blocks wrongly. The review's adversarially-constructed specimens are now
  arms (`test_token_mentions_do_not_silence` in
  `tools/skill-maintainer/tests/test_dev_conventions_directives.py`,
  `f5d3f5b`). Structural version: a pinning specimen authored by the
  pattern's author pins the case the author already imagined; the specimens
  that matter are constructed by something trying to break the pattern.
- **Missing test asserted as existing:** the live-repo silence arm (section
  2). Now exists; the gotchas paragraph cites it by name.
- **Missing coverage for the metadata contract:** nothing exercised custom
  directives (ground off line 2, metadata-looking body lines) until the
  review named the asymmetry; `test_metadata_is_a_head_only_class` now runs
  a hook copy against a synthetic directives dir (`f5d3f5b`).
- **Tests added:** 18 arms total in the bracket file across the session, each
  carrying a rationale comment or a review-citation in the parametrize block;
  the file header states the rot modes the arms watch. This satisfies the
  claim-recoverable property via file-level convention — the form
  0.14.0's own rewording legitimized.

## 5. Forward items

1. **The re-enable decision closes one way or the other.** Checkable: either
   `.claude/settings.json` drops the dev-conventions disable (and CLAUDE.md
   invariant 6 is rewritten), or the owner declines and the premise paragraph
   in `docs/internals/gotchas.md` gains a dated "declined" note. Wrong-premise
   if `test_this_repo_stays_fully_covered` goes red first.

   **ANNOTATION 2026-08-17 — closed, first arm, and more completely than the
   item framed.** Derived, not recalled: `.claude/settings.json` carries no
   `enabledPlugins` key at all, and CLAUDE.md carries no invariant 6. The
   resolution is recorded at `docs/internals/gotchas.md:136` — dev-conventions
   was re-enabled 2026-08-03 and the remaining two disables were retired
   2026-08-04, the latter because the first control census found their stated
   rationale named SessionStart hooks both plugins had already deleted. So the
   item resolved not by the disable being lifted on its own merits but by the
   whole mechanism being retired, which the checkable did not anticipate.
2. **claim-audit builds from the note, in a fresh session.** Checkable: the
   skill exists with the four arms the note specifies, or the note gains an
   annotation saying what changed. Refuted-if: the build finds the procedure
   does not transfer without a local failure record — the note names this as
   its first revision trigger.

   **ANNOTATION 2026-08-17 — closed, first arm.** claim-audit ships as its own
   plugin. All four arms the note specifies at
   `docs/internals/claim_audit_design.md:74-88` are present, though not where a
   reader would look for them: three sit together in the extra-arms step, while
   "quoted claims, never a directory" landed in the scoping step instead.
   Counting the extra-arms bullets alone gives three and reads as a shortfall;
   the item is met. The refuted-if arm did not fire — the procedure transferred,
   and the note's own revision trigger stands unspent.
3. **2026-08-24: the sibling repo's measurement lands and the 0.16.0
   decision cites it.** Checkable by date. The bare-repo pointer ships, or
   the ambient blocks stay, and either way the changelog entry for whichever
   names the measurement.
4. **The two filed tests.py refactors happen at next touch.** Checkable: the
   next edit to either changelog check factors the shared top-section
   extractor and single-parse helpers (both specified in that day's session
   log, which is private and not published — the two refactors are named here
   in full, so the item is checkable without it), or the edit lands without
   them and this item was ignored.
5. **The instrument ordering now has a third sample; treat it as protocol
   here.** The pre-push review out-yielded this session's own testing on
   already-tested work (ten findings, eight acted on — CHANGELOG 1.6.1).
   Checkable: the next release-sized diff in this repo gets an
   adversarial-construction review before push. Refuted-if: two consecutive
   such reviews yield nothing this session's own testing missed — then the
   ordering does not transfer to this repo's defect profile and this item
   reverts to judgment-call.
