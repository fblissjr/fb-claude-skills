# Style reference: three.js 3D scenes

The renderer-specific half of the composition axis, for scenes built on the
three.js template: the camera rail, lighting and colour under ACES, texture
labels, the procedural-asset cookbook, the r185 API notes, and the performance
envelope. The universal method — failure axes, beats discipline, controls,
continuity and semantics review, determinism rules — is `method.md`; read that
first.

This is the first style reference, not the only possible one. A future 2D or
SVG backend gets its own file at this layer; the split exists so that
renderer-specific rules stop reading as universal law (the wash rule below was
exactly that mistake — see "Lighting and colour").

## The camera rail

- Keyframes in `KEYS[]`, smoothstep between consecutive pairs. Ease-in-out per
  segment is what makes it feel filmed rather than programmed.
- A gentle sin() sway (amplitude ~0.06) keeps held shots alive.
- Frame for the beat: the thing changing should occupy the middle third. When a
  new object enters (a part rising, a pulse arriving), aim where it WILL be.
- Long lens (fov 20-25) + frontal angles for diagram worlds; normal lens
  (fov 40-45) + three-quarter angles for character worlds.

## Lighting and colour — wash and crush

ACES compresses highlights, so what goes wrong depends entirely on where your
palette sits. Decide which case you are in *before* touching exposure.

**Pale palettes wash.** Hemisphere + directional + fill over cream, plaster and
pastel materials clips to white. In order of effectiveness:

1. Lower exposure (1.0, not 1.1+) and hemisphere intensity (~0.6).
2. Pick material colours 2 shades darker and more saturated than the target —
   ACES lifts them. A "dark maroon" mouth (0x5e1f28) rendered salmon; 0x24090d
   read as intended. Same for yellows and creams: 0xffd54d not 0xfffbe8.
3. Big pale surfaces (plaster, walls) need speckle/detail dots or they read as
   blank paper at every distance.
4. Transparent glows (MeshBasic + opacity): opacity 0.5+ and saturated colours,
   else they vanish against light backgrounds.

**Dark palettes crush.** A deep background with mid-dark ground and materials has
the opposite problem: everything sinks into the background and the subject stops
separating from the floor. The flywheel walkthrough runs a 0x1b2745 background
over a 0x33405f floor at `exposure: 1.18` with four lights including a warm rim
from the far side — and still renders dark, arguably underlit. Raising exposure
past 1.0 and adding the fourth light were both correct there.

1. Raise exposure above 1.0 and say why in a comment, so the next reader does not
   "fix" it back down.
2. Add a rim light from behind and to the far side. Separating the subject from
   the floor at every camera angle is what it is for.
3. **The speckle advice inverts.** Detail dots earn their place only on a surface
   bright enough for the dots to read against it. The flywheel walkthrough has
   160 seeded floor dots that are invisible in every rendered frame — geometry
   and shadow cost, zero legibility.
4. Emissives do the separating work that ambient light does in a pale scene.
   Budget them per beat rather than leaving everything glowing.

This section is itself a control instance. Working from the previous text — which
said flatly that ACES "WILL wash pale materials to white" and that "every first
render comes out overexposed" — a reviewer predicted the flywheel walkthrough's
payoff would clip, given exposure 1.18, four lights and emissive intensity up to
5.0. The rendered frames refuted it outright: the film is dark end to end.
Following the old text would have made that scene worse. A rule stated without
its precondition gets applied where it does not hold.

## Text on surfaces only reads near-frontal

Draw to an offscreen canvas2d and use it as `CanvasTexture` with
`tex.colorSpace = THREE.SRGBColorSpace`. Overlay text stays in the DOM.

The caveat that used to be missing: **a texture label is only information while
it faces the camera.** In a radial layout most labels never do. The flywheel
walkthrough's station plates render as "1 INGE", "SE", and a "5 COMPILE" so
foreshortened it is a smear. Three options, in order of preference:

1. Keep the label in the DOM overlay, positioned per beat. Always crisp, always
   readable, and it costs nothing at render time.
2. Orient the plate to face the camera arc rather than radially outward.
3. Accept that it is texture, not information, and carry the meaning in the
   caption. Fine for background dressing; not fine for the label the beat is about.

## Procedural assets (no files, no downloads)

Everything is composed from primitives — spheres, boxes, cylinders, planes, tori.
No model files, no textures, no downloads. That constraint is what keeps a scene a
single self-contained HTML file, and it is far less limiting than it sounds.

### The general move

Recipes below are organized by **shape problem**, not by subject, because the same
geometry serves wildly different domains. Before reaching for one, derive your own:

1. **Decompose to primitives.** Almost anything reads as spheres, boxes and
   cylinders in a Group hierarchy. Detail is not what makes it legible.
2. **Silhouette first.** Check it on the squint strip, not at full resolution
   (the rule and the instrument are in `method.md`, "Silhouette").
3. **Signature feature, oversized ~30%.** Whatever identifies the subject — a
   beak, a hat, a chimney, a rotor, a spike in a chart — push it past comfortable.
   The first render is always too timid.
4. **Costume beats anatomy.** A hard hat makes a figure a builder; a torus brim
   and a cap make one a surgeon. Role reads instantly from accessories and never
   from accurate proportions.
5. **Signal over realism.** Emissive brightness, scale pulses and colour shifts
   carry meaning. A photoreal object that does not change is worse than a crude
   one that does.

### Recipes that have actually been built

- **Figure** (creature, mascot, person, robot — anything that presents or
  reacts): body = sphere scaled ~(0.9, 1.1, 1.15); head sphere on a short neck
  sphere; limbs = spheres or cylinders in pivot Groups at the shoulder/hip so
  they rotate for gestures; feet = flattened boxes. A protruding feature (beak,
  snout, visor) = cone scaled flat in one axis and rotated forward. Keep the neck
  and shoulder visible — costume that swallows both kills the silhouette.
- **Expressive face**: head sphere; eyes = white spheres scaled z≈0.5 sitting
  PROUD of the face (bug-eyed reads at distance), pinpoint pupils, glint dots;
  brows floated slightly off the head; blush = flat circles rotated to the
  cheeks; open mouth = dark sphere in a Group (doubles as a portal for dive-ins;
  scale to 0 and swap in a half-torus smile for a finale).
- **Cutaway / cross-section** (geology strata, building floors, soil horizons,
  battery internals, an engine block, a seabed): a flat slab box + bands for
  layers, viewed frontally. CRITICAL: anything "inside" the slab is invisible —
  cavities, thin layers and particles must sit PROUD of the front face by 0.1-0.3
  units, like a museum diorama. A thin dark torus rim where a cavity meets the
  surface sells the carved look.
- **Network or flow** (data pipelines, supply chains, transit maps, circuits,
  approval workflows, nutrient cycles): stations = labeled boxes on a ground
  plane; the payload = a bright emissive sphere whose position is a piecewise
  function of t along the edge path; arrival = `pulse()` scale bump on the
  station.
- **Atmosphere for a large ground plane**: `scene.fog = new THREE.Fog(bg, near,
  far)` matched to the background colour. The floor edge stops reading as a hard
  disc against the backdrop, and distant stations recede instead of competing
  with the subject. Cheap, and it does what a vignette cannot.

### Not yet built, but the shape is obvious

Sketches, not battle-tested — treat them as starting points and add what you
learn back here.

- **Field of instances** (populations, portfolios, fleets, A/B cohorts): one
  instanced primitive per item on a grid, driven by a seeded `R[]` offset so the
  arrangement is deterministic. Colour or height encodes the variable; the beat
  is a wave passing through the field.
- **Mechanism** (gears, levers, pumps, linkages): cylinders and boxes in nested
  Groups where each rotation is a closed form of `t`. Meshing is faked — two
  gears at a fixed ratio never actually collide, so drive both from one ramp.

Shared-material purity — the `setHex` before `lerp` rule — moved to
`method.md`'s determinism section: the worked example is three.js, but the
principle is backend-agnostic and `smoke.js` enforces it for every backend.

# The cinematic kit: post chain, cel shading, analytic IK

Everything in this section shipped in `examples/toybot-walk.html` and was
verified the project's way — `smoke.js` byte-determinism with the full chain
enabled, contact sheet, squint strip, motion profile.

## The post chain (per-frame pure, or not at all)

`build.js vendor` bundles the composer classes onto the THREE namespace:
`EffectComposer`, `RenderPass`, `UnrealBloomPass`, `BokehPass`, `OutputPass`.
The recipe: RenderPass → Bokeh → Bloom → OutputPass (which applies the
renderer's tone mapping + sRGB), `composer.setSize` in the resize handler,
`composer.render()` in `seekTo`.

**The one hard rule: no temporal passes.** TAA and accumulation motion blur
carry state across frames and break the `seekTo` byte-identity contract that
the whole architecture rests on. Every bundled pass is per-frame pure —
**measured**: the toybot scene passes smoke's byte-determinism check with the
full chain enabled, source and bundled. If motion blur is ever wanted, do it
the film way: N sub-samples at `t ± i·dt` averaged — pure, N× render cost,
and an offline pipeline can pay that.

**Rack focus** is the cheapest big cinematic win once BokehPass is in: the
`focus` uniform is a camera-space distance, so compute it per frame from the
live camera (`camera.position.distanceTo(subject)`) and lerp between two
subjects' distances under a `bump()` — a there-and-back rack. Pure, and it
reads instantly as "filmed".

## Cel shading that actually bands

- `MeshToonMaterial` + a `DataTexture` gradient map (3 steps, `NearestFilter`)
  gives the banded light.
- **Hemisphere light washes the bands out.** Toon quantizes *directional*
  light; hemisphere irradiance is smooth and layers on top. Measured on the
  toybot: hemisphere 0.75 read as soft gradients; 0.45 with a stronger key
  restored the cel look. Shift energy from ambient to key.
- **Outlines are inverted hulls added as children**: a `BackSide` black shell
  of the same geometry, scaled ~1.05, parented to the mesh so it rides every
  pivot the IK moves. Because geometries for limbs are pre-translated to
  pivot at the joint, the shell scales about the joint too — close enough at
  these scales.
- **The outline shell exposes every intersection seam.** A head sphere sunk
  into a torso reads fine flat-shaded and grows a hard line the moment the
  shell goes on — clear the joins instead of burying them.
- Bloom threshold sits ABOVE the palette's luminance (0.82 against this
  palette) so only emissives bloom — which is what "budgeted to the payoff"
  means mechanically: the orb's `emissiveIntensity` ramps in its beat and
  nothing else crosses the threshold.

## Analytic two-bone IK and a gait that plants

Closed form, no solver, no state — law of cosines in the sagittal plane,
foot counter-rotated flat (`ankle = -(hip + knee)`). The kit:

- **The plant grid anchors at the walk's START.** Anchored at the world
  origin, the first frame's foot target sat 16 units ahead and the IK swung
  both legs horizontal. Shipped in this scene's first render; the contact
  sheet caught it.
- **Gait derives from distance travelled `s`, never wall time** (method.md,
  cyclic motion): each foot alternates stance/swing over a 2-stride cycle,
  its plant point a pure function of the cycle index — feet freeze mid-plant
  when the body stops.
- **Blend to a rest stance as the motion envelope dies** (`vAmp`, a `pulse`
  over the walk beat) or the last cycle leaves the feet mid-stride.
- **Hop = IK targets, not pose freezing**: mid-air the targets tuck toward
  the body (asymmetrically — back leg higher — or the two feet overlap on
  screen and read as one).
- **Sequence a payoff beat's events**: the first cut ran the hop and the
  orb glow simultaneously and neither read. Anticipation squash → hop →
  landing squash + `backOut` settle → THEN the glow. One event at a time.

## Quality tiers: deliberately not built yet

The plan calls for preview/final tiers. The spike rendered acceptably in a
4-core software-GL container (smoke at 640×360, sheets at 1080p), so the
tier machinery would currently be speculation — it gets built when a
full-length cinematic film actually hurts, and the rule is already decided:
determinism checks and shipped films run at FINAL tier; preview exists only
to iterate.

# three r185 API notes (the renames that fail silently)

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
still exposes correctly at `exposure: 1.0` for the template's own pale palette.
That figure is a property of that palette, not of the renderer — see "Lighting
and colour".

One more silent failure in the same family, which is why the build tooling
insists on `--format=iife`: a non-IIFE bundle leaks its top-level identifiers
into global scope, and a minified two-letter identifier from three once shadowed
a scene variable in a real film and broke its rendering. Nothing errors. The
symptom looks like a scene bug, and you will look for it in `animate()`.

# Performance envelope

Depends entirely on whether you have a real GPU, so know which case you're in
before you budget time:

| Environment | 1080p capture | 20s @ 30fps |
|---|---|---|
| Cloud container, SwiftShader software GL | ~1 fps | ~10 min |
| Local machine, hardware GL | ~5 fps (measured: 288 frames in 54s) | ~2 min |

The software-GL number is the one that shapes the design — keep polycounts modest
(spheres at 24×16, one 2048 shadow map, no postprocessing). But do not let it
scare you off a local render that finishes while you read this. Sample frames are
cheap in both cases.

Capture is embarrassingly parallel, and that falls straight out of determinism:
frames are independent, so N headless pages each shoot a contiguous 1/N of the
range with zero correctness risk. Implemented: `shoot.js <scene> full 30
--workers 4`, or `SHOOT_WORKERS=4` in the environment (which `build.js` callers
inherit). Measured on the template scene: 4-worker output is **byte-identical**
to 1-worker output — and on a 4-core software-GL container the speedup is
**~1.0x**, because SwiftShader already multithreads a single page across the
cores and extra pages only contend. The win case is a many-core box or hardware
GL, where one page cannot saturate the machine — plausible, not yet measured.
Do not expect `--workers` to rescue a low-core cloud render.
