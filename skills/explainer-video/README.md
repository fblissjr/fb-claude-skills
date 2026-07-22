# explainer-video

*Last updated: 2026-07-22*

Build short animated explainer sequences — 3D or diagrammatic — from a topic, a
process, or an existing document. Output is a self-contained looping HTML page,
a frame-exact MP4, or both.

The whole film is a pure function of time `t`: no simulation state, no
`Math.random()` at runtime, no wall-clock dependence. Any frame renders
independently and identically, which is why one scene file drives both the
interactive HTML loop and the headless MP4 render. There is never a second copy
to keep in sync.

![skills are retrieval](skills/explainer-video/examples/skill-retrieval.webp)

*Built with this plugin and committed as a 204 KB animated WebP — 11s, held
camera, three beats, and the best-verified case for inline rendering on
GitHub. Source:
[`skill-retrieval.html`](skills/explainer-video/examples/skill-retrieval.html).*

The same film is also committed as a **28.5 KB** animated AVIF —
[`skill-retrieval.avif`](skills/explainer-video/examples/skill-retrieval.avif),
7x smaller, 132 frames, verified animated with `avifdec --info`. It is
committed as a peer delivery option and as the experiment that would settle
whether GitHub animates AVIF inline (one real-world observation says yes; not
independently confirmed here). The README's hero image above points at the
WebP, the case with real verification behind it — re-pointing it at the AVIF
and writing down what happens is the open follow-up.

## Installation

```bash
/plugin install explainer-video@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `explainer-video` | "make a video / animation / walkthrough / explainer", "turn this doc into a 30-second video" | Plan beats, scaffold a deterministic scene, iterate on rendered frames, ship HTML and/or MP4 |

## Invocation

```
/explainer-video:explainer-video
```

Or trigger automatically by asking for an animation, walkthrough, or explainer
of a topic, architecture, or document — for example "turn docs/data-flywheel.md
into a 30-second video".

## Requirements

- `bun`
- `ffmpeg` on PATH
- `img2webp` for inline WebP loops (macOS: `brew install webp`) — Homebrew's ffmpeg has no libwebp
- `avifenc` for inline AVIF loops (macOS: `brew install libavif`)
- Chromium — resolved from `CHROMIUM_PATH`, playwright's cache, or system
  Chrome; `bunx playwright install chromium` if none

Pinned dependencies, installed into the working directory (not this repo):
`three@0.185.1` (3D scenes only — a Canvas2D scene never needs it),
`playwright-core@1.61.1`.

## Reviewing a scene

A film fails on three axes, and looking at stills only covers one of them.

```bash
bun run build.js sheet  <scene.html>   # one frame per beat, tiled + a squint strip
bun run build.js strip  <scene.html> 21.4 21.8   # consecutive frames at a suspect moment
bun run build.js motion <scene.html>   # per-beat motion profile + dead air
bun run smoke.js                       # contract, determinism, caption + exposure lints
```

The contact sheet exists because sampling one frame per beat hides *systematic*
error: six shots framed the same way wrong look like six small problems viewed
one at a time, and like one bad camera formula when tiled. The squint strip is
the silhouette check. `motion` reports how much each beat moves and where
nothing moves at all — a beat far below its neighbours is either a deliberate
hold or an action that never fired.

`motion` deliberately does not claim to detect pops or stalls. Both were built,
measured against a scene with a known discontinuity, and failed: whole-frame
statistics put the defect at 1.00x its own local baseline, and the stall
detector fired at every beat boundary on a good scene as well as a bad one.
`strip` is the partial replacement — consecutive frames tiled, bracketed both
ways: a whole-body jump is obvious, a limb-level one is invisible. Below that
bracket, continuity is reviewed by watching the loop and by checking three known
shapes in source — see `references/method.md`.

## Delivering inline on GitHub

Four peer delivery options — HTML, MP4, WebP, AVIF — chosen by what the
project needs, not by a fixed ranking.

The HTML scene is the interactive source itself: `build.js bundle` makes it a
single self-contained offline file, and it runs fine served from GitHub Pages
or published as an Artifact. It does not run from github.com directly —
GitHub strips `<script>` tags. A `build.js deploy` helper to automate the
publish step is a plausible future addition, not built yet.

MP4 is the only format with audio, and the only route to a guaranteed real
player — but not inline: a repo-relative mp4 is served with a content type no
browser treats as media, so it has to be attached to an issue or PR to play.

GitHub renders animated WebP inline, and, per one confirming real-world
observation (not yet independently verified — see `references/delivery.md`),
animated AVIF. WebP and AVIF are a tradeoff between size and playback cost,
not a ranking:

- **WebP** decodes cheaply and plays smoothly on any hardware, and its inline
  rendering is the best-verified case. Its cost scales with per-frame change,
  so it wants a held camera — a moving-camera WebP loop costs megabytes.
- **AVIF** measures ~54x smaller than WebP on a moving-camera scene and ~7x on
  a held one, and it lifts the held-camera requirement (a moving-camera 12s
  film is 0.28 MB). But an animated AVIF is an AV1 image sequence decoded in
  software, so it costs decode CPU at playback and was observed to stutter —
  worse in macOS Preview than Chrome — on the repo owner's machine. Whether it
  stays smooth on genuinely low-end hardware is still an open question.

Choose by context: size or bandwidth matters most and the audience skews
capable → AVIF; audience hardware is unknown or weak, or the camera moves →
WebP; audio or a guaranteed player → MP4 via attachment; the interactive
scene itself → HTML via Pages or an Artifact. Full tradeoff, encoder settings,
the content-type mechanism, and the inline-rendering evidence chain:
`references/delivery.md`.

## Two constraints worth knowing before you edit the template

Both were found by rendering, not by reading, and both fail quietly if reverted.

**three is vendored, never CDN-loaded.** three dropped its UMD build after
0.160, so `build.js vendor` bundles it locally into `three.global.js`. The
bundle must be IIFE format: a plain ESM bundle loaded as a classic script leaks
its top-level identifiers into global scope, where a minified `MW` collided with
a scene variable and broke rendering.

**The scene stays a classic `<script>`, never `type="module"`.** Chrome
CORS-blocks ES module imports over `file://`, so a module-based scene cannot be
opened directly from disk — which is the entire point of the HTML artifact.

## Layout

| Path | What it is |
|------|-----------|
| `skills/explainer-video/SKILL.md` | The skill: workflow, contract, style quick-reference |
| `skills/explainer-video/templates/scene.template.html` | Runnable 3D scaffold (three.js) with the full recorder contract |
| `skills/explainer-video/templates/scene2d.template.html` | Runnable 2D scaffold (Canvas2D) — same contract, self-contained, `STYLE` split from `CONFIG` |
| `skills/explainer-video/templates/shoot.js` | Headless frame shooter (sample, full, range, beats); `manifest` emits the beat table as JSON without shooting; `full --workers N` shoots contiguous chunks in parallel (byte-identical output, verified) |
| `skills/explainer-video/templates/build.js` | vendor, bundle, frames, video, avif, loop, poster, sheet, strip, motion |
| `skills/explainer-video/templates/smoke.js` | Contract + determinism check, plus caption and exposure lints |
| `skills/explainer-video/references/method.md` | The universal method: failure axes, beats + controls discipline, continuity/semantics review, determinism rules |
| `skills/explainer-video/references/style-3d.md` | The three.js half: lighting, camera rail, procedural-asset cookbook, r185 API notes |
| `skills/explainer-video/references/delivery.md` | GitHub delivery forensics: format tradeoffs, encoder settings, content-type evidence chain |
| `skills/explainer-video/references/audio.md` | Narration/music extension design (designed, not yet wired) |
| `skills/explainer-video/examples/skill-retrieval.html` | Worked example: 11s, 3 beats, held camera, diagrammatic — the one shown above |
