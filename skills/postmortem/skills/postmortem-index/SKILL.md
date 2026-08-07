---
name: postmortem-index
argument-hint: "[--from=<dir>] [--out=<dir>]"
description: "Build a browsable HTML index of every postmortem in a repo — date, mode, scope, one-line conclusion, and the artifacts each one examined, plus a by-artifact view answering 'has anything been written about this file'. Reads frontmatter only; superseded postmortems are shown and marked, never hidden. Use when the user says 'browse postmortems', 'postmortem index', 'show me past postmortems', 'what have we written about X', 'list our retrospectives', or wants to find an earlier postmortem without knowing its filename. Do NOT use to run a postmortem (use postmortem) or to audit tests (use test-audit)."
metadata:
  last_verified: "2026-07-26"
  review_interval_days: "365"
---
# Postmortem index

A generated, browsable view of a repository's postmortems. It answers the two
questions people actually arrive with: *what have we concluded lately*, and
*has anything been written about this file*.

## This is a view, not a record

The directory is the index. This page is a lens over it, rebuilt from the files
every time it is asked for, and deleting it loses nothing. That is the line it
must not cross: a listing that gets committed and trusted becomes a copy that
drifts out of agreement with the directory, which is exactly why this plugin has
no checked-in index file.

So: **never hand-edit the generated page**, and if the postmortem directory is
tracked by git, offer to add the generated file to `.gitignore`. A generated
artifact that cannot be committed cannot be mistaken for truth.

## Finding the postmortems

Use the same resolution ladder as filing — the plugin-level
`../../references/filing.md` — with two differences.

**Rung 4 does not apply.** Do not propose a location and do not create a
directory. There is nothing to browse in a repo that has never written a
postmortem; say so and stop. Report which rung located the directory.

**Rung 1 is `--from=<dir>`, not `--out=<dir>`.** This skill reads one directory
and writes to another, so the two need separate names: `--from` overrides where
postmortems are *read*, `--out` where the generated page is *written*. Filing's
`--out` means "where the deliverable goes" and it keeps that meaning here — the
deliverable is the page. A bare `--out` never changes what gets indexed.

An empty resolved directory is valid output. Build the page, show the count as
zero, and say where it looked.

## Reading the files

Frontmatter only. Never parse the body — `../postmortem/references/report-format.md`
is a house style, not a parse contract, and an index that depends on prose
shape breaks the first time someone writes a section differently.

**The field set is defined in the plugin-level `../../references/filing.md`, and
that table is the only enumeration of it.** Read every field it lists; do not
keep a second list here. This skill previously carried its own copy, and the two
drifted the first time a field was added — a field written into filing's table
and never displayed is invisible in exactly the view that exists to surface it.

Two display rules the field table does not carry, because they are this page's
business rather than the record's:

- Render `version` beside the mode badge. Feedback on a tool ages against that
  tool's releases, so a reader scanning several experience postmortems about one
  subject is deciding what is still live, and that is the field that answers it.
- Treat any frontmatter key not in the table as data this page does not display,
  rather than as an error.

## Linking to the record

Each entry links to the postmortem's **markdown** file, which is the addressable
artifact. But this page is opened in a browser, and a markdown link there is a
download or a wall of raw text.

So: **when a rendering shares the entry's stem, link that instead, and link the
markdown beside it as a secondary link.** Check for the sibling rather than
assuming one; most postmortems have none. A rendering is derived and may be
absent or deleted at any time, so an entry whose sibling is missing simply falls
back to the markdown — never omit the entry, and never link a rendering you did
not confirm exists.

**Files with missing or unparseable frontmatter still appear.** Postmortems
written before this field set existed have none, and silently dropping them is
what makes an index untrustworthy — a reader cannot tell "nothing was written"
from "the tool did not understand it". The filename carries `date`, `mode` and
`scope` on its own, which is the portable part of the naming rule; recover those,
leave the rest blank, and mark the entry as partially indexed.

**Artifact entries that do not resolve in the tree are marked, not dropped.**
Check each path-shaped entry against the working tree; entries naming a commit or
a command are not paths and are not checked. An unresolved path is not
necessarily wrong — a postmortem is historical, and a file examined a year ago
may have been renamed since — so the mark reads *not in the tree today*, which
makes it a staleness signal rather than an error. Dropping them instead would
reintroduce the failure the previous paragraph names, one level down: a
by-artifact view that silently lists fewer artifacts than were examined.

## The page

`references/index-page.md` has the template, styling, and the filter script.
Two views of the same data, on one page:

1. **Chronological**, newest first. Each entry: date, mode, scope, the `summary`
   sentence, and its artifacts. A postmortem named by another's `supersedes` is
   shown dimmed and labelled — a stale conclusion a reader can see is stale is
   useful, and one that has been hidden is a trap.
2. **By artifact**, alphabetical. Each artifact lists the dates that examined it.
   This is the view `artifacts` was designed to serve. Artifacts marked as not in
   the tree today appear here too, carrying the mark — this view is where the
   distinction between a renamed file and a mistyped one actually costs a reader
   something.

Write it to `index.html` in the resolved directory unless `--out=<dir>` says
otherwise. Report the path and the file count.
