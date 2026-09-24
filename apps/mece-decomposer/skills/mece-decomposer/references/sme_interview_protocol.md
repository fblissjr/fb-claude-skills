# SME interview protocol

last updated: 2026-09-24

The goal: surface the assumptions, exceptions and decision criteria an SME knows but rarely says, and end with a tree the SME has confirmed covers the process without overlap. Interviewing well is assumed competence; this file carries the phase structure the other files refer to, the modes, the confirmation points, and the ways extraction goes wrong.

## Phases

1. **Scope**: what the process is, who is involved, trigger, done-state, exclusions.
2. **Happy path**: the SME narrates end to end; probe each step for actor, duration, inputs, outputs, whether it always happens, and what can run in parallel. Probe only what the narration left unclear.
3. **Exceptions**, per step: what fails, what happens next, skip conditions, branching by input or customer type, worst case. Record each inline under its step (`Exception: condition -> what happens instead`).
4. **Boundaries**: handoffs, parallel activities, upstream dependencies, downstream consumers, time constraints, approval gates.
5. **Validation**: present the tree and iterate.

## Modes

| Mode | When | Phases |
|------|------|--------|
| Full interview (default for "interview me") | SME has a dedicated session, process undocumented | 1-5 |
| Rapid extraction | SME has little time, or a partial description exists | 1 (two questions: what and when done, what is out of scope), 2, 5; record in the output that exceptions and boundaries were not discovered |
| Document-assisted | an SOP, runbook or flowchart exists | pre-fill 1 and 2 from the document, then 3 for what it does not cover only, then 5 |
| Iterative async | SME answers by message, not live | one self-contained batch of 2-3 questions per message, restating the context the SME needs, with the updated tree in each reply |

## Confirmation points

The SME answers every turn, so a one-line recap folded into the next question is enough between these; a separate "does this sound right?" turn after every few answers costs the SME time and adds nothing the next answer would not correct. Stop for explicit confirmation at exactly these points, because each is a boundary later work builds on:

- **End of phase 1**: read back "We are decomposing [process], which begins when [trigger], involves [stakeholders], and ends when [completion criteria]. It does not include [exclusions]." This sentence becomes `metadata.scope`, `trigger`, `completion_criteria` and `exclusions`.
- **L1 structure**, before showing L2: disagreement at L1 invalidates everything beneath it.
- **Completion**: the interview is done when the SME accepts the L1 and L2 structure, at least 3 scenarios have been walked through the tree without finding a gap, no overlap is unresolved, and the SME says it covers the process.

When the SME flags an issue in phase 5: paraphrase it back, classify the fix (relabel, merge, split, new component), apply it, and re-validate the affected level only.

## Gotchas

- **Skipped steps.** Routine steps go unmentioned. Ask what happens between step N and N+1 that is too routine to mention.
- **Jargon.** A label is not an activity; ask what an observer would actually see.
- **The official version.** SMEs describe the documented process. Ask what people actually do and which shortcuts they take.
- **"That never happens."** Push once ("even once a year, what would happen?"); if they hold, accept it and record a low-probability risk.
- **Handoffs** are where processes break and the most common source of cross-branch dependencies. For each: what is passed, how the receiver knows it is their turn, what happens if nobody picks it up.
- **Hesitation is information.** A pause or a vague answer marks an undocumented decision; probe it.
- **"It depends"** is a branch point: ask what it depends on.
- **Structured thinkers** move fast through phase 2 and under-report exceptions they have mentally optimized away; spend the time on phase 3.
- **Narrative thinkers** jump between topics; let them tell stories, organize afterward, and reuse the stories as phase 5 scenarios.
- **Time-constrained or resistant SMEs**: start from a speculative draft tree and let them correct it, phrase questions as confirmations, prioritize L1 and L2, and flag L3+ gaps for follow-up.

## Hand-off to decomposition

The interview yields scope, a happy-path step list with inline exceptions, boundary notes and a confirmed tree. Scope is then settled; continue from dimension scoring in `decomposition_methodology.md`, with `metadata.source_type` set to `sme_interview`.
