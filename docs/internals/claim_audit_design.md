last updated: 2026-08-04

# claim-audit: design note (BUILT 2026-08-04 — historical spec)

**Status: shipped as the `claim-audit` plugin (0.1.0, `skills/claim-audit/`).**
This note is now the design record; the skill file is the current behavior.
The build session's decisions, against the open questions below:

- **Packaging:** own plugin, as leaned — it runs pre-commit on any repo and
  couples to neither `postmortem` nor `skill-maintainer`.
- **Agent definition:** no shipped agent. The skill dispatches
  general-purpose subagents for the adversarial-input arm, briefed per-run
  with quoted claims — shapes, not state, per the `doc-claim-auditor`
  priors-rot incident.
- **Portability:** the mechanism and the claim-class table ship; the skill
  instructs citing the installing repo's own drift record where one exists,
  and a report-only first run to collect local examples where none does.

A skill (likely plugin) that audits the *added prose* of a diff as untrusted
claims — every count, status, and attribution re-derived by executing
commands, never by reading. Spec captured 2026-08-03 while the evidence was
context-resident; the build is deliberately deferred to a fresh session
(starting substantive builds at the tail of long sessions is how escapes
happen, per the sibling repo's postmortem record).

## Evidence base

A sibling repo (mitate, a scene-authoring project) measured review-instrument
yield on two independent samples:

| instrument | yield |
|---|---|
| reading a diff | ~0 |
| reading a quoted claim against its code | mid (9 findings, sample 1) |
| constructing an adversarial input | the only *code* defects (both samples) |
| reading a control against the thing it reimplements | highest (15 findings) |

An ordering measured twice is a protocol, not an observation. Scope caveat the
source repo itself insists on: this was measured where defects are
silent-by-construction (green-by-default corpus). A codebase whose failures
are visible in diffs weighs review differently. The skill must carry this
scope note rather than universalize the ordering.

Sample 1 also found that a day's output written *under unusual care* still
contained ten claims disagreeing with the code, nine authored that day — the
failure concentrates in summary prose, and freshness is the signal to check,
not the excuse not to.

## The spec (from the sibling repo's field-tested `verify-written-claims` skill)

The procedure that survived contact:

1. **Extract claims from added lines only** — counts (number bound to a noun),
   statuses (state assertion about repo/phase/file/branch), attributions (who
   or what found/caused/fixed a thing). By reading, not regex — a scanner
   cannot recognize a count in arbitrary prose (measured >85% FP in the source
   repo; generator-not-scanner is the standing precedent).
2. **Name the deriving command before running anything.** For each claim,
   write the command whose output IS the claim. No command nameable → that is
   itself the finding (step 4).
3. **Run them; record both sides.** One row per claim: sentence, command,
   output, verdict. Never pipe a validator through `tail`/`grep` (exit-status
   masking — bitten repeatedly in the record).
4. **Unsourceable claims get labeled, not failed**: rewrite to past tense with
   observation time, or tag `(memory)` / `(local)` / `(reported)`, or delete.
5. **Report states its own scope** — lines read, claims extracted, claims
   derived. A green report that cannot be told from a run that read nothing is
   the class this skill exists to catch, and it applies to the skill itself.
6. **Report, do not rewrite.** The caller fixes. Auditor findings need
   narrowing by the caller (2 of 4, then 2 of 6 auditors in the record
   returned findings that shrank on verification) — the weigh-it-yourself
   step is load-bearing, not ceremony.

Additional arms this repo's version adds beyond the source skill:

- **Quoted claims, never a directory.** "A vague scope returns a vague
  answer" was measured, not asserted. The skill should refuse or warn on
  directory-shaped scopes.
- **An adversarial-input instruction** when the diff touches executable
  behavior: one auditor told to *construct* hostile inputs and run them, not
  read. This instruction was "the entire difference" in finding the only true
  code defects in both samples.
- **A control-vs-reimplementation arm** when the diff touches anything that
  mirrors logic living elsewhere (a validator reimplementing its subject's
  semantics, a check duplicating a parser). Highest yield of any instrument;
  nothing had tried it until sample 1's annotation.
- **The invalidation pass** (the source skill's step 5): when a decision,
  merge, or version lands, grep the same day's output for the framing it
  invalidated — distinctive phrases of the *old* state, case-insensitive with
  stem variants (the one grep failure on record was `grep "delet"` missing
  `Deleting`). Newest prose is most likely wrong about a change, because it
  was written closest to it.

## Decisions for the build session

- **Packaging**: own plugin vs. joining `postmortem` (which owns the kindred
  test-audit) vs. joining `skill-maintainer`. Leaning: own plugin — it runs
  pre-commit on any repo, not just skills repos, and couples to neither.
- **Agent definition**: ship a claim-auditor agent (quoted claims + execute
  instructions as its briefing) or keep it a skill that dispatches
  general-purpose agents? The sibling repo's `doc-claim-auditor` priors-rot
  incident says agent briefings must carry *shapes, not state* — no
  present-tense drift examples baked into the agent body.
- **How much of the source skill generalizes**: its power comes from citing
  its own repo's failure record. The portable version ships the mechanism and
  the claim-class table; installing repos supply their own examples, or the
  messages read as someone else's scar tissue.
- **Relation to `control-audit`** (second candidate, separate note when
  designed): control-audit is the census instrument (per control: fires-via /
  guarded-by / retirement-condition / disclosed-uncontrolled-edges, "nothing"
  reportable in any slot); claim-audit is the prose instrument. Do not merge
  them — different subjects, different cadence.

## Annotation 2026-08-04, post-ship: the deferred primitive pointer must degrade

When the adversarial arm gains its pointer to `postmortem`'s
adversarial-verify / control-builder (deferred to the next content release
by the control-audit build's sequencing), remember the packaging decision
above: claim-audit is standalone by design. The pointer must read "where
available", with the current general-purpose dispatch as the fallback — a
hard reference would make a plugin chosen for coupling to nothing depend on
the one plugin it deliberately did not join.

## What would revise this note

- The build session finds the procedure does not transfer outside a repo with
  a dense failure record to cite — then the portable form needs its own
  evidence-gathering step (run once in report-only mode, collect the repo's
  own drift examples, then arm the messages).
- A third yield sample contradicting the ordering — then the instrument
  routing becomes configuration, not doctrine.
