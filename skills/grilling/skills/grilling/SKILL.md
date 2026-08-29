---
name: grilling
description: >-
  Interview the user until a plan, design, or decision is fully specified, by
  working a design tree in rounds rather than asking questions as they occur.
  Each round asks every question whose prerequisites are already settled, with a
  recommended answer attached, and the session ends when nothing is left
  unasked. Use when the user says "grill me", "stress-test this", "poke holes in
  this", "interview me", "what am I not thinking about", or when a plan is about
  to be built and its unknowns have not been enumerated. Finding facts is the
  agent's job; only decisions go to the user. Do NOT use to review work already
  done (use a postmortem or code review) or to answer a question the codebase
  can settle on its own.
---

# Grilling

Interview relentlessly until you and the user share an understanding of the
thing. Not a conversation that wanders toward clarity: a tree, worked
systematically.

## The tree and the frontier

Map the problem as a **design tree**. Every decision branches into the decisions
that hang off it.

The **frontier** is every decision whose prerequisites are already settled —
the questions answerable *now*, without guessing at answers you have not heard
yet. That word is doing the work: it is what separates this from asking
questions in the order they occur to you.

A question whose answer depends on another question still open belongs to a
**later round**, not this one. Asking it now produces an answer the user will
revise, and revised answers quietly invalidate everything built on them.

## Rounds

Ask the whole frontier in one round. Then wait.

Each answer reshapes the tree: settled decisions push the frontier outward and
unblock questions that depended on them. Recompute the frontier and ask the next
round.

**Every question carries your recommended answer.** A bare question makes the
user do the thinking twice. A recommendation they can accept, reject, or amend
costs them one judgment instead.

Two formats, by size:

- **Two to four questions with enumerable choices** — use `AskUserQuestion`, one
  question per decision, recommended option first and labelled as such.
- **A larger frontier, or open-ended answers** — numbered plain text, one block
  per question:

```text
Q1 — <question title>
<the question, including the options if there are any>
Recommended: <your answer, and the one-line reason>
```

No emoji in either form.

## Facts are yours, decisions are theirs

**Never ask the user something the environment can answer.** File contents,
which version is installed, what the config already says, whether a thing
already exists: go and look. A question the codebase settles is a question that
wastes the user's turn and signals you did not check.

When a frontier question needs a fact you do not have, dispatch the lookup and
**keep going**. A running exploration is an unsettled prerequisite, so only the
questions downstream of it wait. Ask the rest of the frontier now rather than
blocking the round on one lookup.

Delegate the lookup rather than doing it inline where the search is broad or the
output is large — the point is to keep the interview in the main thread and the
file-reading out of it.

The **decisions** are the user's. Put each one to them and wait. Do not decide
by inference from a previous answer, and do not treat silence as assent.

## Done

The session is done when the frontier is empty: every branch visited, nothing
left silently assumed.

Do not act on the design until the user confirms you have reached a shared
understanding. Reaching the end of the questions is not the same as agreement.

## Where this fits

A primitive. Other skills invoke it rather than reimplementing an interview:
anything that designs before building wants this loop, and a skill that carries
its own ad-hoc question list will drift from it.

Two wrappers are worth knowing even though this repo ships neither: a stateless
one that just runs the interview, and a stateful one that also writes what it
learns into a project glossary and decision records. The stateful variant is the
better default wherever there is a repo to leave a trail in.
