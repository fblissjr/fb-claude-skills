# Rendering a postmortem to HTML

last updated: 2026-08-07

Read this only when `--html` was passed, or when `--visuals` implied it. A
markdown-only run never needs it.

## What this is and is not

The markdown file is the postmortem. The HTML is a **transform of the markdown
that was just written in this run** — same findings, same wording, different
presentation. It is not a second analysis and must not re-derive anything. Write
the markdown first, read what you wrote, then render it. If the two files
disagree, the HTML is wrong by definition.

Both files are written. `--html` adds a rendering; it never replaces the
markdown. The markdown is the addressable artifact that `supersedes`, the
`artifacts` grep, and the annotate-don't-rewrite rule all operate on, so a run
that produced only HTML would break filing.

Rendering a postmortem written in an *earlier* run is not a designed capability.
`references/report-format.md` is a house style, not a parse contract, so nothing
guarantees an old file is machine-readable. If asked anyway, transform what the
file actually says — including any annotations added since — and do not
re-derive findings from fresh evidence. To get a postmortem that reflects
current evidence, run a new one.

**Annotating is the exception, and it is mandatory rather than merely allowed.**
A run that adds a dated annotation to an existing markdown file has that file in
hand, so nothing is being guessed at: re-render every sibling rendering so the
two stop disagreeing. The ladder for that case, including what to do when a
faithful re-render is not possible, is in the plugin-level `references/filing.md`.

## Provenance

Every rendering says where it came from and when, in a line at the foot of the
page:

```html
<footer class="provenance">
  Rendered from <code>2026-08-07_experience_mitate.md</code> on 2026-08-07.
  The markdown is the record; this file is derived and disposable.
</footer>
```

It costs one line and it makes the failure self-describing. Regeneration keeps
the normal path correct, but nothing stops someone editing a markdown file by
hand outside this skill — and when that happens, a reader who can see the
render date next to a later edit date can tell. A rendering with no provenance
gives them nothing to notice.

Use the markdown's filename, not a title, so the reader can find the record.

## The file

Same directory and same stem as the markdown, so filing runs once rather than
per format:

```
<resolved-dir>/2026-07-01_span_lint-tooling.md
<resolved-dir>/2026-07-01_span_lint-tooling.html
```

Report both paths, repo-relative.

## Constraints

- **Self-contained.** No external requests of any kind — no CDN stylesheet, no
  web font, no remote image, no script tag. The file must render identically
  offline and when sent to someone who will never clone the repo. **A relative
  image link breaks this as thoroughly as a CDN link does**, so figures inline
  as `data:` URIs even though the markdown beside them references the media
  directory. That is the constraint doing its job, not an exception to it.
- **No JavaScript.** Nothing here needs it, and a postmortem that requires a
  script to be readable is less durable than the markdown it came from.
- **Empty sections stay visible.** "Nothing." is a result. Do not hide, collapse,
  pad, or omit a section because it is empty. Style it quietly; do not remove it.
- **Citations stay visible.** A finding without its citation is not a finding in
  either format. Never drop a citation for visual tidiness.
- **Annotations must be distinguishable from original findings.** A dated
  append-correction that reads like part of the original text defeats the point
  of append-correcting.
- **No styler dependency.** There is no `--style` flag and no styler lookup. The
  stylesheet below is the whole design.
- **A chart never replaces its numbers.** The table the chart renders stays in
  the page. Dropping it for visual tidiness turns a checkable measurement into
  an unfalsifiable picture, which is the same failure as dropping a citation.
- **Charts are hand-authored inline SVG**, drawn with the CSS custom properties
  below so they follow the page into dark mode. No chart library — the no-
  JavaScript rule means anything rendering client-side renders nothing.

## Structure

| Markdown | HTML |
|---|---|
| Frontmatter | `<header class="meta">` — the `summary` as a lead paragraph, then a definition list of mode, scope, date, range or version and task, supersedes, then the artifacts list. A person receiving the file alone needs this to know what it covers and what it found. |
| `# Postmortem: ...` | `<h1>` |
| `## 1. What went well` … | `<section>` with `<h2>` |
| Finding paragraphs | `<p>`; the citation stays inline in the sentence where it sits |
| Deviations table | `<table>` with `<thead>` — Planned / Shipped / Verdict |
| Expectation table (experience mode) | `<table>` with `<thead>` — Expected / Actual / What led me to expect it |
| `Nothing.` | `<p class="nothing">Nothing.</p>` |
| Dated annotation | `<aside class="annotation">` with the date in a `<strong>` |
| Inline `code` / paths | `<code>` |
| Image reference | `<figure>` with the image inlined as a `data:` URI and the caption in `<figcaption>` |
| Chart data table | `<figure class="chart">` — the inline SVG, then `<figcaption>`, then the table it renders |

Escape `&`, `<`, `>` in content. Paths and commit hashes appear in postmortems
constantly and a raw `<` will silently eat the rest of a line.

## Template

Embed verbatim. Fill the title, the meta block, and the sections.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Postmortem: SCOPE</title>
<style>
:root {
  --bg: #fdfdfc; --fg: #1c1c1a; --muted: #6b6b66; --rule: #e2e2dd;
  --accent: #7a5c2e; --panel: #f5f4f0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16161a; --fg: #e6e6e1; --muted: #9a9a94; --rule: #2e2e34;
    --accent: #d9b978; --panel: #1f1f25;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 3rem 1.25rem 6rem; background: var(--bg); color: var(--fg);
  font: 16px/1.65 ui-serif, Georgia, "Times New Roman", serif;
  -webkit-text-size-adjust: 100%;
}
main { max-width: 44rem; margin: 0 auto; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 1.5rem; letter-spacing: -0.01em; }
h2 {
  font-size: 1.15rem; margin: 2.75rem 0 0.85rem; padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--rule); letter-spacing: -0.005em;
}
p { margin: 0 0 1rem; }
code {
  font: 0.86em/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--panel); padding: 0.12em 0.34em; border-radius: 3px;
  word-break: break-word;
}
.meta {
  background: var(--panel); border: 1px solid var(--rule); border-radius: 6px;
  padding: 1rem 1.25rem; margin: 0 0 2.5rem;
  font: 0.86rem/1.6 ui-sans-serif, system-ui, sans-serif;
}
.meta .summary {
  font: 1rem/1.55 ui-serif, Georgia, serif; margin: 0 0 0.9rem;
  padding-bottom: 0.85rem; border-bottom: 1px solid var(--rule);
}
.meta dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.3rem 1rem; margin: 0; }
.meta dt { color: var(--muted); }
.meta dd { margin: 0; }
.meta .artifacts { margin: 0.85rem 0 0; padding-top: 0.85rem; border-top: 1px solid var(--rule); }
.meta .artifacts ul { margin: 0.35rem 0 0; padding-left: 1.1rem; }
.meta .artifacts li { margin: 0.15rem 0; }
.nothing { color: var(--muted); font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 0 0 1rem; font-size: 0.94rem; }
th, td { text-align: left; vertical-align: top; padding: 0.55rem 0.7rem; border-bottom: 1px solid var(--rule); }
th { font: 600 0.82rem/1.4 ui-sans-serif, system-ui, sans-serif; color: var(--muted);
     text-transform: uppercase; letter-spacing: 0.04em; }
.annotation {
  border-left: 3px solid var(--accent); background: var(--panel);
  padding: 0.75rem 1rem; margin: 0 0 1rem; font-size: 0.94rem;
}
.annotation strong { color: var(--accent); }
ul, ol { margin: 0 0 1rem; padding-left: 1.35rem; }
li { margin: 0.3rem 0; }
figure { margin: 1.5rem 0; }
figure img {
  display: block; max-width: 100%; height: auto;
  border: 1px solid var(--rule); border-radius: 4px; background: var(--panel);
}
figure svg { display: block; max-width: 100%; height: auto; }
figcaption {
  margin-top: 0.55rem; color: var(--muted);
  font: 0.85rem/1.5 ui-sans-serif, system-ui, sans-serif;
}
figcaption .how { display: block; margin-top: 0.25rem; font-size: 0.95em; opacity: 0.85; }
.figrow { display: flex; flex-wrap: wrap; gap: 1rem; }
.figrow figure { flex: 1 1 16rem; margin: 0; }
.chart table { margin-top: 0.75rem; font-size: 0.88rem; }
.chart svg text { fill: var(--muted); font: 11px ui-sans-serif, system-ui, sans-serif; }
.chart svg .axis { stroke: var(--rule); }
.chart svg .bar { fill: var(--accent); }
.chart svg .bar-alt { fill: var(--muted); }
.provenance {
  margin: 3.5rem 0 0; padding-top: 1rem; border-top: 1px solid var(--rule);
  color: var(--muted); font: 0.8rem/1.5 ui-sans-serif, system-ui, sans-serif;
}
@media (max-width: 34rem) {
  body { padding: 2rem 1rem 4rem; }
  .meta dl { grid-template-columns: 1fr; gap: 0.1rem; }
  .meta dt { margin-top: 0.5rem; }
  .figrow { display: block; }
  .figrow figure { margin: 0 0 1.25rem; }
}
</style>
</head>
<body>
<main>
<h1>Postmortem: SCOPE</h1>

<header class="meta">
  <p class="summary">SUMMARY SENTENCE</p>
  <dl>
    <dt>Mode</dt><dd>span</dd>
    <dt>Scope</dt><dd>SCOPE</dd>
    <dt>Written</dt><dd>YYYY-MM-DD</dd>
    <dt>Range</dt><dd><code>A..B</code></dd>
  </dl>
  <div class="artifacts">
    Artifacts examined:
    <ul><li><code>path/one</code></li></ul>
  </div>
</header>

<section>
  <h2>1. What went well</h2>
  <p class="nothing">Nothing.</p>
</section>

<footer class="provenance">
  Rendered from <code>FILENAME.md</code> on YYYY-MM-DD.
  The markdown is the record; this file is derived and disposable.
</footer>

</main>
</body>
</html>
```

The `:root` custom properties in this template are deliberately mirrored in
`../../postmortem-index/references/index-page.md`. Both templates are meant to be
embedded verbatim so each emits one self-contained file, which is why the block
is duplicated rather than extracted. Change one palette, change the other.

Drop `<dt>Range</dt>` for non-span modes, use `<dt>Version</dt>` and
`<dt>Task</dt>` in experience mode, and drop the `supersedes` row when absent —
omit rows that do not apply rather than rendering them empty. The `artifacts`
block is never omitted; if the list is empty the postmortem has no findings, and
that should be visible rather than hidden.

## Figures

Only under `--visuals`. A figure sits inside the section whose finding it
belongs to, immediately after the paragraph making the claim — never gathered
into a figures section, which would detach it from the finding that justifies
it.

```html
<figure>
  <img alt="Axis labels overlapping at 640px" src="data:image/png;base64,...">
  <figcaption>
    Below 640px the two rightmost axis labels overlap; 640px is the default in
    the quickstart config.
    <span class="how">mitate build --preview scenes/title-card.toml, v0.4.2</span>
  </figcaption>
</figure>
```

- **`alt` is required and says what the figure shows**, not what it is called.
- The **caption carries the claim** and a `.how` line saying how the figure was
  produced, so a developer can reproduce it rather than take it on faith.
- A wrong-versus-intended pair goes in a `<div class="figrow">` so the two sit
  side by side; that comparison is the point, and stacking them loses it.
- A still sequence is a `.figrow` in order, each caption naming what changed
  since the previous still.

Inline every figure as a `data:` URI. Escape nothing inside the base64 payload,
but do check the total: see the size guidance in
`references/visual-evidence.md`.

## Charts

A chart is a `<figure class="chart">` holding hand-authored inline SVG, its
caption, and **the table it renders** — in that order. The table is not
optional and does not go in a `<details>`: a collapsed table is a table a
reader will not check, and checkability is the only reason the numbers are on
the page.

```html
<figure class="chart">
  <svg viewBox="0 0 480 180" role="img" aria-label="Failed commands by error class">
    <line class="axis" x1="40" y1="150" x2="470" y2="150"/>
    <rect class="bar" x="56" y="40" width="48" height="110"/>
    <text x="80" y="166" text-anchor="middle">timeout</text>
    <text x="80" y="32" text-anchor="middle">11</text>
  </svg>
  <figcaption>Failed commands by error class across the run; timeouts are two
  thirds of them and every one followed the same retry.</figcaption>
  <table>
    <thead><tr><th>Error class</th><th>Count</th></tr></thead>
    <tbody><tr><td>timeout</td><td>11</td></tr></tbody>
  </table>
</figure>
```

- Give the `<svg>` a `role="img"` and an `aria-label`, and set `viewBox`
  without fixed `width`/`height` so it scales.
- Use the `.bar` / `.bar-alt` / `.axis` classes rather than literal colours, so
  the chart follows the page into dark mode.
- Label marks directly. A legend costs a lookup that labels do not.
- Mark inferred series in the caption. A chart is believed more readily than
  the sentence it came from, so an unlabelled estimate here launders an
  inference into a measurement.

## Checking the result

Before reporting, confirm on the written file:

- No `http://` or `https://` in any `src`, `href`, or `@import` — including
  every `<img>`, which must be a `data:` URI and never a relative path.
- No `<script>`.
- Every section present, including the empty ones.
- Every citation in the markdown appears in the HTML.
- Every figure has an `alt` and a caption, and sits under a finding.
- Every chart has its table, and the table's numbers match the marks drawn.
- Every figure was cropped and redacted before it was inlined — no title bars,
  sidebars, window titles, absolute paths, or tokens in the pixels.
- The provenance footer names the markdown file and today's date.
