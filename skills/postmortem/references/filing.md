# Filing

last updated: 2026-08-07

Where a filed artifact goes, what it is called, and what its frontmatter must
carry so that someone — more often, some model — can find it months later
without reading everything.

A postmortem filed inside a plan doc is findable only by a reader who already
knows which plan doc to open. That is the failure this exists to prevent.

## Shared across this plugin

This file lives at the plugin root, not inside a skill, because more than one
skill depends on it: `postmortem` writes here, `test-audit` writes here, and
`postmortem-index` reads the same ladder to find what to index. **Editing this
file changes all three.**

That is the whole reason for the location. There is no import mechanism in a
plugin made of prose — a file is shared only because several skills name its
path — so the path is the only signal a future editor gets about who depends on
it. A field added to the table below without checking `postmortem-index` is
invisible in exactly the view that exists to surface it; that has already
happened once.

## Resolving the directory

Never hardcode a location and never silently create a directory in a layout the
repo did not choose. `internal/` is one repo's convention, `docs/notes/` is
another's, and whether postmortems are local scratch or a tracked shared record
is the repo owner's call — it changes the answer completely.

Resolve in this order, stopping at the first hit. **Say which rung you landed
on** in the message that reports the written file.

1. **Explicit on the invocation.** An `--out=<dir>` flag, or the user naming a
   location in the request. Highest precedence, never persisted — a one-off
   override is one-off.

2. **Per-repo config.** A root-level `.postmortem.json` with:

   ```json
   { "dir": "internal/postmortems" }
   ```

   Path is repo-relative. Omitted keys mean "default", so the file only ever
   states exceptions. This is the plugin's own config file, deliberately not a
   shared one — see "Per-repo plugin config" in this repo's
   `docs/internals/plugin-patterns.md` for why.

3. **Inferred from where the repo already keeps prose about itself.** The repo
   has answered "where does writing about this project live"; read its answer
   rather than imposing one. In descending confidence:

   - A session-log directory (`internal/log/`, `notes/sessions/`, anything
     holding dated `log_*.md`-shaped files) → a `postmortems/` sibling under the
     same parent.
   - An existing `postmortems/` or `retros/` directory anywhere → use it as-is.
   - A working-notes or internals tree (`docs/internals/`, `notes/`, `docs/adr/`)
     → a `postmortems/` sibling under the same parent.
   - A bare `docs/` tree with prose in it → `docs/postmortems/`.

   Inference picks the *parent*; the leaf is always `postmortems/`. Match the
   parent's tracked-ness: if the sibling directory is gitignored, the postmortem
   is local scratch, and that is a deliberate answer rather than an oversight.

4. **Propose, then remember.** With no signal, do not guess and do not write.
   Propose a location and say **whether it would be tracked or gitignored** in
   this repo as it stands — rung 3 reads that answer off a sibling directory,
   but at rung 4 there is no sibling and "these are committed and shared" versus
   "these are local scratch" is the actual decision being made. Get agreement,
   then write the agreed path to `.postmortem.json` so the question is asked
   exactly once. If the user declines to create the config, honour that and ask
   again next time — a declined config is not a bug.

Rung 4 is the only rung that blocks. Rungs 1–3 write without asking.

## Naming

```
<resolved-dir>/YYYY-MM-DD_<mode>_<slug>.md
```

- **Date first** so lexical sort is chronological sort. Recency is the most
  common filter, and it is the same reason session logs are `log_YYYY-MM-DD.md`.
  For a span, the date is the **start of the range**, not the day someone got
  round to writing it: `2026-07-01_span_lint-tooling.md`. The write date goes in
  frontmatter.
- **Mode** is one of `session`, `span`, `feature`, `experience`, `audit`.
  `feature` is a span scoped to a named feature rather than a date range; when a
  run could be called either, the deciding question is what a reader would
  search for — a feature name or a period of time. `experience` is feedback on
  the system the work was done *with* rather than on the work. `audit` is
  `test-audit`'s output, where the slug names the suite audited.
- **Slug** derived from the scope, not the date: `ruff-diagnostics`,
  `pyright-baseline`, `q3-migration`. Lowercase, hyphenated. This is the part a
  grep will match, so prefer the name the artifacts already use over a
  descriptive phrase. In experience mode the slug is the **subject's** name, not
  the task's — a reader looking for it is looking for everything written about
  that tool, and several runs against one subject then sort together.

The naming is the portable part and holds in any repo. Only the directory is
negotiable.

## The media directory

A run with `--visuals` writes captured media — screenshots, frames, recordings
— to a sidecar directory with the same stem, so filing resolves once:

```
<resolved-dir>/2026-08-07_experience_mitate.md
<resolved-dir>/2026-08-07_experience_mitate.html
<resolved-dir>/2026-08-07_experience_mitate/fig-01-....png
```

Charts write nothing here: their numbers live in a table in the markdown and
the chart is a rendering of that table. `references/visual-evidence.md` has the
rest. Report the directory path alongside the file paths.

## Frontmatter

Every postmortem carries this block. It exists so a model can triage a file
without reading it.

```yaml
---
mode: span
scope: lint-and-type-tooling
date: 2026-07-26
range: 2026-07-01..2026-07-26
summary: Ruff and Pyright diagnostics did not overlap; the LSP registration collision was the real constraint.
artifacts:
  - CHANGELOG.md
  - skills/ruff-diagnostics/
  - docs/internals/context-cost.md
supersedes: 2026-06-14_feature_ruff-trial.md
---
```

An experience-mode block, which swaps `range` for `version` and `task`:

```yaml
---
mode: experience
scope: mitate
date: 2026-08-07
version: 0.4.2
task: A 12-second title-card animation with two timed text reveals.
summary: Timing is expressed in two units that read as one, and every wrong turn in the run traced to that.
artifacts:
  - scenes/title-card.toml
  - scripts/frame-diff.py
  - "mitate build --preview"
---
```

**This table is the only enumeration of the field set.** `postmortem-index`
reads it rather than keeping its own list; do not add a second one anywhere.

| Field | Required | Notes |
|---|---|---|
| `mode` | yes | Matches the filename token. |
| `scope` | yes | Matches the filename slug. |
| `date` | yes | When it was written. For a span this differs from the filename date; that is the point. |
| `summary` | yes | One sentence: what this postmortem *concluded*, not what it examined. See below. |
| `range` | span only | Exact git range or date range examined. |
| `version` | experience only | The exact version or build of the subject **as it was used**. |
| `task` | experience only | One line: what was being built while using the subject. |
| `artifacts` | yes | Repo-relative paths, commits, or command names. May be empty only if the body has no findings. |
| `supersedes` | no | Bare filename of an earlier postmortem this one revisits. |

### `version` and `task` (experience mode)

Both exist because the reader is someone who maintains the subject and has
never seen this repo, and both answer a question that reader asks before
anything else.

`version` answers *does this still apply* — feedback ages against releases, and
without it a developer cannot tell a fixed bug from a live one. Record what was
actually running, not what the manifest pins; if the two can differ, say how it
was resolved.

`task` answers *does this apply to me* — the same friction is a blocker in one
usage and irrelevant in another. It is not recoverable from `summary`, which
carries the conclusion rather than the setting.

Neither belongs in the other modes, where the repo *is* the subject and both
answers are already in the git history.

### `summary`

One sentence, and it must carry a **finding**, not a topic. "Looked at the lint
tooling" is a subject line; "Ruff and Pyright diagnostics did not overlap, so the
LSP registration collision was the real constraint" is a summary. A reader
scanning a directory decides what to open from this field alone, so a summary
that only restates the slug wastes the slot the slug already fills.

A postmortem whose sections are all "Nothing." says so here too. That is a
finding — the work was clean — and it saves the next reader opening the file.

**This is the one field an annotation may change.** Annotate-don't-rewrite
protects findings, because a silently edited conclusion is worse than a wrong
one left standing. It does not protect metadata. If a later annotation
contradicts the summary, update the summary and leave the annotated finding
intact; a stale summary sends readers to the wrong file, which is the failure
the field exists to prevent.

**`artifacts` is a projection of the citations, not free metadata.** Every entry
must appear as a citation somewhere in the body, and every artifact cited in the
body must appear in the list. That is what makes "has anything been written
about this file" a one-line grep, and it is checkable: if the two sets disagree,
one of them is wrong. It also keeps the frontmatter honest under the no-citation-
no-finding rule — a findings-bearing postmortem with an empty `artifacts` list
is a contradiction, not a formatting slip.

**Resolve each path against the tree while assembling the list; do not write it
from memory.** The list is built at the end of the work, which is the distance at
which recall is least reliable, and a path one directory off reads as correct to
any review that reads rather than resolves. It then fails twice downstream: the
by-artifact view gains a row for a file nobody examined, and the file that *was*
examined shows nothing written about it. An entry that will not resolve is either
wrong or it names something that is not a path — a commit, a command — and the
field allows both, so decide which rather than leaving it ambiguous.

**Figures are not `artifacts` entries.** The list records what was *examined*;
a figure is evidence this run *produced*. What the figure depicts — the scene
file, the command, the page — is the artifact, and that is what goes in the
list. The media directory is discoverable from the stem and needs no field of
its own.

Paths are repo-relative. An absolute path in a postmortem leaks the machine it
was written on. In experience mode this matters more than anywhere else,
because the file is written to be sent to someone outside the repo — and a
figure can carry an absolute path in pixels that no check here can read. See
`references/visual-evidence.md`.

`supersedes` is a single value. A long-running scope forms a chain by following
the pointers; a stored chain would be a copy whose only consumer is the check
that it matches the pointers.

## Existing postmortem for the same scope

Annotate, do not duplicate — the append-correction rule in SKILL.md. When new
evidence contradicts a finding in an existing postmortem, add a dated annotation
under that finding in the existing file.

Write a **new** file with `supersedes:` only when the scope was genuinely
revisited as fresh work rather than corrected — a second migration attempt, a
rebuilt feature. The test: if the old document's verdicts still stand and only
one is now wrong, annotate. If its whole framing has been overtaken, supersede.

### Annotating regenerates the derived renderings

**After annotating a markdown file, re-render every sibling rendering that
exists** — the `.html` beside it, and any other derived file sharing its stem.

This is not optional tidying. `references/html-render.md` states that if the
markdown and a rendering disagree, the rendering is wrong by definition; an
annotation that updates only the markdown manufactures exactly that state, and
it does so silently. The rendering is also the copy most likely to have been
sent to someone, so it is the copy most likely to be read and the least likely
to be re-fetched.

Re-rendering *here* is not the same as the unsupported case in
`html-render.md`. That warning is about rendering an arbitrary old file whose
prose shape nothing guarantees. An annotating run has just read and edited the
markdown, so it has the content in hand — transform what the file now says,
annotations included, and re-derive nothing from fresh evidence.

If a rendering exists that you cannot faithfully re-render, **delete it** and
say so. A missing rendering is recoverable from the markdown; a stale one that
looks current is not recoverable at all.

Renderings are derived and disposable. Losing one costs nothing, which is why
regenerating is always the cheap option and staleness never is.

## Cross-linking

If a plan doc for this scope exists, add a one-line pointer to the postmortem in
it. That direction only. The plan doc is where a reader already knows to look;
the postmortem's `artifacts` list already records everything it examined,
including the plan doc and any session logs, so a second inbound link from each
of those would be a copy that drifts.

Do not add an index file. A `postmortems/README.md` listing every file is a copy
whose only consumer is the check that it matches the directory. The naming
convention is the index: listing the directory sorts by date, and a slug grep
finds a topic.

## Reporting

The written path is part of the output. Report it as a repo-relative path,
alongside which resolution rung produced it, so the user can correct a wrong
inference before a second postmortem lands in the same wrong place.
