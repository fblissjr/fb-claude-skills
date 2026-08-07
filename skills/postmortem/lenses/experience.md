---
lens: experience
audience: The developers of the system you used. They maintain it and have never seen your repository.
use-when: The subject is the tool, framework, API, harness, agent, or skill the work was done *with*, rather than the work itself.
fields:
  version: The exact version or build of the subject as it was used. Answers "does this still apply".
  task: One line on what was being built while using the subject. Answers "does this apply to me".
---
# Experience

The `project` lens asks *what did we build and what did it teach us*. This one
asks *what was it like to build with this thing, and what should its developers
change*.

The audience is the whole reason it is a separate lens: the reader maintains the
subject and has never seen your repository. Everything below follows from that.

## What counts as a subject

Anything with a surface you had to learn and use to get work done: a compiler
or build tool, a framework or library, an API, an internal CLI, a harness, an
agent, a skill, a plugin, a model. If you spent the session *using* it rather
than *changing* it, it is a subject.

If you were changing it, this is not this lens — that is a `project`
postmortem of your own work, and the subject's developers are you.

## The one hard problem this lens has

The `project` lens reads evidence that outlives the run: commits, files, logs.
This lens's evidence is *friction*, and friction is the thing that
vanishes first. By the time the work succeeds, the four wrong turns that
preceded it have been overwritten by the one path that worked, and the
honest-sounding sentence "the docs were a bit unclear" is what is left.

That sentence is not a finding. The no-citation-no-finding rule applies here
exactly as it does everywhere else, and here it bites hardest:

> **"I was confused" is not a finding. The turn where you were confused, what
> you did next, and what it cost is a finding.**

So: **reconstruct from the trace, not from the feeling.** Before writing
anything, walk the actual record of the session — the commands run and their
real output, the files created and later deleted, the edits reverted, the
searches repeated, the point where the approach changed. The wrong turns are
still there. Write from those.

If the trace for a stretch is genuinely gone, say so in that finding rather
than reconstructing it plausibly. An experience postmortem that reads smoothly
because its gaps were filled in is worse than one with holes in it, because a
developer will act on it.

## Citations that work here

In descending strength:

1. **A command and its verbatim output** — especially an error message. The
   exact string is the artifact; paraphrasing an error destroys the only thing
   a developer can grep for.
2. **A wrong turn, with its cost** — what you tried, why it looked right, how
   many attempts or how long before it was corrected.
3. **The guidance sentence you read, quoted, plus what you concluded from it.**
   The gap between those two is the defect, and it is invisible unless both
   halves are on the page.
4. **A file you wrote to work around the system**, by path.
5. **A figure** — the produced output next to the intended output, when the
   finding is about something visible. See `visual-evidence.md` in the postmortem skill's references.
6. **A count** — attempts, retries, failures by class, turns to first success.

## Two rules that decide whether the feedback is usable

### Rank by cost, not by annoyance

A developer triages by what a defect costs. Attach a cost to every finding in
sections 2–5: attempts, wall-clock, dead code written and thrown away, or the
number of turns a wrong mental model survived. A finding with no cost attached
is a preference, and preferences from a single user are noise.

"The flag name is unintuitive" is a preference. "The flag name led me to pass
it three times with the wrong value before I read the source" is a defect with
a size.

### Separate "it is missing" from "I did not find it"

Before filing anything as a missing capability, **check whether it exists.**
Search the subject's docs, its help output, its source if available.

If it exists and you missed it, that is **still a finding** — but it is a
discoverability finding, and the fix is completely different from building the
feature. Filing it as missing sends a developer to build something they already
shipped, which is the single most common way this kind of feedback wastes the
time it was meant to save.

Say which one it is. If you could not check, say that instead of guessing.

## Pin the version

Feedback ages against releases, and a developer's first question is always
whether it still applies. This lens **declares two fields** in its frontmatter
above — `version` and `task` — and every postmortem written through it carries
them. Nothing special-cases them: any lens can declare fields the same way, and
the index renders them by shape. See `README.md` here and the plugin-level
`references/filing.md`.

Where a finding depends on how the subject was invoked, put the invocation in
the finding, verbatim.

## Sections

Six, replacing the `project` lens's five. The core rules still hold: a few
sentences per finding, "Nothing." is valid output, and never invent an item to
fill a frame.

### 1. What worked

An affordance of the subject that demonstrably paid off, cited. This section is
not politeness — it is the only signal a developer has about **what not to
break**, and it is the one they will never get from a bug tracker. "It was
fine" is not a finding; "the error pointed at the exact line and the fix was
right the first time" is.

### 2. What did not

Friction, with cost attached. Group repeats: three instances of the same shape
are one finding stated once with three citations, not three findings — a
developer needs to see that it is a pattern.

### 3. Expectation vs. behaviour

A three-column table: **Expected | Actual | What led me to expect it**.

The third column is the one that makes this section actionable, and it is why
this is a table rather than prose. "I expected X" is a fact about you. "The
parameter is named `timeout` and the doc calls it a limit, so I expected it to
cap total runtime" names the surface that misled — and that surface is the
thing to fix. Point at a specific name, signature, doc sentence, example, or
error string. If nothing led you to expect it and you simply assumed, write
"assumption, nothing in the system suggested it" — that is honest and it is a
real category, distinct from being misled.

### 4. Escapes: guidance and instrumentation

The structural twin of the escapes section in the `project` lens. For every
wrong turn in sections 2 and 3, ask: **which surface should have prevented
this, and why didn't it?** Three verdicts:

- **Absent** — nothing said it. A doc, an error, or a signal needs to exist.
- **Present but not found** — it said it, somewhere you did not look. Say where
  you *did* look; that is where it needed to be. This is a routing defect, and
  it is the verdict most often misfiled as "absent".
- **Present but misleading** — it said it, you read it, and it pointed the
  wrong way. Quote it. This is the most expensive class, because the reader
  stops looking.

"Instrumentation" is whatever the subject emits to tell you what it is doing:
error messages, logs, progress output, warnings, exit codes, type signatures,
telemetry, a dry-run mode. Silence is a finding here — a system that did
something surprising and said nothing while doing it is missing an instrument,
and that belongs in this section rather than being folded into section 2.

### 5. Built outside the system

What you had to make yourself to finish the job. Each row: **what it is, what
it substitutes for, its path, and whether it is a workaround or an
extension.**

That last distinction is the section's whole triage value:

- A **workaround** stands in for something the subject should do. Its existence
  is the bug report, and it should stop existing when the subject is fixed.
- An **extension** is legitimately outside the subject's scope. Naming it as
  such is useful too — it maps the boundary, and it keeps the workaround list
  honest.

This is the highest-signal section in this lens, because each row is a
capability request that already ships with a working reference implementation.
Say roughly what it cost to build, and whether it is now load-bearing.

### 6. Forward items

Checkable, addressed to the subject's developers, and phrased so a future
reader can mark each one done, refuted, or wrong-premise — the same bar as the
`project` lens.

**This is the only section where a wish is allowed, and it must trace.** "What
I wish it had" earns a place here only when a finding in sections 1–5 names the
moment it was wanted. A wish with no such moment behind it is generic advice
under a friendlier name, and the ban on generic advice does not lift because
the audience changed.

Order by cost, highest first. You are handing someone a backlog; put the
expensive thing at the top.

## Routing

The routing table in the `project` lens assumes the findings are
about this repo, and under this lens most of them are not. Adapt it:

- **Findings about the subject** — sections 2 through 6 — are for its
  developers. The file is the deliverable and it is written; **getting it to
  them is a separate, outward-facing act, so propose rather than perform it.**
  Say where it could go (an issue, a discussion, a direct hand-off) and let the
  user choose. Never open an issue on someone else's project unasked.
- **Findings about how we use the subject** — a workaround from section 5 that
  is now load-bearing, or a convention that avoided a whole class of friction —
  route as the standard table says: a CLAUDE.md proposal, a check, a task.

Both kinds usually appear in one run. Sort them before routing, or the useful
half goes to the wrong reader.

## This file is likely to leave the repository

An experience postmortem is written to be sent to someone who does not have
your clone, which makes it the one postmortem most likely to be pasted into an
issue tracker, a chat, or a public thread. Two consequences:

**Write it to be readable cold.** No repo-internal shorthand, no unexplained
plugin names, no "as usual". A developer of the subject knows their system and
nothing about yours.

**Redact before writing, not after.** Absolute paths, usernames, hostnames,
tokens, customer names, and unrelated file trees all leak through quotes of
real command output — the exact material this lens is built on. Repo-relative
paths and placeholder home directories, as everywhere else in this repo.

The pixel case is the dangerous one: **path-privacy's hooks read text and
cannot see inside an image.** A screenshot that captures a terminal title bar,
a sidebar of unrelated filenames, or a full window title carries all of it past
every check this repo has. Crop and redact figures before they are written, and
treat that as part of capturing them rather than a review step afterwards.
`visual-evidence.md` in the postmortem skill's references states the capture discipline.
