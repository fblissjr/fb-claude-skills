# The index page

last updated: 2026-08-07

Template, styling, and filter script for the generated index.

## Constraints

Same as the postmortem document, with one deliberate exception.

- **Self-contained.** No external requests of any kind — no CDN, no web font,
  no remote image. Must work offline and when sent to someone.
- **JavaScript is allowed here**, and only here. The document rules it out
  because a record that needs a script to be readable is less durable than the
  markdown it came from. An index is not a record; it is a tool that gets
  rebuilt. The script is inline, has no dependencies, and the page is still
  fully readable with scripting off — filtering is an accelerator over content
  that is all present in the HTML, never the only way to reach it.
- **Nothing is hidden by default.** Superseded entries dim and label; they do
  not disappear. Partially-indexed entries show what the filename yielded and
  say so. An index that quietly omits is worse than no index.
- **Zero postmortems is valid output.** Render the page, show the count, and
  state where it looked. Emit the whole page with an empty list and a single
  `<p class="empty">No postmortems in <code>DIR</code> yet.</p>`, and drop the
  controls — a filter over nothing is furniture. Do not substitute a chat
  message for the page.

## Structure

| Source | HTML |
|---|---|
| Directory + count + date span | `<header>` with `<h1>` and a `.count` line |
| Filter input | `<input id="q">`, plus the superseded toggle |
| One postmortem | `<article class="pm" data-search="...">` |
| `summary` | `<p class="summary">` |
| `artifacts` | `<a class="artifact">` each, clickable to filter |
| `lens` (or `mode` on pre-2026-08-07 files) | `<span class="lens">`, verbatim, never translated |
| `supersedes` target | `class="pm superseded"` on the older entry |
| Missing frontmatter | `class="pm partial"` plus a `.badge` saying so |
| Artifact not in the tree | `class="artifact absent"` plus `title="not in the tree today"` |
| By-artifact view | `<section id="by-artifact">` with one `<div class="art-row">` per artifact |
| `version` (`experience` lens) | `<span class="version">` beside the lens badge |
| `task` (`experience` lens) | `<p class="task">`, above the summary |
| A rendering sharing the stem | `.scope` links the rendering; a `<a class="src">md</a>` links the markdown |

`data-search` is a lowercased space-joined concatenation of date, lens, scope,
summary, every artifact, and — where present — `version` and `task`. The filter
matches against that one attribute, so matching behaviour never depends on which
element a term happened to come from. A term a reader can see on the page but
cannot filter by reads as a broken filter, which is why the two lens-specific
fields join the string rather than only being displayed. A lens that requires
fields of its own joins on the same rule.

Escape `&`, `<`, `>` in all content. Paths and hashes are everywhere in this
data and a raw `<` silently eats the rest of a line.

## Template

Embed verbatim. Repeat `<article class="pm">` per postmortem, newest first, and
`<div class="art-row">` per artifact, alphabetical.

The `:root` custom properties below are deliberately mirrored in
`../../postmortem/references/html-render.md`. Both templates are meant to be
embedded verbatim so each emits one self-contained file, which is why the block
is duplicated rather than extracted into a shared stylesheet. Change one
palette, change the other; `test_postmortem_palettes_match` pins the pair.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Postmortems</title>
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
  font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, sans-serif;
  -webkit-text-size-adjust: 100%;
}
main { max-width: 52rem; margin: 0 auto; }
h1 { font-size: 1.6rem; margin: 0 0 0.35rem; letter-spacing: -0.01em; }
.count { color: var(--muted); font-size: 0.88rem; margin: 0 0 1.75rem; }
.controls { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; margin: 0 0 2rem; }
#q {
  flex: 1 1 16rem; padding: 0.55rem 0.75rem; font: inherit; font-size: 0.94rem;
  color: var(--fg); background: var(--bg); border: 1px solid var(--rule); border-radius: 5px;
}
#q:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.toggle { font-size: 0.86rem; color: var(--muted); display: flex; align-items: center; gap: 0.35rem; }
.pm { padding: 1rem 0; border-bottom: 1px solid var(--rule); }
.pm-head { display: flex; gap: 0.7rem; align-items: baseline; flex-wrap: wrap; }
.date { font: 0.86rem/1 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); }
.lens {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
  border: 1px solid var(--rule); border-radius: 3px; padding: 0.1rem 0.4rem; color: var(--muted);
}
.version {
  font: 0.72rem/1 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted);
}
.src {
  font-size: 0.72rem; color: var(--muted); text-decoration: none;
  border: 1px solid var(--rule); border-radius: 3px; padding: 0.05rem 0.3rem;
}
.src:hover { color: var(--fg); }
.task { margin: 0.4rem 0 0; color: var(--muted); font-size: 0.88rem; }
.scope { font-weight: 600; }
.scope a { color: inherit; text-decoration: none; }
.scope a:hover { text-decoration: underline; }
.summary { margin: 0.4rem 0 0.55rem; font: 1rem/1.55 ui-serif, Georgia, serif; }
.no-summary { color: var(--muted); font-style: italic; }
.artifacts { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.artifact {
  font: 0.78rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  background: var(--panel); border: 1px solid var(--rule); border-radius: 3px;
  padding: 0.12rem 0.4rem; color: var(--muted); cursor: pointer;
}
.artifact:hover { color: var(--fg); border-color: var(--accent); }
.artifact.absent { border-style: dashed; }
.absent { text-decoration: line-through; text-decoration-thickness: 1px; color: var(--muted); }
.badge {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--accent); border: 1px solid var(--accent); border-radius: 3px; padding: 0.1rem 0.4rem;
}
.pm.superseded { opacity: 0.55; }
.pm.hidden { display: none; }
#by-artifact { margin-top: 3.5rem; }
#by-artifact h2 {
  font-size: 1.05rem; margin: 0 0 1rem; padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--rule);
}
.art-row { display: grid; grid-template-columns: minmax(10rem, 22rem) 1fr; gap: 0.5rem 1rem; padding: 0.35rem 0; }
.art-row > code { font-size: 0.82rem; word-break: break-word; }
.art-dates { font: 0.82rem/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); }
.art-row.hidden { display: none; }
.empty { color: var(--muted); font-style: italic; padding: 2rem 0; }
@media (max-width: 34rem) {
  body { padding: 2rem 1rem 4rem; }
  .art-row { grid-template-columns: 1fr; gap: 0.1rem; }
}
</style>
</head>
<body>
<main>
<header>
  <h1>Postmortems</h1>
  <p class="count">12 files in <code>internal/postmortems</code> · 2026-03-14 – 2026-07-26</p>
</header>

<div class="controls">
  <input id="q" type="search" placeholder="Filter by scope, conclusion, or artifact&hellip;" autocomplete="off">
  <label class="toggle"><input type="checkbox" id="hide-superseded"> hide superseded</label>
  <span class="count" id="shown"></span>
</div>

<section id="list">

  <article class="pm" data-search="2026-07-26 project span lint-and-type-tooling ruff and pyright diagnostics did not overlap changelog.md skills/ruff-diagnostics/">
    <div class="pm-head">
      <span class="date">2026-07-26</span>
      <span class="lens">project</span>
      <span class="scope"><a href="2026-07-26_project_lint-and-type-tooling.md">lint-and-type-tooling</a></span>
    </div>
    <p class="summary">Ruff and Pyright diagnostics did not overlap; the LSP registration collision was the real constraint.</p>
    <div class="artifacts">
      <span class="artifact">CHANGELOG.md</span>
      <span class="artifact">skills/ruff-diagnostics/</span>
    </div>
  </article>

  <article class="pm" data-search="2026-08-07 experience mitate 0.4.2 a 12-second title-card animation timing is expressed in two units scenes/title-card.toml">
    <div class="pm-head">
      <span class="date">2026-08-07</span>
      <span class="lens">experience</span>
      <span class="version">0.4.2</span>
      <span class="scope"><a href="2026-08-07_experience_mitate.html">mitate</a></span>
      <a class="src" href="2026-08-07_experience_mitate.md">md</a>
    </div>
    <p class="task">A 12-second title-card animation with two timed text reveals.</p>
    <p class="summary">Timing is expressed in two units that read as one, and every wrong turn in the run traced to that.</p>
    <div class="artifacts">
      <span class="artifact">scenes/title-card.toml</span>
    </div>
  </article>

  <article class="pm superseded" data-search="2026-06-14 feature ruff-trial ...">
    <div class="pm-head">
      <span class="date">2026-06-14</span>
      <span class="lens">feature</span>
      <span class="scope"><a href="2026-06-14_feature_ruff-trial.md">ruff-trial</a></span>
      <span class="badge">superseded by 2026-07-26</span>
    </div>
    <!-- pre-2026-08-07: `mode: feature` read into the lens slot verbatim.
         Not translated, and not marked partial -- the field it has is the
         field it had. -->
    <p class="summary">&hellip;</p>
    <div class="artifacts">
      <span class="artifact">skills/ruff-diagnostics/</span>
      <span class="artifact absent" title="not in the tree today">scripts/ruff-trial.sh</span>
    </div>
  </article>

  <article class="pm partial" data-search="2026-03-14 session setup">
    <div class="pm-head">
      <span class="date">2026-03-14</span>
      <span class="lens">session</span>
      <span class="scope"><a href="2026-03-14_session_setup.md">setup</a></span>
      <span class="badge">partially indexed</span>
    </div>
    <p class="summary no-summary">No frontmatter; fields recovered from the filename.</p>
  </article>

  <p class="empty hidden" id="none">No postmortem matches that filter.</p>

</section>

<section id="by-artifact">
  <h2>By artifact</h2>
  <div class="art-row" data-search="changelog.md">
    <code>CHANGELOG.md</code>
    <span class="art-dates">2026-07-26 · 2026-05-30</span>
  </div>
  <div class="art-row" data-search="scripts/ruff-trial.sh">
    <code class="absent" title="not in the tree today">scripts/ruff-trial.sh</code>
    <span class="art-dates">2026-06-14</span>
  </div>
</section>

<script>
(function () {
  var q = document.getElementById('q');
  var hide = document.getElementById('hide-superseded');
  var shown = document.getElementById('shown');
  var none = document.getElementById('none');
  var items = [].slice.call(document.querySelectorAll('.pm'));
  var rows = [].slice.call(document.querySelectorAll('.art-row'));

  function apply() {
    var terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    var n = 0;
    items.forEach(function (el) {
      var hay = el.getAttribute('data-search') || '';
      var ok = terms.every(function (t) { return hay.indexOf(t) !== -1; });
      if (ok && hide.checked && el.classList.contains('superseded')) ok = false;
      el.classList.toggle('hidden', !ok);
      if (ok) n++;
    });
    rows.forEach(function (el) {
      var hay = el.getAttribute('data-search') || '';
      var ok = terms.every(function (t) { return hay.indexOf(t) !== -1; });
      el.classList.toggle('hidden', !ok);
    });
    none.classList.toggle('hidden', n !== 0 || !items.length);
    shown.textContent = (terms.length || hide.checked)
      ? 'showing ' + n + ' of ' + items.length
      : '';
  }

  q.addEventListener('input', apply);
  hide.addEventListener('change', apply);

  document.addEventListener('click', function (e) {
    if (!e.target.classList.contains('artifact')) return;
    q.value = e.target.textContent.trim().toLowerCase();
    apply();
    q.focus();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); }
  });
})();
</script>
</main>
</body>
</html>
```

## Notes on the script

- Every term must match, so `ruff 2026-07` narrows rather than widens.
- Matching runs against `data-search` only. Do not match against rendered text:
  the two would diverge the first time styling changed what is displayed.
- The superseded toggle is the one filter a reader cannot type, which is why it
  is a control rather than a convention.
- `/` focuses the box, `Escape` clears it. Clicking an artifact filters to it.
- With scripting disabled the page loses filtering and keeps everything else.
  That is the intended degradation and the reason nothing starts hidden.

## Checking the result

- No `http://` or `https://` in any `src`, `href`, or `@import`. Links to
  sibling `.md` files are relative and expected.
- Entry count in the page matches the number of files in the directory.
- Every file in the directory appears, including ones with no frontmatter.
- No entry is hidden in the initial HTML — `.hidden` is applied only by script.
- Every artifact in every postmortem's frontmatter appears in the by-artifact
  view, `.absent` ones included. A path that failed to resolve must still be a
  row; the mark is the whole point, and an absent artifact that is also missing
  from the view is indistinguishable from one nobody ever wrote about.
