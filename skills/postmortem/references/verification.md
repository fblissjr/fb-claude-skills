# Verification: the needle rule

last updated: 2026-08-07

Shared across this plugin. `adversarial-verify` states the protocol,
`test-audit` dispatches to it per test, `control-audit` per control, and the
`control-builder` agent executes it. This file is where the rule itself lives,
so the four cannot drift into four wordings of it.

Read it at the dispatch point. Nothing here needs to be in context before a
verification actually happens.

## The rule

> **A green that never reached its subject is worse than no check at all.** It
> converts an open question into a settled one, and nobody revisits a settled
> question.

That is the whole thing. Everything below is how it goes wrong in practice.

A control, a mutation, a live-fire violation, and a spot-check are the same
move under different names: remove or break exactly one thing, and confirm the
result changes. The move fails the same way in all four — the removal or the
break never reached the input, so the run measured nothing and returned green.

## Verify the attempt landed, before believing either outcome

The judgment splits in two, and they stay separate on purpose:

1. **Did the violation reach the subject's input?**
2. **What did the subject do about it?**

Answer (1) first and independently. A control can be right for a bogus reason,
and both facts belong in the record. **The constructor does not grade its own
needle** — the check on (1) is a fresh pass over the run's own evidence (its
diff, its command transcript, its measurements), by the caller or a second
dispatch, answering only whether the violation landed and not whether the
verdict was right.

## The recurring ways an attempt silently misses

This list is maintained here and nowhere else.

- A "does it fail without X" run where X was still present.
- A mutation that shell quoting turned into a literal matching nothing, so the
  run was a no-op.
- An injected perturbation assigned to a variable overwritten before it reached
  any output.
- A check that never modified the file it claimed to break.
- A test that never executed the code path it asserts about.
- A pattern-anchored control whose synthetic violation was made so visibly fake
  that it no longer matches the pattern being tested.

**Confirm the file changed, the command errored or didn't, the dependency was
actually absent.** Show it; do not infer it.

Symptom to watch for: **a control that passes on the first attempt, testing
something you expected to be broken.** That is the shape, more often than not.

## Verdicts

Four, not three:

| Verdict | Meaning |
|---|---|
| confirmed | The claim survived a real attempt to refute it. |
| refuted | The attempt succeeded; the claim is false. |
| no separation | Both sides measured the same. The mechanism was not doing the work — a real and common finding, not a failed run. |
| **vacuous** | The needle never threaded. Sends the construction back; counts for neither side. |

`vacuous` is the caller's verdict, not the constructor's, and that is the
boundary the two-judgment split exists to create. A constructor reports
confirmed / refuted / no separation over the run it performed; only a pass that
did not perform it can overturn all three to vacuous.

## Thresholds bracket

A claim that is a threshold is not verified until it brackets: one observation
confirmed bad above the line, one confirmed fine below it. An unbracketed
threshold is a guess with a number on it and should be labelled as one.

## A proxy can reject, never approve

A lint, heuristic, or snapshot **passing** does not establish the property.
Only its failure establishes anything. This is the same rule from the other
side: a green from an instrument that cannot express the property is not weak
evidence, it is no evidence.
