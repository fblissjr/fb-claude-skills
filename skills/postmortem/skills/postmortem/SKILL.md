---
name: postmortem
argument-hint: "[session|span|feature] [scope]"
arguments:
  - mode
  - scope
description: "Evidence-grounded postmortem of finished work — a session, a feature, or a span of sessions. Recovers what went well, what did not, deviations from plan, and test escapes; every finding must cite a concrete artifact, and empty sections are valid output. Use when the user says 'postmortem', 'run a postmortem', 'retrospective', 'what went well', 'what would you do differently', or wants a look back at a completed plan, task, bugfix, feature, or run of sessions. Span mode mines git history, session logs, and changelogs. Do NOT use for auditing a test suite (use test-audit) or for drafting a session log."
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

## Scope: two modes

Chosen by the argument:

- **Session mode** (no argument, or "this session"): the evidence base is the
  current conversation — decisions made, errors hit, detours taken, bugs found
  and fixed, commands that failed, assumptions that turned out wrong.
- **Span mode** (an argument naming a feature, git range, plan doc, or "the
  last N sessions"): the evidence base is the repository record. Gather, in
  order of value:
  1. The plan doc, if one exists (needed for the deviations table).
  2. `git log` over the range — commits, messages, what was reverted or
     re-fixed.
  3. Session logs (`internal/log/log_*.md` or the repo's equivalent).
  4. `CHANGELOG.md` entries in the range.

Do the evidence pass **before** writing any finding. In span mode, read the
record first; do not reconstruct the span from memory of it.

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

## Writing the report

The section-by-section format, the file-naming rule, and the table for routing
each kind of finding afterwards are in `references/report-format.md`. Read it
when you start writing, not when deciding whether to run one.
