# Rendering a postmortem to HTML

last updated: 2026-07-26

Read this only when `--html` was passed. A markdown-only run never needs it.

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
  offline and when sent to someone who will never clone the repo.
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

## Structure

| Markdown | HTML |
|---|---|
| Frontmatter | `<header class="meta">` — the `summary` as a lead paragraph, then a definition list of mode, scope, date, range, supersedes, then the artifacts list. A person receiving the file alone needs this to know what it covers and what it found. |
| `# Postmortem: ...` | `<h1>` |
| `## 1. What went well` … | `<section>` with `<h2>` |
| Finding paragraphs | `<p>`; the citation stays inline in the sentence where it sits |
| Deviations table | `<table>` with `<thead>` — Planned / Shipped / Verdict |
| `Nothing.` | `<p class="nothing">Nothing.</p>` |
| Dated annotation | `<aside class="annotation">` with the date in a `<strong>` |
| Inline `code` / paths | `<code>` |

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
@media (max-width: 34rem) {
  body { padding: 2rem 1rem 4rem; }
  .meta dl { grid-template-columns: 1fr; gap: 0.1rem; }
  .meta dt { margin-top: 0.5rem; }
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

</main>
</body>
</html>
```

Drop `<dt>Range</dt>` for non-span modes and the `supersedes` row when absent —
omit rows that do not apply rather than rendering them empty. The `artifacts`
block is never omitted; if the list is empty the postmortem has no findings, and
that should be visible rather than hidden.

## Checking the result

Before reporting, confirm on the written file:

- No `http://` or `https://` in any `src`, `href`, or `@import`.
- No `<script>`.
- Every section present, including the empty ones.
- Every citation in the markdown appears in the HTML.
