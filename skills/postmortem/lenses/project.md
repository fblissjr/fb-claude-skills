---
lens: project
audience: Your future self, and the next model to work in this repo.
use-when: Work this repo did is finished — a session, a feature, a span of sessions. The default lens.
---
# Project

The default lens, and the one most postmortems want. The subject is work this
repo did; the reader is whoever picks the work back up, which is usually you or
a model reading the record months later.

Because the reader shares the repo, findings can name files, commits, and
conventions without explaining them. That is the main thing separating this
lens from `experience`, whose reader has never seen this codebase.

## Sections

Five, in this order. Keep each finding to a few sentences: the claim, the
citation, and — only when it generalizes — the structural lesson.

### 1. What went well

Only items with evidence that a deliberate choice paid off. **"The tests
passed" is not a finding**; "the contract seam let every tool run unchanged
against the new backend on the first try" is.

This section is not politeness. It is the record of what should not be undone
by a later refactor that does not know why something was built that way.

### 2. What did not go well

Include negative results (things built and discarded), wrong premises acted on,
and cost sinks. **A repeated failure shape across items is itself a finding**:
say the pattern plainly rather than listing three instances of it separately.

### 3. Deviations from the plan

A three-column table: **Planned | Shipped | Verdict**.

The verdict is honest in both directions — "better than planned" is an allowed
verdict, and so is "scoped down honestly". Work with no plan doc still gets this
table: the Planned column comes from what the task was stated to be at the
start.

### 4. Escapes (tests)

For every bug found during the scope, ask the discriminating question:
**which test should have caught this, and why didn't it — missing, or
green-but-blind?**

Also the inverse: did the scope add tests, and does each carry a recorded claim
(what breaks if it is deleted)? Escapes here are real events, so this section
needs no speculation.

Repeated green-but-blind escapes are the trigger to run the sibling `test-audit`
skill over the whole suite. Say so when the pattern appears.

### 5. Forward items

Each forward item must be **checkable**: phrased so a future reader can mark it
done, refuted, or wrong-premise. "Consider improving performance" fails that
bar; "measure X on hardware Y; if under Z, the premise of item N was wrong"
passes it. **An item that cannot be refuted is an opinion — cut it.**

## Routing

After writing, sort what should outlive the document:

- Durable lessons about how the user or project works → propose a memory or
  CLAUDE.md addition (propose; do not silently edit CLAUDE.md).
- A mistake that will repeat mechanically → suggest a hook or check.
- Follow-up work → the repo's task list, roadmap, or session log.

Route only what earned it. Most findings correctly stay in the postmortem.
