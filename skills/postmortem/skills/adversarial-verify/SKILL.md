---
name: adversarial-verify
argument-hint: "[the claim, check, or green result to verify]"
description: "Verify something about to be trusted by trying to refute it, in two separate judgments: construct the experiment that would prove it false (dispatched to the control-builder agent), then independently verify the attempt actually reached the subject before believing either outcome. Use when the user says 'adversarially verify this', 'build the control', 'try to refute this', 'prove this check can fail', 'did that green actually test anything', or when a new check, threshold, or 'this technique helps' belief is about to be trusted, or a result came back green where red was expected. Do NOT use for auditing a whole test suite (use test-audit) or for auditing prose claims (use claim-audit) — this is the single-claim primitive those audits dispatch to."
---

# Adversarial verify

Reading a thing and nodding is the lowest-yield verification instrument on
record; constructing the input that would break it is the highest. This skill
is that move, stated once, as two separate judgments:

1. **Construct the refutation.** Build and run the experiment that would
   prove the claim false — the same subject with the single claimed cause
   removed, the deliberate violation the check should catch, the input the
   threshold should reject. Dispatch this to the `control-builder` agent
   (shipped beside this skill); its method and report shape are the
   contract.

2. **Verify the needle was threaded.** Before trusting either outcome, prove
   the attempted violation actually reached the subject's input. The
   recurring ways an attempt silently misses are listed under the agent's
   *verify the control actually ran* step — that list is the constructor's
   own checklist, maintained there and only there. A green whose needle
   never threaded is the worst outcome of all: an open question converted
   into a settled one.

Constructor and verifier are separate judgments, kept separate on purpose:
judge the gate and the outcome separately, because a control can be right
for a bogus reason, and both facts belong in the record. Do not let the
constructor grade its own needle — the verification is a fresh pass over the
run's evidence (its diff, its command transcript, its measurements), by the
caller or a second dispatch, answering only "did the violation reach the
subject", not "was the verdict right".

## How a control couples to its subject

Two failure modes sit at opposite ends of one axis, and both yield a control
that tells you nothing:

- **Derived from the subject.** A control whose input is computed from the
  thing it checks cannot fail — the expectation moves with the subject. This
  is the common one, and it survives review because the code looks correct.
- **Duplicating the subject.** A control carrying a copy of its subject's
  content goes red when the subject is *correctly* changed. A false red is
  worse than no check, because it teaches people to override the gate.

The stable middle is coupling by **stable identifier** — a symbol name, a path,
an ID. `path::symbol` is the checkable form: it survives insertions above the
target and fails only when the named thing stops existing. Never couple by
position (`path:line`, "step 4", "the third bullet"), which misaims silently
and so fails without ever looking wrong. Never couple by content.

Where an enumeration's order carries meaning, a third option is to **freeze the
numbering** — state in the document that entries are removed rather than
renumbered, making the position a stable identifier by fiat.

## When a thing is "about to be trusted"

- A new check, hook, or validator is about to start gating work.
- A threshold is about to be adopted (verify it brackets: one observation
  confirmed bad above, one confirmed fine below).
- A "this technique helps" belief is about to shape a design.
- A result came back green where you expected red — the strongest trigger,
  and the one most often waved through.

## Outcome

Relay the control-builder report (claim, control with proof it took effect,
both measurements, verdict) plus the verifier's separate finding on the
needle. Four verdicts are possible, not three: confirmed, refuted, no
separation — and **vacuous**, when the needle never threaded, which sends
the construction back rather than counting for either side.

The siblings apply this protocol to their own subjects: `test-audit`'s spot
mutation (per test) and `control-audit`'s live-fire (per hook or validator)
are dispatches to this primitive. `claim-audit`'s adversarial arm states
the same move independently today and gains its explicit pointer here at
its next content release.
