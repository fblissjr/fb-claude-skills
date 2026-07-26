# Postmortem output formats — design for a future pass

last updated: 2026-07-26
status: **not started.** Design only. Nothing below is implemented.

Two separable problems, deliverable independently: **rendering** a postmortem in
more than one format from a single analysis, and **filing** postmortems so a
model can find the relevant one months later. The second is worth doing even if
the first never happens.

## What is being asked for

A postmortem should be able to render in whatever format the reader needs, from
one analysis pass:

- **Markdown by default.** Unchanged from today, and it stays the default
  because the primary reader is often the next model, not a person.
- **A human-facing rendering on request** — HTML, or HTML/JS — in a style the
  user picks.
- **Both from one run.** An LLM-readable file and a human one for the same
  postmortem, not two separate analyses that can disagree.
- **Styling is pluggable and optional.** The `impeccable` plugin is one possible
  styler and was named only as an example. Nothing here may hard-depend on it.

## Why this is not just "add an `html` flag"

The current skill conflates two jobs: deciding what is true, and writing a
markdown file. Adding formats to that shape means every renderer re-derives the
findings, and two renderings of the same postmortem can then disagree — which is
worse than having one format.

**The split to make first:** analysis produces a structured result; renderers
consume it. One analysis, N renderings, and the renderings cannot contradict
each other because neither one is doing any thinking.

That structured intermediate is the whole design decision. Everything else
follows from it.

## The intermediate

Needs to carry, per finding: the claim, the evidence citation (file, commit,
command, measurement), which section it belongs to, and severity or category.
Plus run-level metadata: mode (`session`/`span`/`feature`), scope, what was
examined, and what could not be.

Two viable shapes, and the choice matters:

1. **Markdown with structured frontmatter.** The markdown file *is* the
   intermediate; an HTML renderer parses its frontmatter and sections. Keeps
   today's output as the source of truth and means no new artifact when nobody
   asks for HTML. Weaker guarantees — a renderer is parsing prose.
2. **A sidecar data file** (`.postmortem.json` next to the report). Both
   renderers consume it. Stronger, but adds an artifact users did not ask for
   and that will drift if hand-edited.

Recommendation: **(1)**, with the section structure in
`skills/postmortem/skills/postmortem/references/report-format.md` treated as the
contract a renderer may rely on. Revisit if a renderer turns out to need
anything prose cannot carry cleanly.

## Argument interface

`postmortem` currently declares:

```yaml
argument-hint: "[session|span|feature] [scope]"
arguments:
  - mode
  - scope
```

Positional arguments do not extend to a third independent dimension — format is
orthogonal to mode and scope, and `postmortem session "" html` is a bad
interface. Switch to flags parsed out of `$ARGUMENTS`:

```
/postmortem:postmortem span --since=2026-07-01 --format=md,html --style=impeccable
```

- `--format` defaults to `md`. Accepts a comma list so one run emits both.
- `--style` is only meaningful for a visual format. Optional, free-form.
- Bare first token stays the mode, so existing invocations keep working.

## Composing with a styler without depending on one

The rule: **postmortem must produce a complete, readable HTML file with no
styler installed.** A styler improves it; its absence never blocks it.

Suggested resolution order:

1. `--style` names something available → invoke it via the Skill tool, hand it
   the rendered content, let it style.
2. `--style` names something unavailable → say so once, fall back to (3), do not
   fail.
3. No style, or nothing available → a self-contained HTML file with minimal
   embedded CSS. Readable, printable, no external requests.

Check availability rather than assuming. A skill that errors because an
unrelated plugin is missing is a hard dependency wearing a soft one's clothes.

## Constraints that must survive

These are load-bearing in the current skill and easy to lose in a rewrite:

- **No citation, no finding.** A renderer must not be able to emit a finding
  with no evidence — if that is representable in the intermediate, the format is
  wrong.
- **Empty sections are valid output.** "Nothing went wrong here" is a result.
  Renderers must not hide or pad empty sections.
- **A file, always.** Chat-only output is not a postmortem. Multiple formats
  mean multiple files, all written, all reported.
- **Annotate, do not duplicate.** If a postmortem for the same scope exists,
  today's rule is to annotate it. Decide what that means when formats differ —
  probably: annotate the markdown, re-render the rest.
- **Finding routing survives.** The "what should outlive this document" step is
  independent of format and must run once, not per renderer.

## Open questions (formats)

- Should `--format=html` alone (without `md`) be allowed, or is markdown always
  written because it is the machine-readable record? Leaning: always write
  markdown, treat other formats as additional.
- Does `test-audit`, the sibling skill, want the same treatment? Its output is
  more tabular and may benefit more from HTML than the narrative postmortem does.
- Where do multi-format outputs live? Same directory as the markdown, or a
  subdirectory once there are three of them?
- Is there a case for a terminal-friendly format distinct from markdown?

## Where postmortems live, and how a model finds them later

This is a second, separable problem from formats, and today's rule makes it
worse. The current instruction is to *append a `## Postmortem` section to the
plan doc*, or failing that put it in the session log. That optimises for
proximity to the work and against ever finding it again: postmortems end up
scattered across plan docs and dated logs with no shared name, so "what did we
conclude last time we touched X" is unanswerable without reading everything.

**Make each postmortem a standalone file in one known place, and cross-link from
the plan doc rather than living inside it.**

### Naming

```
internal/postmortems/YYYY-MM-DD_<mode>_<slug>.md
```

- **Date first** so lexical sort is chronological sort — the same reason the
  session logs are `log_YYYY-MM-DD.md`. Recency is the most common filter.
- **Mode** (`session` / `span` / `feature`) because the three answer different
  questions, and a reader usually knows which kind they want.
- **Slug** derived from the scope, not the date: `ruff-diagnostics`,
  `pyright-baseline`, `q3-migration`. This is the part a grep will match.

A span postmortem covering a range should carry the range, not the write date:
`2026-07-01_span_lint-tooling.md` reads better than the day someone got round to
writing it. Put the exact range in frontmatter either way.

### Organisation: by scope, not by session

A session is *when* the work happened; the scope is *what it was about*, and
that is what someone searches for months later. Sessions are already indexed by
`internal/log/log_YYYY-MM-DD.md`; duplicating that axis adds nothing. Keep the
directory flat and let the filename carry both — a flat dated directory greps
and globs cleanly, and subdirectories by topic require guessing the taxonomy up
front, which is exactly the guess that ages badly.

### Discovery without an index file

Do not add an index. A `postmortems/README.md` listing every file is a copy
whose only consumer is the check that it matches the directory, and this repo
has already removed two things on that reasoning. The naming convention *is* the
index: `ls internal/postmortems/` sorts by date, and a slug grep finds a topic.

What each file should carry so a model can triage it without opening it fully:

```yaml
---
mode: span
scope: lint-and-type-tooling
range: 2026-07-01..2026-07-26
artifacts: [CHANGELOG.md, skills/ruff-diagnostics/, docs/internals/context-cost.md]
supersedes: 2026-06-14_feature_ruff-trial.md   # optional
---
```

`artifacts` is the highest-value field: it makes "has anything been written about
this file or plugin" a one-line grep. `supersedes` handles the annotate-vs-
duplicate rule when a later postmortem revisits the same scope.

### Consequences for the format work above

- The **markdown file is the addressable artifact.** Other renderings are
  derived and sit beside it with the same stem (`.html`), so the naming
  convention does not fork.
- The frontmatter above is a superset of what the intermediate needs, which
  argues further for option (1) — markdown-with-frontmatter as the source of
  truth rather than a sidecar.
- `internal/` is gitignored in this repo, so postmortems here are local. A repo
  that wants them shared should point the skill somewhere tracked; the location
  needs to be a convention the skill reads, not a hardcoded path.

### Open questions (location)

- Does the skill create `internal/postmortems/` unasked, or propose it first?
  Leaning propose-once, then remember.
- Should the session log link the postmortem, the postmortem link the session
  log, or both? One direction is enough; two will drift.
- Is `supersedes` sufficient, or does a long-running scope need a chain the way
  `marketplace.json` `renames` does?

## Prior art in this repo

- `mitate` renders one scene definition to a live HTML page and to frame-exact
  video from the same source — the "one definition, several renderings" split
  this design is copying, and worth reading before starting.
- `ruff-diagnostics` shows the availability-check pattern: resolve a tool through
  a fallback ladder, degrade quietly, and say which rung you landed on.
