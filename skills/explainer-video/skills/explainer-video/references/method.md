# Method: designing a sequence that reads

## Beats before geometry

A sequence is a list of beats — (time range, caption, one visible change). Write
the beats table first and keep each beat to ONE idea. 3-4 seconds per beat is
the pacing that reads; under 2s the viewer misses it, over 6s it drags. The
title card is a beat. The payoff/outro is a beat. 20 seconds ≈ 5-6 beats.

Structure that consistently works for explainers:
establishing shot → dive into the subject → 3-4 stages of the process →
pull back out → payoff/celebration. The "dive" and "pull out" are world cuts.

## Worlds and cuts

Model distinct settings (an office and a jaw interior; a datacenter and a
database's insides) as separate Groups offset far apart (y -60). Toggle
`.visible` per frame in `animate(t)`; jump the camera between them instantly.

**The one rule about cuts: hide them under a flash, completely.** A camera
interpolating between worlds shows empty void. Make the camera jump span ≤0.06s
between two adjacent keyframes, centered on a `CONFIG.flashes` midpoint. If the
exit keyframe is seconds before the world switch, add a holding keyframe just
before the cut — this exact bug shipped once and cost a re-render.

## The camera rail

- Keyframes in `KEYS[]`, smoothstep between consecutive pairs. Ease-in-out per
  segment is what makes it feel filmed rather than programmed.
- A gentle sin() sway (amplitude ~0.06) keeps held shots alive.
- Frame for the beat: the thing changing should occupy the middle third. When a
  new object enters (an implant rising, a pulse arriving), aim where it WILL be.
- Long lens (fov 20-25) + frontal angles for diagram worlds; normal lens
  (fov 40-45) + three-quarter angles for character worlds.

## Procedural assets (no files, no downloads)

Everything is composed from primitives. Character recipes that worked:

- **Bird/mascot**: body = sphere scaled (0.9, 1.1, 1.15); head sphere on a
  short neck sphere; beak = cone scaled flat in one axis, rotated forward;
  wings = spheres scaled (0.22, 0.8, 0.55) in pivot Groups at the shoulders so
  they can rotate for gestures; legs = thin cylinders + flattened box feet.
  Costume beats anatomy: a teal half-sphere cap + torus brim reads "surgeon"
  instantly. Oversize the signature feature ~30% past comfortable (a pelican's
  beak, a wizard's hat) — the first render is always too timid.
- **Emoji-face human**: head sphere; eyes = white spheres scaled z≈0.5 sitting
  PROUD of the face (bug-eyed reads at distance), pinpoint pupils, glint dots;
  brows floated slightly off the head; blush = flat circles rotated to the
  cheeks; open mouth = dark sphere in a Group (portal for dive-ins, scale to
  0 and swap in a half-torus smile for the finale).
- **Cutaway diorama** (anatomy, geology, architecture): a flat slab box + bands
  for layers, viewed frontally. CRITICAL: anything "inside" the slab is
  invisible — cavities, membranes, and particles must sit PROUD of the front
  face by 0.1-0.3 units, like a museum diorama. A thin dark torus rim where a
  cavity meets the surface sells the carved look.
- **Process pulse** (for data-flow/architecture): stations = labeled boxes on a
  ground plane; the payload = a bright emissive sphere whose position is a
  piecewise function of t along the edge path; arrival = bump() scale pulse on
  the station. Captions carry the semantics.

Text ON surfaces (posters, station labels): draw to an offscreen canvas2d, use
as `CanvasTexture` with `tex.colorSpace = THREE.SRGBColorSpace`. Overlay text
stays in the DOM.

## three r185 API notes (the renames that fail silently)

Pinned at 0.185.1. Several r149-era names were removed outright, and because
`THREE.<removed>` evaluates to `undefined` rather than throwing, the scene keeps
rendering with wrong colors and no error. If output looks subtly off, check
these first:

| removed | use instead |
|---|---|
| `renderer.outputEncoding = THREE.sRGBEncoding` | `renderer.outputColorSpace = THREE.SRGBColorSpace` (also the default) |
| `texture.encoding = THREE.sRGBEncoding` | `texture.colorSpace = THREE.SRGBColorSpace` |
| `THREE.PCFSoftShadowMap` | `THREE.PCFShadowMap` (PCFSoft deprecated; silently downgrades and warns) |
| `renderer.useLegacyLights` | gone — physical lighting is the only mode now |

The directional/hemisphere rig in the template was re-checked under r185 and
still exposes correctly at `exposure: 1.0`; the wash guidance above is unchanged.

## Lighting and color — the wash problem

ACES + hemisphere + directional + point lights WILL wash pale materials to
white. Every first render comes out overexposed. In order of effectiveness:

1. Lower exposure (1.0, not 1.1+) and hemisphere intensity (~0.6).
2. Pick material colors 2 shades darker and more saturated than the target —
   ACES lifts them. A "dark maroon" mouth (0x5e1f28) rendered salmon; 0x24090d
   read as intended. Same for yellows and creams: 0xffd54d not 0xfffbe8.
3. Big pale surfaces (bone, walls) need speckle/detail dots or they read as
   blank paper at every distance.
4. Transparent glows (MeshBasic + opacity): opacity 0.5+ and saturated colors,
   else they vanish against light backgrounds.

## The iteration loop (this is the actual method)

1. `bun run shoot.js scene.html sample <t of each beat>`
2. LOOK at every image. Checklist: Is the beat's subject in the middle third?
   Is anything floating/disconnected? Is detail hidden inside solid geometry?
   Washed out? Does the caption contradict what's on screen?
3. Fix coordinates/colors in source; re-render ONLY the affected samples.
4. Budget 3-4 rounds. Then `bun run build.js all`, and spot-check the encoded mp4 at
   2-3 timestamps INCLUDING mid-transition frames (`ffmpeg -ss <t> -frames:v 1`)
   — transition bugs hide between sampled beats.

## Determinism rules (breaking these breaks video/HTML parity)

- All randomness from the seeded pool `R[]`, indexed, never re-drawn.
- No `Date.now()`, no `performance.now()` outside the preview driver, no state
  accumulated across frames — `seekTo(8)` after `seekTo(2)` must equal
  `seekTo(8)` cold.
- `renderer.setPixelRatio(1)` and `preserveDrawingBuffer: true` — screenshots
  need both.
- Physics is faked with closed forms: a drop is `y0 - k*(t-t0)²`, a wobble is
  `sin(t*ω) * ramp`, a screw-in is position + rotation both driven by the same
  ss() ramp.

## Performance envelope (cloud container, SwiftShader software GL)

1080p renders at roughly 1 fps — a 20s/30fps film is ~10 minutes of frame
capture. Keep polycounts modest (spheres at 24×16, one 2048 shadow map, no
postprocessing). Sample frames during iteration are cheap (~1s each).
