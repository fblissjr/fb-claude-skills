---
name: claim-audit
argument-hint: "[diff ref, files, or quoted claims to audit]"
description: "Audit the added prose of a diff as untrusted claims: every count, status, and attribution re-derived by executing commands, never by reading. Reports each claim beside the command whose output is that claim, labels what cannot be derived, and states its own scope so a green report is distinguishable from a run that read nothing. Use when the user says 'audit the claims', 'claim audit', 'verify this summary against the code', 'check what the changelog says actually happened', 'is this doc telling the truth', or before committing prose that describes work — session logs, changelogs, READMEs, postmortem summaries. Do NOT use for auditing a test suite (use test-audit) or for reviewing code changes themselves (use a code review)."
metadata:
  last_verified: "2026-08-04"
  review_interval_days: "365"
---

# Claim audit

Prose written about work disagrees with the work at a measured, repeatable
rate — and the disagreement concentrates in the newest writing. A day's output
written under unusual care still contained ten claims that disagreed with the
code, nine of them authored that day. Freshness is the signal to check, not
the excuse to skip checking.

The instrument: treat every claim in the *added lines* of a diff as untrusted,
and re-derive it by running a command whose output IS the claim. Reading the
code and nodding is not derivation — reading a diff was the lowest-yield
review instrument in both samples that motivated this skill.

**Scope caveat, carried on purpose:** the yield ordering behind this skill was
measured where defects are silent by construction (a green-by-default corpus).
A codebase whose failures show up loudly in diffs weighs plain review more
highly. Apply the procedure; do not universalize the ordering.

## What counts as a claim

| Class | Shape | Example |
|---|---|---|
| Count | a number bound to a noun | "18 new test arms", "suite at 225" |
| Status | a state assertion about repo, phase, file, or branch | "all green", "not started", "committed", "the flag defaults to false" |
| Attribution | who or what found, caused, or fixed a thing | "caught by the hook", "pinned by a test", "the reviewer's finding" |

Extract by reading, not by regex — a scanner cannot recognize a count in
arbitrary prose (measured above 85% false positives when tried). You are the
generator; there is no scannable pattern.

## Procedure

### 1. Scope to added lines

The subject is the *new* prose: `git diff` added lines, the file about to be
committed, or the claims the user quoted. **Quoted claims, never a
directory** — a vague scope returns a vague answer (measured, not asserted).
If handed a directory-shaped scope, narrow it first: which files, which
sections, which sentences.

### 2. Extract the claims

List every count, status, and attribution in the scoped prose. One line each,
verbatim or near-verbatim.

### 3. Name the deriving command before running anything

For each claim, write the command whose output is the claim: the `grep -c`,
the `pytest -q` tail, the `git log` line, the `jq` read. Naming it first is
the discipline — a command chosen after seeing output drifts toward
confirming. **No command nameable is itself the finding** (step 5).

Never pipe a validator through `tail` or `grep` for the verdict — exit-status
masking has bitten repeatedly. Capture the exit status, then filter for
display.

### 4. Run them; record both sides

One row per claim: the sentence, the command, its actual output, the verdict.
Output pasted, not paraphrased — the row must let a reader disagree with your
verdict.

### 5. Label the unsourceable; do not fail it

A claim with no deriving command gets one of:

- rewritten to past tense with an observation time ("as of the 10:30 run, ..."),
- tagged `(memory)`, `(local)`, or `(reported)` — stating where it came from,
- or recommended for deletion.

These are report recommendations for the caller — see step 7.

### 6. Run the extra arms when the diff qualifies

- **Adversarial input** — when the diff touches executable behavior, spend
  one pass *constructing* hostile inputs and running them, not reading. This
  instruction was the entire difference in finding the only true code defects
  in both motivating samples. Dispatch it as its own subagent pass where
  available, briefed with the quoted claims and the instruction to execute.
- **Control vs. reimplementation** — when the diff touches anything that
  mirrors logic living elsewhere (a validator reimplementing its subject's
  semantics, a check duplicating a parser), read the two side by side for
  divergence. Highest yield of any instrument measured.
- **Invalidation pass** — when a decision, merge, or version just landed,
  grep the same day's output for the framing it invalidated: distinctive
  phrases of the *old* state, case-insensitive, with stem variants (`delet`
  misses nothing; `deleted` missed `Deleting` on record). Newest prose is
  most likely wrong about a change because it was written closest to it.

### 7. Report; do not rewrite

The caller fixes. This is load-bearing, not ceremony: in the record, auditor
findings shrank on the caller's verification in two of four, then two of six
cases. Present findings as claims-with-evidence; let the caller weigh them.

## The report states its own scope

Every report ends with three numbers: lines read, claims extracted, claims
derived by execution. A green report that cannot be told from a run that read
nothing is exactly the class this skill exists to catch — and that applies to
the skill's own output first.

```
scope: 214 added lines read, 17 claims extracted, 14 derived, 3 labeled
```

## Grounding in this repo's record

Findings land harder citing the installing repo's own failures than someone
else's scar tissue. If the repo keeps postmortems, session logs, or a
changelog, cite its own prose-drift incidents when reporting. On a first run
in a repo with no such record, run report-only: collect the drift examples
this audit itself surfaces, and let them become the local evidence base.
