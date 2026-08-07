# Postmortem report format

last updated: 2026-08-07

The section-by-section shape of the output file, and where each kind of
finding should be routed afterwards.

**Experience mode uses a different section set** — six sections, in
`references/experience-mode.md`, because its reader maintains the subject
rather than the repo. Everything else in this file still applies to it: the
per-finding shape, "Nothing." as valid output, and the routing table at the
end.

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

## Figures and charts

Only under `--visuals`. A figure attaches to a finding in one of the sections
above; there is no figures section, because a figure that has to be gathered
into one has no finding to sit under. A chart's numbers live in a table in this
document and the chart is a rendering of that table, so the markdown is never
lossy. Full discipline: `references/visual-evidence.md`.

## Output: a file, always

A postmortem's value depends on being durable and annotatable, so chat-only
output is not a postmortem. Every run writes a file.

The file opens with the frontmatter block, then the five sections above.

Where it goes, what it is called, what the frontmatter must carry, and what to
do when a postmortem for the same scope already exists: the plugin-level
`references/filing.md`, shared with the other skills here that write files.
Resolve the location from that ladder; never assume one.

## Routing the findings

After writing, sort what should outlive the document:

- Durable lessons about how the user or project works → propose a memory or
  CLAUDE.md addition (propose; do not silently edit CLAUDE.md).
- A mistake that will repeat mechanically → suggest a hook or check (via
  hookify if installed).
- Follow-up work → the repo's task list, roadmap, or session log.

Route only what earned it. Most findings correctly stay in the postmortem.
