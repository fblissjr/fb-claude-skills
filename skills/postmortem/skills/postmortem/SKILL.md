---
name: postmortem
description: "Evidence-grounded postmortem of finished work — a session, a feature, or a span of sessions. Recovers what went well, what did not, deviations from plan, and test escapes; every finding must cite a concrete artifact, and empty sections are valid output. Use when the user says 'postmortem', 'run a postmortem', 'retrospective', 'what went well', 'what would you do differently', or wants a look back at a completed plan, task, bugfix, feature, or run of sessions. Span mode mines git history, session logs, and changelogs. Do NOT use for auditing a test suite (use test-audit) or for drafting a session log."
metadata:
  last_verified: "2026-07-24"
  review_interval_days: "365"
---

# Postmortem

A postmortem is a verdicted retrospective of finished work. Its findings are
claims about what actually happened, so every claim must be grounded in an
artifact. The deliverable is judgment, not a log: what the work revealed, where
it deviated from intent, and what that implies going forward.

The single most important rule: **no citation, no finding.** A finding names a
concrete artifact — a file, a commit, a failed command, a measurement, a
decision visible in the record. Generic advice ("could add more tests",
"communication could improve") is banned. If a section has no grounded
findings, write "Nothing." — **an empty section is valid output, not a
failure.** Never invent an item to fill a frame.

## Scope: two modes

Chosen by the argument:

- **Session mode** (no argument, or "this session"): the evidence base is the
  current conversation — decisions made, errors hit, detours taken, bugs found
  and fixed, commands that failed, assumptions that turned out wrong.
- **Span mode** (an argument naming a feature, git range, plan doc, or "the
  last N sessions"): the evidence base is the repository record. Gather, in
  order of value:
  1. The plan doc, if one exists (needed for the deviations table).
  2. `git log` over the range — commits, messages, what was reverted or
     re-fixed.
  3. Session logs (`internal/log/log_*.md` or the repo's equivalent).
  4. `CHANGELOG.md` entries in the range.

Do the evidence pass **before** writing any finding. In span mode, read the
record first; do not reconstruct the span from memory of it.

## Format

Five sections, in this order. Keep each finding to a few sentences: the claim,
the citation, and — only when it generalizes — the structural lesson.

### 1. What went well

Only items with evidence that a deliberate choice paid off. "The tests passed"
is not a finding; "the contract seam let every tool run unchanged against the
new backend on the first try" is.

### 2. What did not go well

Include negative results (things built and discarded), wrong premises acted
on, and cost sinks. A repeated failure shape across items is itself a finding:
say the pattern plainly.

### 3. Deviations from the plan

A three-column table: **Planned | Shipped | Verdict**. The verdict is honest
in both directions — "better than planned" is an allowed verdict, and so is
"scoped down honestly". Session mode without a plan doc still gets this table:
the Planned column comes from what the task was stated to be at the start.

### 4. Escapes (tests)

For every bug found during the scope, ask: **which test should have caught
this, and why didn't it** — missing, or green-but-blind? Also the inverse: did
the scope add tests, and does each carry a recorded claim (what breaks if it
is deleted)? Escapes here are real events, so this section needs no
speculation. Repeated green-but-blind escapes are the trigger to run the
sibling `test-audit` skill on the whole suite.

### 5. Forward items

Each forward item must be **checkable**: phrased so a future reader can mark
it done, refuted, or wrong-premise. "Consider improving performance" fails
that bar; "measure X on hardware Y; if under Z, the premise of item N was
wrong" passes it. An item that cannot be refuted is an opinion — cut it.

## Ground rules

1. **No citation, no finding** (see above).
2. **Empty sections are valid.** The expected honest output for a small clean
   task is mostly "Nothing."
3. **Annotate, do not rewrite.** A postmortem is append-corrected: when later
   evidence contradicts a finding, add a dated annotation under it stating
   what changed — never silently edit the original. A postmortem that slips
   its own conclusions quietly is worse than none.
4. **State the structural version.** When a defect or win generalizes beyond
   its instance, write the general form in one plain sentence. That sentence
   is the part that transfers.
5. **Distinguish measurement from inference.** Label anything not directly
   observed as inference.

## Output: a file, always

A postmortem's value depends on being durable and annotatable, so chat-only
output is not a postmortem. Where to write it:

- Repo work with a plan doc: append a `## Postmortem` section to that doc.
- Repo work without one: the session log (`internal/log/`) or a doc the repo's
  conventions point to.
- Outside a repo: propose a location and write there.

If a postmortem for the same scope already exists, annotate it (rule 3) rather
than writing a second one.

## Routing the findings

After writing, sort what should outlive the document:

- Durable lessons about how the user or project works → propose a memory or
  CLAUDE.md addition (propose; do not silently edit CLAUDE.md).
- A mistake that will repeat mechanically → suggest a hook or check (via
  hookify if installed).
- Follow-up work → the repo's task list, roadmap, or session log.

Route only what earned it. Most findings correctly stay in the postmortem.
