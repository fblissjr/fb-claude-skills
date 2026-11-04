---
paths:
  - "**/hooks/**"
  - "tools/**"
  - "**/tests/**"
---

# Controls and checks

A control fails when it is trusted because it exists rather than because
anything watches it. `/postmortem:control-audit` censuses them.

- The header says why not the obvious alternative, the measured false-positive
  rate with its sample, what it does not do, and the retirement trigger: the
  condition under which it is deleted rather than tuned.
- A rule earns its tier (AGENTS.md invariant 1c). When a class a reminder
  covers becomes checkable, it gets a real check and leaves the reminder.
- Reminders are deduplicated and their fire rate measured on real history
  before shipping. A reminder that fires on most actions trains dismissal of
  the whole channel.
- A green states its scope: print the derived count of what was covered. "0
  hits" is indistinguishable from a run that checked nothing, and a `| head`
  pipeline hides a failed glob.
- A proxy can reject; it cannot approve. Give a heuristic authority only over
  its confident region and make it silent elsewhere, or hand the rest to a real
  measurement. A warning band trains skimming.
- Prefer a fixture that cannot collide over one that probably will not.
- Bracket the control: prove it can go red, pin its silent edges, check that
  examples its messages cite still resolve, and live-fire a new gate once.
- A wrapper needs a check that its target is still called. A patch on a method
  nobody calls passes its binding test and does nothing.

## One claim in several places

A claim kept once is maintained; kept in four places it is stale in three, and
nothing is red.

- Assert that paths agree, not only that each is right. Per-path tests are
  blind to cross-path divergence.
- A copied shape drifts like a copied constant: a docstring or documentary
  model describing a structure no assertion reads.
- Sweep the generated artifact, not the source (the rendered schema, the
  published listing, the manifest), using the strings you just replaced as the
  input. A clean sweep proves only those strings are absent.
- The widest-reach copy is the least reread: a skill `description` sits in
  every session's listing and above the body being edited.
