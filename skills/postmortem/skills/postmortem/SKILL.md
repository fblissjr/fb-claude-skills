---
name: postmortem
argument-hint: "[scope] [--lens=<name>] [--html] [--visuals] [--out=<dir>]"
arguments:
  - scope
description: "Evidence-grounded postmortem of finished work. Every finding must cite a concrete artifact; empty sections are valid output. Use when the user says 'postmortem', 'run a postmortem', 'retrospective', 'what went well', 'what would you do differently', or wants a look back at a completed plan, task, bugfix, feature, or run of sessions. Evidence can be this session, a git range, a feature, or a plan doc. A lens picks what gets asked and who reads it: the default covers work this repo did, and the experience lens writes feedback to a tool's developers - 'what was confusing about using X', 'feedback for the devs', 'developer experience writeup', 'what do I wish it had'. Repos can add their own lenses. Add --visuals for figures and charts. Do NOT use for auditing a test suite (use test-audit) or for drafting a session log."
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

## Three axes

A run picks one of each, independently. They used to be one word (`mode`),
which made most combinations unreachable.

### 1. Evidence — where to look

Set by the positional argument.

- **This session** (no argument, or "this session"): the current conversation —
  decisions made, errors hit, detours taken, bugs found and fixed, commands that
  failed, assumptions that turned out wrong.
- **The repository record** (an argument naming a feature, git range, plan doc,
  or "the last N sessions"). Gather, in order of value:
  1. The plan doc, if one exists.
  2. `git log` over the range — commits, messages, what was reverted or re-fixed.
  3. Session logs, wherever this repo keeps them.
  4. `CHANGELOG.md` entries in the range.

Do the evidence pass **before** writing any finding. Read the record; do not
reconstruct it from memory of it.

### 2. Lens — what to ask, and who is reading

A lens is one markdown file holding the sections and the guidance under each.
Resolve in order, and **say which rung you landed on**:

1. `--lens=<name>` on the invocation.
2. `"lens"` in the repo's root-level `.postmortem.json`.
3. A repo-local `lenses/` directory beside where postmortems are filed. A repo's
   own lens shadows a built-in of the same name — that is how a repo adapts one
   without forking the plugin.
4. The built-in `project` lens.

A named lens that does not resolve is an error, not a silent fallback: say what
was asked for, list what is available, and stop.

Built-ins are `../../lenses/project.md` (work this repo did — the default) and
`../../lenses/experience.md` (feedback to the developers of a system you used).
`../../lenses/README.md` has the format and how to write one.

**Read the chosen lens before gathering evidence**, not after — it changes what
counts as evidence.

### 3. Rendering

Markdown always. `--html` adds a rendering; `--visuals` adds figures and implies
`--html`. Both are below.

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

`references/report-format.md` holds what a finding looks like and what the file
must be — the rules every lens inherits. The sections themselves come from the
lens. Read both when you start writing, not when deciding whether to run one.

**A postmortem is always a standalone file**, never a section appended to a
plan doc. Where it goes is resolved per repo — an `--out=<dir>` flag, a
root-level `.postmortem.json`, or inference from where that repo already keeps
prose about itself — and with no signal at all you propose a location rather
than creating one. The naming rule `YYYY-MM-DD_<lens>_<slug>.md` and the
required frontmatter (including the `artifacts` list, which must match the
body's citations exactly) are in `../../references/filing.md` — shared with
the other skills in this plugin that write files. Read it before writing.

Markdown is the postmortem and is always written. `--html` additionally renders
a self-contained HTML file beside it with the same stem — a transform of the
markdown just written, never a second analysis. Read
`references/html-render.md` only when that flag is passed, or when `--visuals`
implies it.
