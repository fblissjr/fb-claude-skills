---
name: doc-architecture
description: >-
  Establish where a project's writing lives: a stable home for principles that a
  fast-moving rules file cannot hold, and a CLAUDE.md shaped as a routing index
  rather than an accumulating pile of rules. Creates the slot and the criteria for
  what earns a line in it; never writes principles for you. Use when starting a new
  project, when asked to set up docs or a VISION or principles file, when CLAUDE.md
  has grown into the largest always-loaded cost in the repo, or when nobody can say
  which document a claim belongs in. Triggers on "set up the docs", "new project
  setup", "where should this go", "CLAUDE.md is too big", "we need a vision doc".
metadata:
  last_verified: "2026-08-17"
  review_interval_days: "365"
---

# Document architecture

Two things every project needs and most lack: a slow-clock home for principles,
and a `CLAUDE.md` that routes rather than accumulates.

**This skill ships no principles.** A pre-written set of beliefs is exactly the
broadcast that a conventions mechanism should not perform — the reader's own
principles are the point, and one hour writing them beats any inherited file.
What ships is the slot, the criteria for what earns a line in it, and the shape
of the index.

## Before creating anything, look

A principles home may already exist under another name. Check, in order, and
stop at the first hit — report which one matched:

1. `VISION.md`, `PRINCIPLES.md`, `PHILOSOPHY.md`, `DESIGN.md` at the root.
2. `docs/vision.md`, `docs/principles.md`, `docs/design-principles.md`.
3. A section inside `CLAUDE.md` or `README.md` that is already doing this job —
   stating why the project is shaped the way it is, rather than what to do.

If one exists, **say so and stop**. Do not create a second. If the third case
matched, the useful move is offering to lift that section into its own file,
which is a proposal, not an edit.

**Never overwrite an existing file, and never recreate one that was deleted.**
A missing `VISION.md` in a repo that once had one is a decision, not an
oversight — the same reason `model-routing` pauses its own install rather than
silently undoing a deliberate removal.

## What earns a line in the principles file

The test is **what would reopen this claim**, not what topic it belongs to.

| Class | Reopened by | Home |
|---|---|---|
| Principle | evidence contradicting it | the principles file |
| Rule or gate | its source moving | the fast-clock rules file |
| Design record | the decision's premises changing | a dated document |
| Incident | nothing — it is what happened | a dated record, never edited |

A principle is a claim about *why the project is shaped this way* that survives
its own implementation being replaced. If a sentence would need editing when a
library version changes, it is a rule and belongs elsewhere. If it would need
editing when someone disagrees with it, it is a principle and belongs here.

**State a tie-breaker.** Where two homes could hold the same claim, write down
which one wins — one sentence, in the principles file. Without it, two documents
drift and nobody can tell which is authoritative. This is the part most often
skipped and it is the part that makes the split hold.

## The starter file

Create `VISION.md` at the root containing the criteria above and nothing else —
no borrowed principles, and headings the owner fills. It should read as
obviously incomplete, because a template that looks finished never gets edited.

## CLAUDE.md as a routing index

**Propose this; do not rewrite an existing `CLAUDE.md`.** It is always-loaded
and frequently load-bearing, so an unrequested edit is expensive in a way the
principles file is not.

The shape: `CLAUDE.md` holds what bites on the first edit — invariants a
newcomer would violate without knowing — plus a table routing everything else
to where it actually lives. It is an index with a short preamble, not the place
rules accumulate.

The failure it prevents: `CLAUDE.md` is the one file loaded in full, every
session, forever. Every rule parked there is paid unconditionally whether or not
the session touches that subject. A rule that applies to Python work belongs in
a Python-triggered surface; a rule that applies once a year belongs in a
document the index points at.

Suggest moving out anything that (a) applies only to one language or subsystem,
(b) restates behaviour the model already exhibits, or (c) is reference material
rather than a constraint.

## What this skill does not touch

`.claude/rules/` is namespaced territory — `advisor` and `model-routing` each
own a file there, and a document-architecture pass has no business editing them.
Git hooks belong to `path-privacy` and `skill-maintainer`. Where postmortems are
filed is resolved by `postmortem`'s own ladder and recorded in `.postmortem.json`.

Removal is deletion: nothing here installs machinery, so deleting `VISION.md`
undoes it completely.
