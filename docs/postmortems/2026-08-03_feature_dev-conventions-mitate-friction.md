---
mode: feature
scope: dev-conventions-mitate-friction
date: 2026-08-03
summary: The friction was structural, not a bad rule — a generic form shipped over a sharper local property with no per-block escape — and the fix took three rounds in one day because the first was rent reduction and the second inverted the failure direction before force-load closed it.
artifacts:
  - 41a42cf
  - 7684a29
  - f5d3f5b
  - CHANGELOG.md
  - CLAUDE.md
  - .claude/settings.json
  - docs/internals/gotchas.md
  - docs/internals/plugin-patterns.md
  - skills/dev-conventions/hooks/dev-conventions-session-start.sh
  - skills/dev-conventions/hooks/directives/
  - skills/dev-conventions/skills/configure/SKILL.md
  - skills/dev-conventions/skills/init/SKILL.md
  - tools/skill-maintainer/tests/test_dev_conventions_directives.py
  - docs/postmortems/2026-08-03_session_dev-conventions-inversion.md
---

# Postmortem: the dev-conventions friction mitate reported, and the fix arc

Scope: the friction the dev-conventions plugin caused its first sophisticated
consumer (the sibling repo mitate), and the three-round fix shipped 2026-08-03
as 0.14.0 → 0.15.0 → 0.15.1 (`41a42cf`, `7684a29`, `f5d3f5b`). The mitate
side of the evidence is (reported) — relayed by the owner from that session on
2026-08-03 — except where this repo's own record confirms it. The wider
session containing this arc has its own postmortem
(`docs/postmortems/2026-08-03_session_dev-conventions-inversion.md`);
this file stays on the feature.

## 1. What went well

- **The consumer's friction report was precise enough to act on the same
  day.** It named the exact colliding rule (the TDD block's "one line on what
  breaks if it is deleted"), the exact cost (twice formally disclosing a
  "shortfall" against a form its own stronger, mechanically-enforced rule
  does not use — (reported)), and the principle (ambient text earns its place
  by biting). 0.14.0 (`41a42cf`) shipped hours later. Structural version: a
  consumer that reports friction as rule-plus-cost-plus-principle hands the
  maintainer the fix; a consumer that reports "the plugin is annoying" hands
  them nothing.
- **Verifying the consumer's operational claim before acting caught a
  product gap.** The report claimed "/dev-conventions:configure does per-repo
  trims." Read against the hook source
  (`skills/dev-conventions/hooks/dev-conventions-session-start.sh` as of that
  morning), it was false: `enforce.*` gated only the PreToolUse hook and
  nothing could mute a SessionStart block short of disabling the plugin —
  which is exactly how this repo itself ran it (`.claude/settings.json`,
  CLAUDE.md invariant 6). The trim mitate wanted was unexpressible, so the
  feature got built instead of a consumer hitting a dead end mid-config.
  Structural version: a consumer's claim about your product's capabilities
  is a claim like any other — verify it against the source before either of
  you acts on it.
- **The consumer's design review arrived pre-build and changed the design.**
  The 0.15.0 spec's auto-silence was file-existence detection; mitate's flag
  — nearly every active repo has a CLAUDE.md that says nothing about
  package managers, so file existence is de facto deletion of the ambient
  tier — became per-block ground coverage (`7684a29`), which is the feature's
  load-bearing mechanism. Cheapest possible timing for a design correction.
- **The friction generalized instead of staying a one-repo patch.** The
  structural diagnosis (generic-form-over-local-property, broadcast's four
  friction properties) is recorded as the scaffolder-not-broadcaster pattern
  in `docs/internals/plugin-patterns.md`, with `dimensional-modeling` and
  `mece-decomposer` named as next candidates.

## 2. What did not go well

- **The friction was shipped by design and paid twice before it was
  reported.** The plugin stated forms ("one line per test"; "date at top of
  every doc") where consumers with mature conventions satisfy the property
  under different forms — mitate disclosed a false shortfall in two separate
  documents before the report reached this repo ((reported); the collision
  class is confirmed in this repo's own record by CHANGELOG 1.3.0's account).
  The only escape was all-or-nothing disable, which this repo's invariant 6
  had already chosen — losing the enforcement hooks along with the prose.
- **Round one was rent reduction, not dissolution.** 0.14.0's muting kept
  the two-party ownership structure (the consumer's own assessment —
  (reported)) and required a second design round the same day. The inversion
  (0.15.0) is what dissolved it.
- **Round two inverted the failure direction instead of closing it.** The
  0.15.0 ground patterns over-matched token mentions — including the bare
  `last updated:` stamp the doc-conventions directive itself mandates
  (`skills/dev-conventions/hooks/directives/`, CHANGELOG 1.6.1) — so the fix
  for over-broadcast created over-silencing, with no recovery because mute
  could only force silence. The force-load state and rule-shaped patterns
  (`f5d3f5b`) are what finally closed both directions. Structural version:
  a fix that moves a failure from one direction to the other is half a fix;
  closing means an escape exists in both directions.
- **The three-round shape cost three version bumps in one day** (0.14.0,
  0.15.0, 0.15.1 — CHANGELOG 1.3.0, 1.6.0, 1.6.1). Not churn to hide: each
  round's defect was found by a different instrument (consumer field report,
  consumer design review, adversarial pre-push review), which is measurement
  the arc could not have produced faster in fewer rounds. Inference, labelled:
  had the pre-push review run against the 0.15.0 spec rather than its code,
  round three might have merged into round two.

## 3. Deviations from the plan

The plan, as the consumer stated it: trim the generic TDD and doc blocks for
mitate via `/dev-conventions:configure`, keep the bun block and log cadence.

| Planned | Shipped | Verdict |
|---|---|---|
| Trim two blocks via existing configure | The trim capability did not exist; 0.14.0 built it (`directives` muting, `41a42cf`) | plan's premise was false; verified before execution rather than during |
| Keep using muting per repo | 0.15.0 made muting mostly unnecessary — blocks silence themselves per ground coverage (`7684a29`); mitate's mute config became moot, as designed | better than planned — the manual trim became automatic |
| — (not planned) | `/dev-conventions:init` scaffolder: conventions written into the repo's own files, reaching every collaborator (`skills/dev-conventions/skills/init/SKILL.md`) | expanded deliberately — the owner asked what would remove the friction permanently, and distribution turned out to be the real argument |
| — (not planned) | Force-load state + rule-shaped patterns (`f5d3f5b`) | unplanned rework from the pre-push review; closed the inverted failure direction |
| Bare-repo pointer (broadcast fully retired) | Deliberately not shipped; gated on mitate's 2026-08-24 measurement (CHANGELOG 1.6.0) | scoped down honestly, trigger on record |

## 4. Escapes (tests)

- **The granularity pin was green-but-blind through round two.** The arm
  guarding "an architecture-only CLAUDE.md silences nothing" used a specimen
  hand-authored to contain no ground tokens, by the author of the patterns;
  it passed while five real-world token mentions silenced blocks wrongly.
  The adversarially-constructed specimens are now arms
  (`test_token_mentions_do_not_silence` in
  `tools/skill-maintainer/tests/test_dev_conventions_directives.py`).
- **Nothing could have caught the false configure claim mechanically.** A
  skill's prose asserting a capability the code lacks has no check in either
  repo; it was caught by reading the source. This is the class the
  claim-audit design note exists for, and this escape is a named motivating
  specimen for it.
- **Tests added across the arc:** 18 arms in the bracket file, covering
  fire/silence per class, mute and force-load, metadata head-only handling,
  the five over-match specimens, and the live-repo silence pin
  (`test_this_repo_stays_fully_covered`) that doubles as the re-enable
  premise guard cited by `docs/internals/gotchas.md`.

## 5. Forward items

1. **Mitate's mute config comes out.** Checkable: their `.dev-conventions.json`
   drops its `directives` keys once 0.15.1 reaches them (coverage supersedes
   it), or a reason is recorded there. Wrong-premise if their local rules'
   phrasing slips past the rule-shaped patterns — in which case `force` is
   the wrong tool and the pattern needs their specimen.

   **ANNOTATION, 2026-08-03 (same day) — done, and the wrong-premise arm
   half-fired.** The keys came out ((reported): their config is now
   `{"directives": {}}`, verified against the installed 0.15.1 with a
   counterfactual line-deletion test). But the javascript block's silence
   rests on a command example matching the pattern while the repo's genuine
   bun declaration (a bare token in a tooling list) matches nothing — right
   verdict, wrong line read. They correctly declined both `force` and
   writing a bun rule just to make the silence earned ("making a check pass
   by touching what it measures"), and sent the specimen upstream instead.
   Recorded with its tuning trigger in `docs/internals/plugin-patterns.md`;
   the item closes as done-with-specimen rather than clean.

   **ANNOTATION 2, 2026-08-03 (later the same evening) — the verdict above
   was itself corrected, the trigger fired, and 0.15.2 shipped.** The
   consumer measured that "right verdict, wrong line read" was untenable:
   the trigger gate short-circuits coverage, so the coverage verdict was
   moot on any clone and wrong on the one machine where it ran ((reported),
   verified by their `bash -x` traces both ways). That is the
   wrong-direction case this item named as its tuning trigger, so tuning
   stopped being deferred: 0.15.2 ships fence-stripped prose-only coverage
   (their tested fix — the rule-vs-command discriminator is positional),
   force overriding both gates (their loop-trace finding: force could not
   recover a trigger miss), and `--explain` (their argument that without an
   instrument, specimen-counting triggers are unreachable by construction).
   A further specimen — the two hooks "disagreeing" about JS-ness — was
   raised and withdrawn by their own per-directory measurement the same
   evening; the withdrawal is recorded in plugin-patterns.md because the
   false inconsistency came from testing at the wrong cwd. Their end state:
   mute keys out, nothing forced, plugin kept (zero ambient cost, one live
   enforcement arm).
2. **2026-08-24, the pre-registered measurement reports.** Checkable by
   date: mitate's correction-rate data either supports retiring broadcast
   for bare repos (0.16.0 pointer ships, citing it) or shows the ambient
   blocks earning their keep (the arc stops at 0.15.x and the changelog says
   why).
3. **The second broadcaster converts or the pattern stays provisional.**
   Checkable: `dimensional-modeling` or `mece-decomposer` gets the
   scaffolder treatment at next substantive touch (named in
   `docs/internals/plugin-patterns.md`), or six months pass and the pattern
   section gains an annotation that N stayed at 1.
4. **This repo's own disable gets decided on the new premise.** Checkable:
   `.claude/settings.json` re-enables dev-conventions (restoring the
   enforcement hooks at zero ambient cost, per the premise paragraph in
   `docs/internals/gotchas.md`) or the decline is dated there.
