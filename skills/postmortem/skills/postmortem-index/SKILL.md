---
name: postmortem-index
argument-hint: "[--out=<dir>]"
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

Use the same resolution ladder as filing —
`../postmortem/references/filing.md` — with one difference: **rung 4 does not
apply.** Do not propose a location and do not create a directory. There is
nothing to browse in a repo that has never written a postmortem; say so and
stop. Report which rung located the directory.

An empty resolved directory is valid output. Build the page, show the count as
zero, and say where it looked.

## Reading the files

Frontmatter only. Never parse the body — `../postmortem/references/report-format.md`
is a house style, not a parse contract, and an index that depends on prose
shape breaks the first time someone writes a section differently.

Per file, read `mode`, `scope`, `date`, `summary`, `range`, `artifacts`, and
`supersedes`.

**Files with missing or unparseable frontmatter still appear.** Postmortems
written before this field set existed have none, and silently dropping them is
what makes an index untrustworthy — a reader cannot tell "nothing was written"
from "the tool did not understand it". The filename carries `date`, `mode` and
`scope` on its own, which is the portable part of the naming rule; recover those,
leave the rest blank, and mark the entry as partially indexed.

## The page

`references/index-page.md` has the template, styling, and the filter script.
Two views of the same data, on one page:

1. **Chronological**, newest first. Each entry: date, mode, scope, the `summary`
   sentence, and its artifacts. A postmortem named by another's `supersedes` is
   shown dimmed and labelled — a stale conclusion a reader can see is stale is
   useful, and one that has been hidden is a trap.
2. **By artifact**, alphabetical. Each artifact lists the dates that examined it.
   This is the view `artifacts` was designed to serve.

Write it to `index.html` in the resolved directory unless `--out=<dir>` says
otherwise. Report the path and the file count.
