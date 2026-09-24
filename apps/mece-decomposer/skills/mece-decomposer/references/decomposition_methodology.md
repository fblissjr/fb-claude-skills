# Decomposition methodology

last updated: 2026-09-24

The goal: a tree whose siblings never overlap and together cover their parent, cut down to atoms that each map to one executable unit, with every judgment recorded in the JSON (`output_schema.md`). The order below is load-bearing only where noted; otherwise plan the path yourself and revisit earlier decisions when a later level exposes them.

## Scope (before any cut)

Record the scope statement, trigger, completion criteria, inclusions and exclusions in `metadata`. Exhaustiveness is only testable against a bounded scope, so this comes first. Boundary test for any candidate item: if removing it leaves the process complete from trigger to completion, it is a candidate for exclusion.

Scope failures to recognise: too broad (no trigger or completion, "run the business"), too narrow (already atomic, "validate email format"), fuzzy (overlaps adjacent processes, "handle customer issues"). When the scope cannot be pinned from what the user gave, switch to the interview protocol (`sme_interview_protocol.md`).

## Dimension scoring

Score each candidate dimension 0-2 on four criteria and take the highest total. Record the winner in `metadata.decomposition_dimension` and the reason, naming the runner-up, in `metadata.dimension_rationale`:

| Criterion | 0 | 2 |
|-----------|---|---|
| Natural fit | forced grouping | obviously the right lens |
| Clean boundaries | significant sibling overlap | crisp splits |
| Balanced depth | one branch deep, others shallow | comparable complexity per branch |
| SDK mappability | hard to orchestrate | maps 1:1 to orchestration patterns |

Candidates: temporal (phases), functional (kinds of work), stakeholder (who does it), state (entity transitions), input-output (data flow). A child branch may use a different dimension from its parent (temporal at L1, functional inside each phase is common).

## Cutting and descending

- L1 has 3 to 7 components; below L1, 2 to 7. Merge candidates that always co-occur; split any that hold distinct sub-activities.
- Before descending, write L1 as a flat list with one sentence each saying what the component covers and what it does not. The "does not" half is what makes the ME test answerable.
- Depth is allowed to be uneven. A depth difference of more than 3 levels between branches usually means the deep branch should have been split at L1.

## Atomicity judgment calls

Primary test: "would one sub-step ever execute without the others in this context?" No means atom. Patterns that look atomic and are not:

- "Validate and process": two responsibilities.
- "Handle all error cases": independent paths; split by error type.
- "Coordinate between X and Y": orchestration, not execution; make it a branch with X and Y as children.

## Cross-branch dependencies

Look for four kinds per atom: data (needs another branch's output), sequencing (must wait for it), resource (contends for the same resource), approval (needs sign-off from it). A data dependency between parallel branches forces a sequencing constraint; a resource dependency needs a mutex or semaphore; an approval dependency adds a human gate. Many dependencies relative to the tree size suggest the L1 cut is wrong.

## When validation fails

- ME failure (overlap): redefine the sibling boundaries, or merge and re-cut along another dimension.
- CE failure (gap): add the missing component or broaden a sibling.
- Structural failure (too deep, too wide): re-cut at a higher level.

Scores, limits and the issue vocabulary: `validation_heuristics.md` and `scripts/validate_mece.py`. Mapping atoms and branches to code: `agent_sdk_mapping.md`.
