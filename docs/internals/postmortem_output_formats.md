# Postmortem output formats — design for a future pass

last updated: 2026-07-26
status: **both halves implemented.** Filing in `postmortem` 0.3.0, rendering in
0.4.0. The skill's own references are the authority —
`references/filing.md` and `references/html-render.md`. This doc now records
only *why*, and several of its recommendations were rejected on contact with the
implementation; each is marked below. Read it for the reasoning, not the spec.

**The largest correction.** This document's central claim — that the analysis/
render split "is the whole design decision. Everything else follows from it" —
was wrong, and it was wrong because the doc reasoned about renderers as if they
were separate processes. They are not. There is one model in one turn, and HTML
is only ever produced in the run that writes the markdown, so "two renderings
can disagree" is prevented by a rule (render what you just wrote, never
re-analyse) rather than by a data structure. The structured intermediate, the
sidecar-versus-frontmatter question, and the styler-composition ladder were all
answers to a question the shipped feature does not ask. What survived is the
constraint list, which was the genuinely load-bearing part.

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

## Open questions (formats) — resolved in 0.4.0

- **Markdown is always written; there is no HTML-only mode.** The lean was
  right, but for a firmer reason than "it is the machine-readable record":
  filing made the markdown the addressable artifact, so `supersedes` names a
  `.md`, the `artifacts` grep hits the `.md`, and annotate-don't-rewrite edits
  the `.md`. HTML-only would fork all three.
- **`--html`, not `--format=md,html`.** With markdown mandatory the list has
  exactly one optional member, and a comma list advertises a choice that does not
  exist. This also retires the "positional arguments do not extend to a third
  dimension" argument above: `--html` and `--out=<dir>` compose with positional
  mode and scope, so the interface never had to break.
- **`test-audit` stays markdown for now.** One consumer is enough to learn from,
  and its tabular verdicts may want different treatment than narrative prose.
- **Same directory, same stem.** Never a subdirectory. Filing resolves the
  location once, and a derived rendering that moves breaks that.
- **No terminal-specific format.** Markdown is the terminal format.
- **No styler integration, no `--style`, no availability ladder.** The section
  above on composing with a styler was not implemented. One built-in stylesheet
  is the whole design; the hook can be added if a different look is ever actually
  wanted. A soft dependency nobody exercises is still instructions to maintain.
  The rule it was protecting — a complete readable HTML file with no styler
  installed — is now simply the only behaviour there is.
- **Re-rendering an older postmortem is not a designed capability.**
  `report-format.md` is a house style, not a parse contract. Asked anyway,
  transform what the file says, including annotations added since, and never
  re-derive from fresh evidence.

## Where postmortems live, and how a model finds them later

This is a second, separable problem from formats, and today's rule makes it
worse. The current instruction is to *append a `## Postmortem` section to the
plan doc*, or failing that put it in the session log. That optimises for
proximity to the work and against ever finding it again: postmortems end up
scattered across plan docs and dated logs with no shared name, so "what did we
conclude last time we touched X" is unanswerable without reading everything.

**Make each postmortem a standalone file in one known place, and cross-link from
the plan doc rather than living inside it.**

### Where: resolved, never hardcoded

`internal/postmortems/` is *this* repo's answer, not the design. `internal/` is
a convention here and is gitignored here; a plugin that ships to other repos has
no business assuming either. Whether postmortems are local scratch or a tracked,
shared record is the repo owner's call, and it changes the answer completely.

Resolve in this order, stopping at the first hit:

1. **Explicit** — a `--out=<dir>` flag on the invocation, or a per-repo config
   key. `dev-conventions` established the per-repo override pattern with a
   tracked `.dev-conventions.json`; whether postmortem reads that same file, its
   own, or a shared one is an open question below.
2. **Inferred from the repo's existing conventions** — if there is a session-log
   directory, put postmortems beside it; if the repo keeps working notes under
   `docs/`, use that. The repo has already answered "where does prose about this
   project live" and the skill should read that answer rather than impose one.
3. **Propose, then remember.** With no signal, suggest a location, get
   agreement, and write it to the per-repo config so it is asked exactly once.

Never silently create a directory in a layout the repo did not choose.

### Naming

```
<resolved-dir>/YYYY-MM-DD_<mode>_<slug>.md
```

- **Date first** so lexical sort is chronological sort — the same reason session
  logs are `log_YYYY-MM-DD.md`. Recency is the most common filter.
- **Mode** (`session` / `span` / `feature`) because the three answer different
  questions, and a reader usually knows which kind they want.
- **Slug** derived from the scope, not the date: `ruff-diagnostics`,
  `pyright-baseline`, `q3-migration`. This is the part a grep will match.

A span postmortem covering a range should carry the range, not the write date:
`2026-07-01_span_lint-tooling.md` reads better than the day someone got round to
writing it. Put the exact range in frontmatter either way.

The *naming* is the portable part and should hold in any repo. Only the
directory is negotiable.

### Organisation: by scope, not by session

A session is *when* the work happened; the scope is *what it was about*, and
that is what someone searches for months later. Where a repo already indexes
sessions by date, duplicating that axis adds nothing. Keep the directory flat
and let the filename carry both — a flat dated directory greps and globs
cleanly, and subdirectories by topic require guessing the taxonomy up front,
which is exactly the guess that ages badly.

### Discovery without an index file

Do not add an index. A `postmortems/README.md` listing every file is a copy
whose only consumer is the check that it matches the directory, and this repo
has already removed two things on that reasoning. The naming convention *is* the
index: listing the resolved directory sorts by date, and a slug grep finds a topic.

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
- Derived renderings sit beside the markdown with the same stem, wherever that
  resolved to, so the location logic runs once rather than per format.

### Open questions (location) — resolved in 0.3.0

- **Config: its own `.postmortem.json`.** The shared-config lean was rejected.
  One file coupling plugins that release independently forces a schema versioned
  across all of them, and there is exactly one consumer. The convention that
  stops the third plugin inventing a third format is written in
  `plugin-patterns.md`, and three files agreeing on structure migrate
  mechanically if they ever become painful.
- **Cross-link direction: plan doc → postmortem, nothing back.** The plan doc is
  where a reader already knows to look. The session log gets no inbound link
  because the postmortem's `artifacts` list already records it.
- **`supersedes` stays a single value.** A chain is recovered by following the
  pointers; storing it would be a copy whose only consumer is the check that it
  matches them — the same reasoning that removed the index file.

Two things the implementation added that this design did not have: the
`artifacts` list is specified as a *projection of the body's citations* rather
than free metadata, which makes it checkable; and rung 4 must state whether the
proposed directory would be tracked or gitignored, because rungs 1–3 inherit
that answer and rung 4 has nothing to inherit it from.

## Prior art in this repo

- `mitate` renders one scene definition to a live HTML page and to frame-exact
  video from the same source — the "one definition, several renderings" split
  this design is copying, and worth reading before starting.
- `ruff-diagnostics` shows the availability-check pattern: resolve a tool through
  a fallback ladder, degrade quietly, and say which rung you landed on.
