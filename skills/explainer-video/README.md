# explainer-video

*Last updated: 2026-07-21*

Build short animated explainer sequences — 3D or diagrammatic — from a topic, a
process, or an existing document. Output is a self-contained looping HTML page,
a frame-exact MP4, or both.

The whole film is a pure function of time `t`: no simulation state, no
`Math.random()` at runtime, no wall-clock dependence. Any frame renders
independently and identically, which is why one scene file drives both the
interactive HTML loop and the headless MP4 render. There is never a second copy
to keep in sync.

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
- Chromium — resolved from `CHROMIUM_PATH`, playwright's cache, or system
  Chrome; `bunx playwright install chromium` if none

Pinned dependencies, installed into the working directory (not this repo):
`three@0.185.1`, `playwright-core@1.61.1`.

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
| `skills/explainer-video/templates/scene.template.html` | Runnable scaffold with the full recorder contract |
| `skills/explainer-video/templates/shoot.js` | Headless frame shooter (sample, full, range) |
| `skills/explainer-video/templates/build.js` | vendor, bundle, frames, video |
| `skills/explainer-video/templates/smoke.js` | Contract + determinism check, source and bundled |
| `skills/explainer-video/references/method.md` | Design method, procedural-asset cookbook, r185 API notes |
| `skills/explainer-video/references/audio.md` | Narration/music extension design (designed, not yet wired) |
| `skills/explainer-video/examples/pelican-implant.html` | Worked example: 20s, 5 beats, two worlds |
