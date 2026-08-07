# Lenses

last updated: 2026-08-07

A lens is **what to ask, and who is reading the answers**. It is one markdown
file. The built-in lenses in this directory and one your repo writes are the
same kind of thing, read the same way — there is no separate mechanism for
"custom".

## The three axes

A postmortem run picks one of each, independently:

| Axis | What it decides | Set by |
|---|---|---|
| **Evidence** | where to look — this session, a git range, a feature, a suite | the positional argument |
| **Lens** | what to ask and who is reading | `--lens=<name>`, repo default, or inference |
| **Rendering** | markdown, plus HTML, plus figures | `--html`, `--visuals` |

These were one word (`mode`) until 2026-08-07, which made most combinations
unreachable: three of the five old modes asked identical questions and differed
only in where they looked, so asking the feedback-for-developers questions
across a span of sessions was impossible — not because it is a bad idea, but
because nobody had minted a token for it.

## What a lens may and may not do

**A lens says what to ask. The core says what counts as an answer.**

That line is the whole design. A lens cannot weaken these, because it has no
authority over them — it describes sections, nothing more:

- **No citation, no finding.** Every claim names a concrete artifact.
- **Empty sections are valid output.** "Nothing." is a result, never padded.
- **Annotate, do not rewrite.** Corrections append, dated.
- **A file, always.** Chat-only output is not a postmortem.
- **`artifacts` is a projection of the body's citations**, checkable both ways.
- **Measurement is distinguished from inference.**

So the worst a bad lens can do is ask boring questions. It cannot produce an
ungrounded document, and it cannot quietly turn the discipline off.

## Writing one

Frontmatter, then a section per question you want asked:

```markdown
---
lens: incident
audience: The on-call rotation and whoever owns the affected service.
use-when: A production incident is resolved and the timeline is still recoverable.
---
# Incident review

One paragraph on what this lens is for and what makes it different.

## Sections

### 1. Timeline
What to put here, and what does not belong. Be specific about what counts as
evidence for this kind of work.

### 2. Detection
For every symptom, name the alert that should have fired and why it did not:
absent, fired-but-ignored, or fired-too-late.
```

Three things make a lens good, and all three are about the prose under each
heading rather than the headings themselves:

1. **Say what does *not* belong in a section.** "The tests passed" is not a
   finding; that sentence does more work than the section title.
2. **Give the discriminating question.** The strongest built-in sections ask one
   sharp question with named outcomes — *which test should have caught this,
   missing or green-but-blind?* A heading alone leaves the reader to invent one.
3. **Name the audience in the frontmatter and mean it.** It changes what needs
   explaining, what jargon is allowed, and whether the file is safe to send
   outside the repo.

A three-column table is a good shape when two things need comparing and the
third column names the cause — both built-in lenses use one. Say the column
headers explicitly; do not leave the shape to be guessed.

## Resolution

Stop at the first hit, and **say which one you landed on** when reporting:

1. `--lens=<name>` on the invocation.
2. `"lens"` in the repo's root-level `.postmortem.json`.
3. A repo-local lens directory — `lenses/` beside wherever postmortems are
   filed. A repo's own lenses shadow a built-in of the same name, deliberately:
   that is how a repo adapts `project` without forking the plugin.
4. The built-in `project` lens.

A named lens that does not resolve is an error, not a silent fallback. Say what
was asked for, list what is available, and stop — quietly writing the wrong kind
of postmortem is worse than writing none.

## The built-ins

| Lens | Reader | For |
|---|---|---|
| `project` | your future self, the next model | Work this repo did: what shipped, what it cost, what it taught. The default. |
| `experience` | the developers of a system you used | What it was like to build with something. Sections are about friction, not features. |

Two is not a taxonomy. Add lenses when a kind of work keeps not fitting, not in
anticipation of one that might.
