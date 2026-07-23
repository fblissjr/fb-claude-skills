---
name: screenwright
description: >
  Create deterministic animated films of any register — an explainer, a game
  cutscene, a meme, a character short — as a self-contained looping HTML page,
  an MP4, or an animated WebP/AVIF that plays inline in a README. Use when
  asked to "make a video / animation / cutscene / walkthrough / explainer /
  motion graphic / animated meme" of anything: a mechanism, a story beat, a
  system, an organism, a joke, a document. Built on the three.js node stack —
  WebGPURenderer with transparent WebGL2 fallback, TSL node materials,
  MaterialX procedural noise, zero assets — plus a Canvas2D flat-vector
  backend, on one shared contract: the film is a pure function of time t, so
  one scene file drives the live HTML loop and the frame-exact render alike.
  Successor to explainer-video (frozen); same beats/shots/instruments method,
  new renderer and material ceiling. Do NOT use for editing existing video
  files, screen recordings, or slide decks.
metadata:
  author: Fred Bliss
  last_verified: 2026-07-23
  review_interval_days: 90
---

# screenwright

One idea powers everything here: **the entire film is a pure function of `t`**.
No simulation state, no `Math.random()` at runtime, no wall-clock dependence.
Any frame renders independently and identically — one scene file is both the
interactive HTML artifact and the source for a frame-exact MP4.

The register — explainer, cutscene, meme, character short — changes the
geometry, the pacing, and the caption voice. It never changes the contract,
the pipeline, or the review method.

## Workflow

The method is inherited from a project that shipped and hardened it; this file
covers the mechanics, `references/method.md` the discipline. Read method.md
before building — it organizes the recurring failure modes by axis with the
fix for each.

### 1. Spec first (data before code)

Write the spec before touching the template: topic, audience, duration,
`FRAME` (aspect + px — vertical and square are one edit), register, style,
subtitles on/off, and the **beats table** — named beats with durations that
accumulate. Nothing downstream holds a timestamp; retiming a beat is a
one-line edit. Every beat needs geometry, not just a caption; vary durations;
budget the content window, not the beat.

### 2. Scaffold

Two templates, one window contract, every tool works on both:

- `scene.template.html` — the 3D node stack: `WebGPURenderer` (WebGL2
  fallback), TSL node materials, shadows, the cinematography solver
  (`SHOTS[]` as data). Needs the vendor step.
- `scene2d.template.html` — Canvas2D flat vector. Born self-contained; skip
  `bun add three` and `vendor` entirely.

```bash
cp "${CLAUDE_SKILL_DIR}"/templates/{scene.template.html,shoot.js,build.js,smoke.js} .
mv scene.template.html <name>.html
bun add three@0.185.1 playwright-core@1.61.1
bun run build.js vendor <name>.html   # EMBEDS three into the scene; leaves no .js
# (the scene name is required — argument-less `vendor` builds and discards.
#  Skipping this is recoverable: every command that opens a scene embeds
#  automatically via ensureVendor.)
```

Both scenes run as-is (placeholder, 12s) and carry the shared contract:
`BEATS`, `CONFIG`/`STYLE`, `FRAME`, the deterministic kit (seeded `R[]` pool,
`ss`, `bump`, easing personalities, `ramp`/`pulse`/`rampS`/`latch`/`warp` —
see method.md), DOM caption/title overlays, and the driver: `window.seekTo(t)`,
`window.DURATION`, `window.stopPlayback()`, `window.sceneReady`,
`window.BEATS`, `window.FRAME`, `window.FLASHES`. Do not rename any of these.
The 3D template additionally carries `SHOTS[]` with the match-cut constraint
(the 2D template keeps its simpler `KEYS[]` camera rail) and exports
`window.BACKEND` (`'webgpu' | 'webgl2'` — which backend actually rendered;
smoke prints it per run).

Replace the two marked sections: `buildWorlds()` (geometry) and `animate(t)`
(per-beat motion, every property a function of `t`).

**Node-stack rules (3D scenes)** — full detail in `references/webgpu-stack.md`:

- Time reaches shaders only through the `uTime` uniform the template declares;
  never import the TSL `time` node (it wall-clocks).
- The `seekTo` body's `nodeFrame.update()` tick, the boot block's
  `compileAsync`, `renderer.sortObjects=false`, and `frustumCulled=false` in
  `mesh()` are each load-bearing for determinism — measured, not stylistic;
  do not simplify them away. Consequence of unsorted drawing: create
  overlapping transparent objects farther-first.
- Every scene renders through an always-on `RenderPipeline` (pass-through
  by default — zero look change, but the post path is smoke-checked on every
  scene). Effects are `STYLE` flags: `STYLE.bloom` (`{strength,radius,
  threshold}` — thresholds for the TSL bloom are unmeasured; bracket before
  trusting) and `STYLE.dof` (`{maxBlur}` — focus follows the `SHOTS[]`
  `focus` property, so two adjacent shots differing only in focus, joined by
  `cut:'blend'`, are a rack focus).
- No temporal post passes, no `ComputeNode`, no storage buffers.

### 3. Review on three axes (looking is the method)

```bash
bun run build.js sheet <name>.html            # one frame per beat -> .sheet.jpg + .squint.jpg
bun run build.js sheet <name>.html 480 0.95   # every beat at its END — a standing pass
bun run build.js sheet <name>.html 480 0.6 nocap  # every WORD removed — the semantics pass
bun run build.js aspect <name>.html 8.5       # one moment, four window shapes
bun run shoot.js <name>.html sample 0,3,7,11  # arbitrary timestamps
```

**Read the generated images with the Read tool.** A filename is not a review.
Composition fails within a frame (sheet shows it); continuity fails between
frames (watch the loop; `build.js strip` for a suspect window); semantics
fails when every frame is fine and the film explains nothing (cover the
captions — the nocap sheet). Budget 3-4 look-and-edit rounds for composition;
the other two axes need their own passes.

### 4. Smoke-test the contract

```bash
bun run smoke.js                              # all scenes; add WEBGPU=metal to test that path
bun run build.js motion <name>.html           # per-beat motion profile + dead air
```

`smoke.js` checks: loads clean, full contract, deterministic `seekTo` (same
`t` twice → byte-identical), renders something, **and ships something** — a
caption-stripped cold-page check that catches a backend compositing only the
clear color, which four other checks passed on before it existed. Run before
any full shoot.

### 5. Build and deliver

```bash
bun run build.js all  <name>.html             # bundle -> frames -> mp4
bun run build.js loop <name>.html 12 720      # .webp — inline in a README (held camera)
bun run build.js avif <name>.html 12 720      # .avif — much smaller, decode-heavier
bun run build.js poster <name>.html 7.2       # .jpg still + markdown
```

Four peer formats — HTML (the scene itself; Pages or an Artifact, not raw
github.com), MP4 (only format with audio; attach to an issue/PR for a player),
WebP (held camera), AVIF (moving camera, small). Choose at spec time, not
encode time: WebP's cost is per-pixel-changed, so it constrains the camera.
Whatever ships, the scene file stays the single source.

## Backend policy (recorder)

No env vars: WebGL2 fallback — universal, CI-safe. `WEBGPU=metal` (macOS
hardware, verified, ~2.3x faster) or `WEBGPU=vulkan` (Linux, unverified) to
opt in; `ANGLE_BACKEND` selects the GL backend on the fallback path.
`WEBGPU=swiftshader` is diagnostic-only — shoot refuses it. Frames are not
byte-identical across backends; pin the backend on both sides of any
comparison. Never hand-roll WebGPU Chromium flags: the wrong combination
ships flat frames with exit 0 (`references/webgpu-stack.md`).

## Environment

Pinned: `three@0.185.1`, `playwright-core@1.61.1`, ffmpeg on PATH, bun.

Two constraints that dictate the setup — do not "simplify" them away:

- **three is vendored and EMBEDDED in the scene** (`build.js vendor` builds an
  IIFE of `three/webgpu` + `three/tsl` + display passes and splices it in;
  1.09 MB per scene, paid once). Never CDN, never a sibling `.js`, never
  `type="module"`: module imports are CORS-blocked over `file://`, and opening
  the file from disk is the point. `smoke.js` fails any scene that is not
  self-contained.
- **One scene = one file.** No `.bundled.html`, no shipped `three.global.js`.

## Files

- `templates/scene.template.html` — 3D scaffold (node stack)
- `templates/scene2d.template.html` — 2D scaffold (Canvas2D, self-contained)
- `templates/shoot.js` / `templates/build.js` — recorder + pipeline (sheet,
  strip, aspect, motion, loop, avif, poster)
- `templates/smoke.js` — contract, determinism, shipped-frame checks + lints
- `references/method.md` — the universal method: failure axes, beats and
  controls discipline, continuity/semantics review, determinism rules
- `references/film-language.md` — shot vocabulary: sizes, cuts, match
  constraint, focus, camera energy
- `references/webgpu-stack.md` — the node stack: backend policy, async boot,
  the six determinism rules, recorder mechanics, measured brackets
- `references/materials.md` — the material packs: cel (TSL-native banding),
  subsurface (thin/thick split), glass (transmissionNode, ordering
  discipline), bloom observations — read before authoring any surface
  beyond flat color
- `references/bibles.md` — style bibles v2: the whole look as ONE object
  (palette, exposure, post, lens, cut pace, camera energy), switched by one
  line; `examples/gearbox.html` ships the committed control pair
  (`workshop` / `neon`) — read at art-direction time
- `examples/gearbox.html` — the regression film against frozen
  explainer-video: same scene body on both stacks, judged side-by-side
- `examples/materials.html` — the pack showcase: cel, SSS, glass in one
  film, including the overlapping-transparency ordering case
  (rendered previews live in the repository outside the plugin subtree —
  deliberately: installed plugins carry only what the skill needs)
