---
name: test-audit
description: "Audit an existing test suite for meaning and drift: recover each test's motivating claim, verify its oracle can actually fail (spot mutation — deliberately break the guarded behavior, confirm red), and map the reachability envelope (conditions the harness never exercises). Classifies tests as load-bearing, scar-tissue, decorative, or redundant and returns keep/rewrite/delete verdicts with evidence. Use when the user says 'audit the tests', 'test audit', 'are these tests testing the right thing', 'test drift', 'which tests are dead weight', 'do we trust this suite'. Do NOT use for writing new tests or TDD (use tdd-workflow) or for designing coverage on new features."
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

Two standing cautions from measured experience:

- **A green control that never ran is the worst outcome** — a check that
  passes because it never reached the behavior it guards reads as coverage.
  Whenever you verify an oracle, first verify the test actually executed the
  code path (a deliberate break must go red; if it stays green, the test never
  touched the subject).
- **A proxy can reject, never approve.** A lint, heuristic, or snapshot
  passing does not establish the property; only its failure establishes
  something.

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
mutation in place. Delegate the break-and-confirm loop to a subagent where one
is available (in repos that ship a `control-builder` agent, that is its job).
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

## Forward convention

Recommend (and apply to tests touched during the audit): every new test
carries a one-line note of what breaks if it is deleted — the motivating
requirement, bug, or incident. This is what makes the next audit cheap.
