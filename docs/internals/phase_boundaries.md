last updated: 2026-08-13

# Phase boundaries: continue, clear, hand off, delegate, or compact

A **phase** is a chunk of work inside a session: the design, the
implementation, the QA. The definition is deliberately fuzzy — a phase ends when
you think "right, that's that done".

The **boundary** between two phases is the only place this decision belongs.
Mid-phase there is nothing to decide: continue, or split off what remains into a
subagent. Compacting mid-phase loses the thread.

Adopted 2026-08-13 from `ask-matt/PHASE-BOUNDARIES.md` in
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT), because this
repo had session logs, a `finish-session` skill, and an `advisor` that spawns a
bounded subagent, and no written policy on which of those to reach for when.

## The five options

| Option | What it does |
|---|---|
| **Continue** | Stay in the session. No context switch at all |
| **`/clear`** | Empty the window and start from nothing |
| **Hand off** | Write a portable markdown file and seed a session anywhere from it |
| **Subagent** | Send the task to its own window and get a report back |
| **`/compact`** | Replace this session's history with a summary, in place, and continue |

## The tree

Work top to bottom at the boundary. First yes wins.

**1. Can you continue in this session?** Two things make the answer yes: the
next phase needs this one as a **primary source**, or there is enough headroom
left for the next phase to fit. Design into implementation is the standard yes —
the implementation wants the reasoning verbatim, not a summary of it. Continue
costs nothing and loses nothing, so rule it out before anything else.

**2. Is the context irrelevant to what comes next?** If the exploration, the
decisions, and the dead ends are all disposable, **`/clear`**. It is the
cheapest move available: no time, and the whole window back. It is also not
terminal, since the old session stays resumable.

Getting this one wrong is one-way. Clear a *relevant* context and you lose the
**why** behind what you built, and re-reading the diff does not give it back.

**3. Do you need to hand off?** Narrow. You need it only when something is
travelling: a **new harness**, a **new directory or repo**, a **colleague**, or
a side task found mid-phase that you want to fork without derailing what you are
doing. That list is the whole clause. What a hand-off buys is portability, so if
nothing is travelling you do not need one.

**4. Can the task run unattended?** Scoped tightly enough to go without
steering? Send it to a **subagent** and leave this session untouched. Automated
review is the standard case: the agent reads the diff and reports, and you are
not needed while it does.

**5. Otherwise, `/compact`.** Relevant context, same harness, same directory,
and you need to stay in the loop. This is where the tree lands, and it lands
here often. Pass it an instruction so the summary keeps what the next phase
needs.

`/compact` is the **default, not the first reach**. It sits at the bottom
because the four questions above it are each cheaper or more precise. The
failure mode of starting here is a continuation that is confidently wrong about
a decision the summary flattened.

## Primary and secondary sources

Every move except Continue turns a **primary source** into a **secondary** one:
the session as it happened, replaced by a summary of it.

| Source | Information | Noise | Room to move |
|---|---|---|---|
| Primary (Continue) | Full | Lots | Little |
| Secondary (compact, hand-off) | Lossy | Less | Lots |

That is why question 1 comes first. You only pay the lossiness when staying
costs more than it saves.

## These are judgement calls

The questions are not objective. Each has taste in it, and the same boundary can
go two ways on two days. The value is in asking them **in order**, at the
boundary rather than in the middle of the work.

## Adaptations

- The original cites a context-window figure for how much headroom counts as
  "enough" for question 1. That number is model-dependent and moves; re-derive
  it from `/context` in the session rather than carrying a constant. The
  principle survives the number.
- The original links a published vocabulary site for several terms. Dropped —
  the terms carry themselves here.
- The original describes `/compact` as compressing the context and seeding a
  fresh session with the summary. In this harness `/compact` replaces the
  history in place and the same session continues; corrected above. Adopting a
  doc means checking its behavioural claims against this harness, not only its
  links and numbers.
