---
name: postmortem
argument-hint: "[session|span|feature|experience] [scope] [--html] [--visuals] [--out=<dir>]"
arguments:
  - mode
  - scope
description: "Evidence-grounded postmortem of finished work — a session, a feature, a span of sessions, or the experience of building with a system. Every finding must cite a concrete artifact; empty sections are valid output. Use when the user says 'postmortem', 'run a postmortem', 'retrospective', 'what went well', 'what would you do differently', or wants a look back at a completed plan, task, bugfix, feature, or run of sessions. Experience mode writes feedback to a tool's developers — 'what was confusing about using X', 'feedback for the devs', 'developer experience writeup', 'what did I have to build around it', 'what do I wish it had'. Span mode mines git history, session logs, and changelogs. Add --visuals for figures and charts when findings are about something visible or counted. Do NOT use for auditing a test suite (use test-audit) or for drafting a session log."
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

## Scope: three modes

Chosen by the argument. The first two ask *what did we build and what did it
teach us*; the third asks *what was it like to build with this thing*.

- **Session mode** (no argument, or "this session"): the evidence base is the
  current conversation — decisions made, errors hit, detours taken, bugs found
  and fixed, commands that failed, assumptions that turned out wrong.
- **Span mode** (an argument naming a feature, git range, plan doc, or "the
  last N sessions"): the evidence base is the repository record. A span scoped
  to a named feature rather than a date range files as mode `feature`; the
  method is identical. Gather, in order of value:
  1. The plan doc, if one exists (needed for the deviations table).
  2. `git log` over the range — commits, messages, what was reverted or
     re-fixed.
  3. Session logs, wherever this repo keeps them.
  4. `CHANGELOG.md` entries in the range.
- **Experience mode** (the user asks for feedback on a system rather than on
  the work — "what was confusing about using X", "write this up for the devs",
  "what do I wish it had"): the subject is the tool, framework, API, harness,
  or skill the work was done *with*, and the reader is someone who maintains it
  and has never seen this repository. Its evidence is friction, which is the
  first thing a successful session overwrites, so it is reconstructed from the
  session trace rather than from memory of it. Six sections instead of five, an
  extra pair of frontmatter fields, and rules about redaction that the other
  modes do not need: `references/experience-mode.md`. Read it before gathering
  evidence, not after.

Do the evidence pass **before** writing any finding. In span and experience
mode, read the record first; do not reconstruct it from memory.

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

## Visual evidence

Some findings are about something visible — output that rendered wrong, a
layout that broke, a frame that was off — and some are about something counted.
For those, prose is a lossy citation, and `--visuals` adds figures and charts.
It implies `--html`, because a figure set whose only rendering is relative
image links is half a deliverable.

Two rules bound the figure set from both sides: **no finding, no figure** — a
figure with no finding is the visual form of the generic advice this skill bans
— and **no chart without its numbers**, so the numbers live in a table in the
markdown and the chart is a rendering of that table, exactly as the HTML is a
rendering of the markdown. Charts therefore produce no files; captured media
goes in a sidecar directory with the same stem.

Capture discipline, the countable measures, chart form, redaction, and size:
`references/visual-evidence.md`. Read it only when the flag is passed.

Without the flag, no media is captured and no directory is created. If a run's
findings clearly want figures and the flag was not passed, say so once and
offer — do not capture unasked, and do not silently create the directory.

## Writing the report

The section-by-section format and the table for routing each kind of finding
afterwards are in `references/report-format.md`. Read it when you start
writing, not when deciding whether to run one. Experience mode replaces its
five sections with the six in `references/experience-mode.md`; everything else
in it still applies.

**A postmortem is always a standalone file**, never a section appended to a
plan doc. Where it goes is resolved per repo — an `--out=<dir>` flag, a
root-level `.postmortem.json`, or inference from where that repo already keeps
prose about itself — and with no signal at all you propose a location rather
than creating one. The naming rule `YYYY-MM-DD_<mode>_<slug>.md` and the
required frontmatter (including the `artifacts` list, which must match the
body's citations exactly) are in `references/filing.md`. Read it before
writing the file.

Markdown is the postmortem and is always written. `--html` additionally renders
a self-contained HTML file beside it with the same stem — a transform of the
markdown just written, never a second analysis. Read
`references/html-render.md` only when that flag is passed, or when `--visuals`
implies it.
