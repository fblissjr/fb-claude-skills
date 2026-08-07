---
name: test-audit
argument-hint: "[paths or test names to scope the audit] [--out=<dir>]"
description: "Audit an existing test suite for meaning and drift: recover each test's motivating claim, verify its oracle can actually fail (spot mutation — deliberately break the guarded behavior, confirm red), and map the reachability envelope (conditions the harness never exercises). Classifies tests as load-bearing, scar-tissue, decorative, or redundant and returns keep/rewrite/delete verdicts with evidence, written to a dated markdown file so the next audit can diff against it. Use when the user says 'audit the tests', 'test audit', 'are these tests testing the right thing', 'test drift', 'which tests are dead weight', 'do we trust this suite'. Do NOT use for writing new tests or for designing coverage on new features."
metadata:
  last_verified: "2026-07-24"
  review_interval_days: "365"
---

# Test audit

A test is three things, and a suite drifts when they separate:

- **The claim** — what its authors believed it verifies.
- **The oracle** — what it actually checks.
- **The envelope** — the conditions under which it runs (fixtures, configs,
  viewports, backends, data shapes).

A green suite proves only what its envelope can express, through oracles that
may no longer match their claims. The audit checks all three, per test, and
ends in verdicts — not observations.

The posture this runs on: **a green that never reached its subject is worse
than no check at all.** The rule, its failure shapes, and the verdict set are
in the plugin-level `../../references/verification.md`, shared with the other
skills here that verify. Read it at step 4, where it is used.

## Process

### 1. Inventory

Enumerate the suite: files, counts, runtime, and how it is invoked (local, CI,
both). Note tests skipped/disabled and for how long — a long-skipped test is
already a verdict waiting to be recorded.

### 2. Claim recovery

For each test (or coherent group), recover why it exists: the introducing
commit (`git log --follow` / `git blame` on the test), linked issue, or an
in-test comment. Record the claim in one line. **"Unknown" is itself a
finding** — a test whose claim nobody can recover cannot be maintained, only
appeased.

### 3. Classify

- **Load-bearing** — claim is a current requirement; failure would block a
  real defect.
- **Scar-tissue** — claim was a specific past incident whose conditions no
  longer exist; the oracle now constrains code without protecting anything.
- **Decorative** — the oracle cannot fail meaningfully (asserts a tautology,
  mirrors the implementation, or never reaches the subject).
- **Redundant** — another test's oracle strictly covers this one.

### 4. Oracle verification (spot mutation)

For the load-bearing tests — and any test whose classification is in doubt —
verify the oracle by breaking the thing it guards: introduce a deliberate,
targeted defect in the code under test, run the test, confirm red, revert.
A test that stays green under mutation of its own subject is decorative,
whatever its claim says. Work on a throwaway branch or stash; never leave a
mutation in place. This step is a dispatch to the `adversarial-verify`
protocol (shipped in this plugin): the break-and-confirm loop goes to the
`control-builder` agent, and a red — or a suspicious green — counts only
after a separate pass confirms the mutation actually reached the subject.
Read `../../references/verification.md` here; a mutation that never landed is
the failure this whole step exists to avoid, and it looks identical to a pass.
Full mutation tooling (mutmut, Stryker) is an escalation for suites where spot
checks keep failing, not the default.

### 5. Envelope mapping

Enumerate what the harness never exercises, by construction: one viewport, one
renderer, one locale, one database size, one config, one happy-path fixture
shape. State each as "defects of kind X are unreachable by this suite" — that
is a property of the harness, not of the code. The per-architecture question
packs in [references/architectures.md](references/architectures.md) list the
envelope questions that bite for each project shape (API/LLM server,
full-stack e2e, CLI, perceptual/generative, data pipeline).

### 6. Verdicts

Every audited test ends in exactly one verdict, with its evidence:

- **Keep** — claim current, oracle verified (or credibly failable), envelope
  understood.
- **Rewrite the claim** — the behavior is worth guarding but the recorded (or
  recoverable) claim is stale; update the test's stated purpose, and often its
  assertions.
- **Delete** — scar-tissue, decorative, or redundant, with the evidence named.
  List deletions for the user; do not apply them unasked.

Report the envelope gaps separately from the per-test verdicts — they are
suite-level findings and usually the most valuable output.

## Output: a filed artifact

**This audit writes a file.** Location, naming, and frontmatter come from the
plugin-level `../../references/filing.md`, the same ladder `postmortem` uses,
with mode token `audit` and the slug naming the suite or scope audited
(`2026-08-07_audit_skill-maintainer.md`).

Why this files when the sibling `control-audit` deliberately persists nothing:
a controls census is a snapshot of live configuration and goes stale the moment
a hook changes, so a stored copy competes with the code. Test verdicts are
judgments about *intent* — a recovered claim, a scar-tissue classification, an
envelope gap — which are expensive to reconstruct and do not rot on the same
clock. The value of auditing a suite twice is the diff against last time, and
there is no diff without a file.

Markdown only. There is no `--html` and no `--visuals` here: the output is
tabular verdicts whose reader is the next audit, and a rendering would be a
second format to keep in step for no reader that exists yet.

Same annotate-don't-rewrite rule as a postmortem. A verdict overturned by later
evidence gets a dated annotation under it, never a silent edit — a deleted test
that turns out to have been load-bearing is precisely the record worth keeping
intact.

## Forward convention

Recommend (and apply to tests touched during the audit): every new test
carries a one-line note of what breaks if it is deleted — the motivating
requirement, bug, or incident. This is what makes the next audit cheap.
