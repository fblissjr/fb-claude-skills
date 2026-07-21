---
name: explainer-video
description: >
  Create animated explainer sequences — 3D or diagrammatic — delivered as a
  self-contained looping HTML page, an MP4 video, or both. Use when asked to
  "make a video / animation / walkthrough / explainer / animated sequence" of a
  topic, process, architecture, or document (e.g. "turn docs/data-flywheel.md
  into a 30-second video"). Handles topic, audience, duration, visual style,
  subtitles on/off, and characters. Deterministic by construction: the whole
  film is a pure function of time t, so the same scene file drives both the
  live HTML loop and the frame-exact MP4 render. Do NOT use for editing existing
  video files, screen recordings, or slide decks. Extension points for audio
  narration exist but are not yet wired (see references/audio.md).
metadata:
  author: Fred Bliss
  version: 0.1.3
  last_verified: 2026-07-21
  review_interval_days: 90
---

# explainer-video

One idea powers everything here: **the entire film is a pure function of `t`**.
No simulation state, no `Math.random()` at runtime, no wall-clock dependence.
Any frame can be rendered independently and identically — which is why a single
scene file serves as both the interactive HTML artifact (a `requestAnimationFrame`
loop mapping wall time onto `seekTo(t)`) and the source for a frame-exact MP4
(headless Chromium stepping `seekTo(t)` frame by frame into ffmpeg).

## Workflow

### 1. Write the spec first (data before code)

Before touching the template, write the spec as a comment block or scratch file.
Everything downstream is derived from it:

```yaml
topic:      what the sequence explains, one sentence
source:     doc/file it's based on, if any (read it FIRST — facts before film)
audience:   who watches, and what they should understand at the end
duration_s: 15-40 typical; ~3-4s per beat is the pacing that reads well
aspect:     16:9 default
style:      palette (3-5 colors), tone (playful | clinical | technical),
            characters if any (procedural, built from primitives)
subtitles:  on | off  — if on, one caption per beat, <70 chars
beats:      ordered list of {t0, t1, caption, what happens on screen}
outputs:    html | mp4 | loop | poster (see "Delivery" — decide this HERE, not
            at encode time: it constrains the camera, which constrains the beats)
```

If the sequence has to play **inline in a GitHub README**, decide that now. Inline
delivery means an animated WebP, and WebP's cost is driven by how much of the
frame changes per frame — so it wants a held camera (`CONFIG.sway = 0`, no
swooping keyframes). That is a beats-level constraint, not an encode flag.
Diagrammatic sequences hold the camera anyway; narrative walkthroughs do not, and
should not be forced to. See "Delivery".

Get the beats table agreed with the user (or settled yourself) before building.
Retiming a beat later is a one-line edit; re-planning a scene is not.

### 2. Scaffold from the template

Copy the template files into your working directory, then vendor three:

```bash
cp ${CLAUDE_SKILL_DIR}/templates/{scene.template.html,shoot.js,build.js,smoke.js} .
mv scene.template.html <name>.html
bun add three@0.185.1 playwright-core@1.61.1
bun run build.js vendor            # writes three.global.js beside the scene
```

The scene is runnable as-is (placeholder scene, 12s) and already contains the
full contract:

- `CONFIG` — duration, title, style tokens, captions: pure data at the top
- deterministic kit — seeded PRNG (`R[]` pool), `ss()` smoothstep, `bump()`,
  `lerp()`; **never** call `Math.random()`/`Date.now()` in scene code
- camera rail — `KEYS[]` keyframes, smoothstep-interpolated, with instant
  world-cuts hidden under white-flash overlays
- caption + title overlay as DOM (crisp text in screenshots), styled from CONFIG
- driver — `window.seekTo(t)`, `window.DURATION`, `window.stopPlayback()`,
  `window.sceneReady`: the recorder contract; do not rename these

Replace the placeholder in the two marked sections: `buildWorlds()` (geometry)
and `animate(t)` (per-beat motion, every property a function of `t`).

### 3. Iterate by looking, not by hoping

Render single frames and actually look at them — composition, exposure, and
readability problems are invisible in code and obvious in pixels:

```bash
bun run shoot.js <name>.html sample 0,3,7,11  # one PNG per timestamp
```

`shoot.js` prints any scene error to stderr — a renamed three API fails quietly
otherwise, and you do not want to discover it after 600 frames.

Budget 3-4 rounds of look-and-edit. `references/method.md` lists the recurring
failure modes (washed-out lighting, cutaway detail hidden inside solid
geometry, world-cut voids, floating features) and their fixes — read it before
the first render, it saves two rounds.

### 4. Smoke-test the contract

```bash
bun run smoke.js                              # all scenes, source + bundled
```

Checks each scene loads with no console errors, exposes the full contract,
renders something, and — the one that matters — that `seekTo(t)` is
deterministic: same `t` twice, byte-identical pixels. A scene that carries state
across frames looks fine in the MP4 (rendered 0→N once) and wrong in the HTML
loop's second pass. Run it before you shoot 600 frames.

### 5. Build outputs

```bash
bun run build.js all <name>.html              # bundle -> frames -> mp4
bun run shoot.js <name>.html range 300 360    # re-shoot 2s after an edit, then re-encode
```

`bundle` inlines `three.global.js` into the HTML, so the artifact is a single
file that runs offline and the render never touches the network. Requires
ffmpeg on PATH; `shoot.js` finds Chromium via `CHROMIUM_PATH`, playwright's
cache, or system Chrome (macOS/Linux), in that order — `bunx playwright install
chromium` if none.

### 6. Deliver

```bash
bun run build.js loop   <name>.html 12 720   # <name>.webp — plays inline in a README
bun run build.js poster <name>.html 7.2      # <name>.jpg + the markdown to paste
```

HTML: the bundled file is the artifact — it autoplays and loops. It does **not**
run on github.com (script tags are stripped); serve it via Pages or publish it as
an Artifact, both of which run it fine.

MP4: encode at the fps you shot (30 default), `crf 17`, `yuv420p`. A
repo-relative mp4 will **not** render as a player — `<video>` is stripped from
GFM, and GitHub serves video from `raw` as `text/plain; charset=utf-8` with
`X-Content-Type-Options: nosniff`, so the browser refuses to treat it as media.
To get a real player, drag the file into an issue or PR composer and use the
`github.com/user-attachments/assets/...` URL it returns.

That content-type allowlist is the whole mechanism, and it is why WebP works
where mp4 does not — verified by fetching both:

| committed file | what `raw` serves | result in a README |
|---|---|---|
| `.webp` | `image/webp` | renders; animation chunks intact |
| `.mp4` | `text/plain` + `nosniff` | inert |

**Do not track the loop under Git LFS.** `raw` returns the LFS pointer file, not
the image, and the README shows a broken image. Most repos with demo videos hit
exactly this.

Inline motion: GitHub renders animated **WebP**, so `build.js loop` is the output
that embeds. Choose by what the scene is, not by what squeezes under the 10MB cap:

| Scene | Inline artifact | Why |
|---|---|---|
| Held camera (diagrammatic, architecture, data flow) | `loop` — the WebP | Cheap and lossless-feeling. `examples/skill-retrieval.html`: **175 KB**, smaller than its own 232 KB mp4, same content. |
| Moving camera (narrative, characters, world cuts) | `poster` — a still linking to the mp4 | A loop here costs megabytes *and* shows different content than the video, so it becomes a second artifact to maintain. A 19 KB still does not. |
| Authored diagram, motion *is* the explanation | Neither — hand-write an animated SVG | 10-25 KB, inline, no cap. Wrong tool for a rendered 3D scene; right tool for a diagram. |

Measured on the 12s template scene at 960px/24fps, where the default sway moves
every pixel every frame: mp4 0.52 MB, gif 12.08 MB, webp **15.56 MB**. Sway is
free in mp4 and ruinous in WebP. That is the whole reason the camera decision
belongs in step 1.

Whatever you ship, the scene file stays the single source: never maintain two.

## Style quick-reference

- **Playful** (characters, story): saturated pastels, soft shadows, big shapes,
  a character "presenting" — see `examples/pelican-implant.html`.
- **Technical/diagrammatic** (architecture, data flow): flat planes, labeled
  boxes, a pulse traveling edges; camera glides between stations rather than
  cutting between worlds. Same contract, just calmer keyframes and an
  orthographic-feeling long lens (fov 20-25).
- Subtitles off: beats still exist — they discipline pacing even uncaptioned.

## Environment

Pinned: `three@0.185.1`, `playwright-core@1.61.1`, ffmpeg on PATH, bun.

Two constraints that dictate the setup — do not "simplify" them away:

- **three is vendored, never CDN-loaded.** three dropped its UMD build after
  0.160, so `build.js vendor` bundles it into `three.global.js` (an IIFE that
  sets `window.THREE`). IIFE matters: a plain ESM bundle leaks its top-level
  identifiers into global scope and collides with scene variables.
- **The scene stays a classic `<script>`, never `type="module"`.** Chrome
  CORS-blocks ES module imports over `file://`, and opening the HTML straight
  from disk is the whole point of the artifact.

## Files

- `templates/scene.template.html` — the scaffold (start here)
- `templates/shoot.js` / `templates/build.js` — recorder + pipeline (copy beside the scene)
- `templates/smoke.js` — contract + determinism check (run before a full shoot)
- `references/method.md` — design method, procedural-asset cookbook, gotchas (L3: read when building)
- `references/audio.md` — narration/music extension design (not yet wired)
- `examples/pelican-implant.html` — complete worked example, 20s, 5 beats, two worlds
