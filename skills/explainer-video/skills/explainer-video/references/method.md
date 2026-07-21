# Method: designing a sequence that reads

## Three ways a sequence fails

A film can fail on three independent axes, and they need different instruments.
This file used to be organized by topic, which hid the fact that only the first
axis had any coverage at all.

| Axis | Fails | Instrument |
|---|---|---|
| **Composition** | inside a single frame | look at stills — `build.js sheet` |
| **Continuity** | between frames | watching the film, and the three source shapes — no metric works, see below |
| **Semantics** | even when every frame is right and the motion is smooth | cover the caption and ask what the beat is about |

Composition failures are the ones you find by accident, because they are the
only ones a still can show. Continuity and semantics failures survive a careful
frame-by-frame review untouched, which is exactly why they ship.

## Before you build

### Beats are data, not comments

`BEATS` is the only place a timestamp exists. Captions, camera keyframes and
`DURATION` all derive from it, and `animate()` addresses beats by name:

```js
const BEATS = [
  {name:'title', dur:2.4},
  {name:'scan',  dur:2.4, cap:"…"},
  {name:'load',  dur:3.2, cap:"…", capEnd:2.85},   // caption ends early, beat does not
];
ramp(t,'load',0,.56)      // fraction of the beat — stretches when you retime
rampS(t,'load',1.8,2.3)   // seconds from beat start — does NOT stretch
```

**Fractions by default; seconds when the duration is physical.** A rise "across
the first half of a beat" should stretch if the beat grows. A 0.25s flash or a
0.06s world cut should not — stretching a cut window uncovers the cut, which is
the bug below that already cost one re-render. That distinction is the whole
reason both forms exist.

Durations **accumulate**: lengthening `scan` shifts `load` rather than
overlapping it. Retiming is genuinely one edit.

Two things this bought immediately, both structural rather than stylistic:

- Before it existed, a scene written *in the same session that documented the
  problem* still restated caption windows as literals in `animate()`. The
  template made magic numbers the path of least resistance, so no amount of
  warning fixed it.
- Narration-driven audio becomes possible at all: you cannot write a measured
  speech duration back into `ss(t, 5.0, 6.9)`.

#### Migrating an existing scene

Shoot the same sample timestamps before and after and compare with
`ffmpeg -lavfi psnr`. Byte-identical frames mean behavior-preserving; >70 dB is
imperceptible rounding. Anything lower, go look at a difference image
(`blend=all_mode=difference`) before assuming it is fine — when this was done on
the shipped scenes the only sub-70 dB frames were caption-fade boundaries,
localized to the caption pill, and a precision-critical world cut came out
byte-identical.

### Beats before geometry

A sequence is a list of beats — (time range, caption, one visible change). Write
the beats table first and keep each beat to ONE idea. 3-4 seconds per beat is
the pacing that reads; under 2s the viewer misses it, over 6s it drags. The
title card is a beat. The payoff/outro is a beat. 20 seconds ≈ 5-6 beats.

Structure that consistently works for explainers:
establishing shot → dive into the subject → 3-4 stages of the process →
pull back out → payoff/celebration. The "dive" and "pull out" are world cuts.

While the table is still text, check each beat against the semantics axis below.
A beat that states a conclusion rather than showing a process has no geometry,
and that is far cheaper to discover now than after it is built.

### Spike the hostile beat first

Identify the beat that is both load-bearing and compression-hostile — the one
carrying the explanation *and* changing every pixel every frame (a wobbling
mechanism, a whip pan, a particle burst) — and build that beat alone before
committing to the full table.

A few seconds of work answers two questions at once: does the motion read
without a caption, and does it encode small enough for the delivery target. Fail
the first and the premise is wrong. Fail only the second and the delivery plan
changes, not the film. Discovering either after building six beats is expensive.

This is "iterate by looking" applied to the encode step, which otherwise has no
early check. It mostly stops mattering if the camera is held, since per-frame
change is the entire problem.

## Build the control

**For any claim that a technique improves something, build the version without it
and confirm that one is worse. Otherwise you have measured your own effort rather
than the effect.**

This is the single most useful discipline in this file, and every check and
threshold here that survived contact with reality has it. Three forms:

| Claim | Control |
|---|---|
| "this technique makes it read better" | render it without the technique; confirm the difference is visible |
| "this check catches the failure" | construct the failing case; confirm the check fails on it |
| "this threshold is right" | bracket it — one observation confirmed bad above, one confirmed fine below |

Worked instances, each of which changed the outcome:

- `smoke.js`'s blank-frame check was verified against a deliberately blank
  scene. Without that, a check that never fires is indistinguishable from a
  check that always passes.
- The caption bracket is 27 CPS watched and found comfortable, 37 watched and
  found unreadable. The boundary is somewhere in that gap and no observation
  narrows it further, so plan against 27 (the confirmed-good end) and let the
  lint warn at 30. Warning at 25, as it briefly did, flags a density that was
  directly observed to read fine. The threshold before that (17-21) had no
  observation on either side and was wrong by a wide margin.
- The wash rule below was stated here as universal law for months. Rendering one
  dark-palette scene refuted it. See "Lighting and colour".
- Phase-locking two coupled objects is *claimed* to make causality legible.
  Untested — and the way to test it is to break the phase deliberately and check
  whether the broken version reads differently. If it does not, the locking was
  decorative.

The failure mode this prevents is specific and seductive: you apply a technique,
the result looks good, and you conclude the technique did it. The result would
often have looked good anyway. Only the control separates the two.

### The caption bracket is thinner than it looks

Brackets built from one viewer are small-n. Tighten them as more scenes get
watched rather than treating the current numbers as settled.

The caption bracket in particular rests on two observations. A third data point
exists and does not resolve it: an earlier hand-iterated scene shipped a
~60-character caption in a 1.85s window — about 50 characters per second once the
fades are subtracted, nearly double the 27 CPS planning figure and well above the
37-was-unreadable end of the bracket. Its author considers that film imperfect
but serviceable.

Record that as what it is: **an unbracketed real-world instance sitting well above
the line.** It is not a confirmed-comfortable observation, so it does not raise
the threshold. It is not a confirmed-unreadable one either, so it does not
confirm it. What it does establish is that the current bracket is built on very
few observations and the region above it is not actually mapped. Watch for the
next scene that lands between 37 and 50 and record which way it went.

### Verify the control actually ran

A control testing the wrong thing still returns a number, and the number looks
like evidence. This is the failure mode of the rule above, and it is easy to hit:

- A blank-scene check that never modified the scene, so the failure you observed
  came from something else still in the way.
- A "does it fail without X" run where X was still present, so the pass proved
  nothing.
- Asking a summarizing tool whether a document says something and reading its
  silence as absence — absence is exactly what summarization discards.

Before recording a control, confirm it exercised the thing you think it did:
check the command actually errored or didn't, that the file was actually modified,
that the dependency was actually absent. **A green control you did not really run
is worse than no control**, because it converts an open question into a settled
one in your notes and nobody revisits it.

Symptom to watch for: a control that passes on the first attempt, testing
something you expected to be broken.

### The worked instance: three frames that proved nothing

A four-round iteration pass on the flywheel walkthrough finished its encode,
spot-checked the mp4 by extracting three single frames at three beat boundaries,
and concluded: transitions are clean, no voids, no pops.

That conclusion could not follow from that evidence, for two independent reasons:

- **A single extracted frame cannot show a discontinuity.** A pop is a
  relationship between *consecutive* frames; one frame has nothing to be
  discontinuous with. The check was structurally incapable of detecting the thing
  it declared absent — the strongest form of this failure, because no amount of
  care in running it would have helped.
- **None of the three sampled boundaries was the one carrying the known
  discontinuity** in that scene. Even a check that could work was pointed
  somewhere else.

And a few minutes earlier the same pass had grepped for `during(`, seen both call
sites in the output, and moved on — without registering that one of them adds a
term that is nonzero at the beat edge. The defect was looked at directly, in
source, and not seen.

The lesson is not that the pass was careless. It was thorough: four rounds, per-beat
samples, a post-encode check. **It was an instrument gap.** Nothing in the method
made a discontinuity visible, so no amount of diligence within the method would
find one, and the diligence itself produced a confident all-clear. That is exactly
the "green control you did not really run" case, and it is the direct reason the
continuity axis below is written down at all.

It has a second act worth recording. An instrument *was* built for this — a
per-frame delta pass meant to flag exactly that discontinuity — and measured
against the same scene it failed: the defect sat at 1.00x its own local
baseline, invisible under the global motion, and the companion stall detector
fired at every beat boundary of a known-good film. The instrument was cut back
to what it can honestly measure. Building the control did not rescue the check;
it prevented a broken check from shipping and being trusted, which is the more
common payoff and the less satisfying one.

When a check reports absence, ask what a positive result would have looked like.
If you cannot describe one, you have not run a check.

---

# Axis 1 — Composition: what fails inside one frame

## One frame per beat hides systematic error

Shoot the contact sheet, not a pile of loose samples:

```bash
bun run build.js sheet <scene.html>     # one frame per beat, tiled and labelled
                                        # plus <scene>.squint.jpg — the thumbnail strip
```

Reviewing eleven separate PNGs one at a time shows you the same mistake eleven
times without ever registering that it is *one* mistake. Tiled side by side, a
systematic error is obvious in a second — and systematic errors are the
expensive ones, because a single bad constant costs you every beat it touches.

Pattern-blindness, not taste, is what lets a bad shot ship six times.

## Generated keyframes replicate their errors

The flywheel walkthrough generates its six station keyframes from one map:

```js
...STAGES.map((s,i)=>({beat:s, at:.62, a:ANG(i)+0.74, r:13.4, h:5.3,
                       lr:RW-2.1, ly:2.0, la:ANG(i)+MOFF*0.55})),
```

At every one of those six shots the figure stands between the camera and the
station he is presenting, occluding the mechanism the caption is describing and
pushing it to the frame edge. One shared angular offset, six broken shots. The
hand-authored keyframes in the same scene — title, meet, spin, signal, outro —
are all well composed.

**Verify one generated shot before generating the rest.** A formula that frames
one beat correctly by luck will frame the other five wrong with total
consistency.

## Subject versus apparatus: decide who owns the middle third

When a figure and the thing it is presenting must share a shot, they compete for
the same screen space. Pick one to own the middle third for that beat and push
the other to a side third. Splitting the difference loses both — which is what
the flywheel walkthrough's `MOFF = 0.30` offset does: the figure is not clear of
the station and the station is not clear of the figure.

The rule underneath is the old one: the thing *changing this beat* occupies the
middle third. If the mechanism is what animates, the mechanism gets the frame
and the figure gestures from the edge.

## The camera rail

- Keyframes in `KEYS[]`, smoothstep between consecutive pairs. Ease-in-out per
  segment is what makes it feel filmed rather than programmed.
- A gentle sin() sway (amplitude ~0.06) keeps held shots alive.
- Frame for the beat: the thing changing should occupy the middle third. When a
  new object enters (a part rising, a pulse arriving), aim where it WILL be.
- Long lens (fov 20-25) + frontal angles for diagram worlds; normal lens
  (fov 40-45) + three-quarter angles for character worlds.

## Silhouette, and the instrument for it

If a subject does not read as a black shape at thumbnail size, more detail will
not save it. This rule was in the file for a long time with nothing to apply it
with; the squint strip from `build.js sheet` is the instrument.

The flywheel walkthrough's central figure fails it at both distances: shawl and
headscarf merge into a single rounded mass, there is no neck or shoulder line,
and the arms are lost against the body. It reads as an egg. At full resolution
it is a well-built character — which is the point. Silhouette failure is
invisible at the size you are authoring at.

Fixes are structural, not additive: separate the masses (raise the head, narrow
the neck, break the shoulder line), push limbs away from the torso in the rest
pose, and give the signature feature a profile that survives filling in solid.

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

## Dwell: measured, not derived

Two numbers observed by rendering and watching, not reasoned about. Treat them
as starting points and re-measure rather than trusting the arithmetic:

- **A sweep highlight at ±0.55 units wide reads as a flicker.** At ±0.9 the lit
  phases of neighbouring elements overlap and it reads as a wave passing
  through. Width mattered more than beat length: stretching the beat alone just
  spaced the flickers further apart.
- **A beat under ~3s felt rushed even when its caption was comfortably
  legible.** Caption speed and motion speed are separate problems and the
  caption is the weaker signal — a beat can pass a reading-speed check and still
  be too fast to follow.

Overlay fades belong **inside** their beat. The title fade used to be centred on
the beat boundary, which spilled title pixels 0.3s into the next beat and made
retiming non-local. Fade out completes at `t1`; fade in starts after `t0`.

### Transit eats the content window

The ~3s floor applies to the part of the beat where the *content* happens, not
the beat's nominal duration. If a beat opens by moving something into position —
a figure walking to the next station, a camera travelling, a part sliding in —
that transit is not content and the mechanism gets what is left.

Each stage beat in the flywheel walkthrough runs 3.4s and spends its first 42%
walking, leaving under 2s for the mechanism the caption names. Comfortably
under this file's own floor, in a scene whose beat durations all look fine in
the table.

This is the same effective-window argument the caption budget makes. Apply it to
motion too: measure the window in which the thing you are explaining is actually
doing something.

### Uniform beat durations are a smell

Six consecutive beats at exactly 3.4s, framed by the same formula, with the same
walk-then-present rhythm, reads as a slideshow however good each individual shot
is. Identical duration is the visible symptom of identical structure.

Vary the durations because the beats genuinely differ in weight — the one with
the surprise gets longer, the one that only re-establishes position gets shorter.
The flywheel walkthrough does this correctly in exactly one place: its approve
beat runs 4.6s against the others' 3.4s, because something actually happens
there.

## Procedural assets (no files, no downloads)

Everything is composed from primitives — spheres, boxes, cylinders, planes, tori.
No model files, no textures, no downloads. That constraint is what keeps a scene a
single self-contained HTML file, and it is far less limiting than it sounds.

### The general move

Recipes below are organized by **shape problem**, not by subject, because the same
geometry serves wildly different domains. Before reaching for one, derive your own:

1. **Decompose to primitives.** Almost anything reads as spheres, boxes and
   cylinders in a Group hierarchy. Detail is not what makes it legible.
2. **Silhouette first.** Check it on the squint strip, not at full resolution.
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

### Mutating a shared material is pure only if you restate it

This is the sneakiest form of accumulated state, and the determinism rules never
called it out. A material is scene-global; touching its colour without resetting
first carries the change into the next frame.

```js
mat.color.setHex(BASE).lerp(TARGET, u);   // pure — restated from a constant
mat.color.lerp(TARGET, u);                // accumulates — desyncs on the 2nd pass
```

The second form renders correctly in the MP4, which is shot 0→N exactly once,
and wrong in the HTML loop's second pass. `smoke.js`'s determinism check catches
it; understanding why saves the debugging round. The flywheel walkthrough gets
this right in four places, always via `setHex` before `lerp`.

The same applies to `emissiveIntensity`, `opacity` and anything else you reach
for on a shared material: assign it outright every frame, never adjust it.

---

# Axis 2 — Continuity: what fails between frames

Stills cannot show time. Every failure in the composition axis is visible in one
frame, which is why the documented loop finds them. Nothing in this section is.
A film can pass a careful frame-by-frame review and still stutter, pop and slide,
and every one of the defects below shipped in a scene whose sampled frames all
looked correct.

```bash
bun run build.js motion <scene.html>    # per-beat motion profile + dead air
```

**There is no automated detector for this axis.** That is a measured result, not
an omission. A per-frame delta pass was built to flag pops and stalls and tested
against a scene carrying one known discontinuity and two known stalls:

| attempt | result |
|---|---|
| pop = frame delta above 4x the global median | known 0.35 rad limb step measured **1.00x its local baseline** — invisible under a moving camera |
| pop = step-halving probe, exploiting `seekTo` purity | 1.60 at the known step vs 1.69 at a control boundary — not a separator |
| stall = run of near-zero delta | fired at **every** beat boundary, on the known-good film as well as the bad one — films are supposed to settle between beats |

Whole-frame statistics can see that a film moves. They cannot see *which* of the
things in it moved wrongly. What the command reports instead is the profile: how
much each beat moves, and stretches where nothing changes at all. A beat far
below its neighbours is either a deliberate hold or an action that never fired;
a run of near-identical bars is a slideshow.

One pixel-level instrument does survive, with a measured range:

```bash
bun run build.js strip <scene.html> 21.4 21.8   # consecutive frames, tiled
```

Consecutive frames rather than one per beat, so adjacent cells can be compared —
smooth motion moves a similar amount per cell, a discontinuity moves once and
stops. It exists because the reviewer is often an agent, which cannot play a
film, and "watch the loop" is not an instruction such a reviewer can follow.

Bracketed both ways on a moving-camera scene: a **1.2-unit whole-body jump**
(~15% of frame height), injected as a positive control, is obvious between
adjacent cells. A **0.35 rad limb rotation** (~2% of frame area) is invisible —
the same signal that measured 1.00x its local baseline above. So `strip` reaches
world- and object-level breaks and stops short of limb-level ones, and does
better on a held camera where nothing else competes for the eye.

Below that bracket the axis is reviewed by knowing the shapes below and checking
them in source, and by watching the loop. That is a weaker instrument than a
metric and it is the honest one.

A note on dead air, since it is the finding people are most tempted to silence:
the shipped diagrammatic example trips it, with ~1.8s of a completely static
title card. That is a legitimate held title, not a defect, and the correct
response is to say so — not to lower the floor until the check goes quiet. A
threshold moved to make a known case pass stops measuring anything.

## `ss()` has zero derivative at both ends

Smoothstep is `u*u*(3-2u)`, whose derivative `6u(1-u)` is zero at both `u=0` and
`u=1`. **Every ramp starts and ends at a dead stop.** For a camera segment that is
exactly right — it is what makes the move feel filmed rather than programmed. For
anything carrying momentum it is wrong.

The flywheel walkthrough drives its wheel as a sum of per-beat ramps:

```js
wheel.rotation.y = 1.9*ramp(t,'spin',.18,1)
                 + 3.4*ramp(t,'signal',0,1)
                 + 2.6*ramp(t,'outro',0,.78);
```

Three consecutive beats, three ramps, so angular velocity returns to zero at each
boundary. The wheel decelerates to a full stop twice during the payoff — in a
film whose entire subject is a flywheel that should be gathering speed. Every
sampled frame is correct. The defect exists only in the derivative.

**Author continuous motion as one ramp spanning every beat it covers**, or
integrate a speed envelope in closed form. Per-beat ramps are for per-beat
events, and momentum is not an event.

## `during()` is a step function

`during(t,'x')` is a hard boolean on the beat bounds. Any term you add inside it
that is nonzero at the beat edge steps to zero in a single frame.

```js
if (during(t,'approve')) armR.rotation.x += -0.85*ramp(t,'approve',.40,.58)
                                          +  0.5*ramp(t,'approve',.60,.68);
```

Both ramps are saturated at the end of the beat, so the term is −0.35 rad right up
to the boundary and 0 on the next frame: the arm snaps roughly 20°, and the prop
held in that hand vanishes on the same frame.

The instructive part is that the same scene handles three other visibility
toggles correctly — the ingest blocks, the verify ticks and the sparkles all pair
a `.visible` flip with a scale that has already reached zero, so the flip is
invisible.

### The rule is not "never step" — it is "never step uncovered"

A discontinuity is only a defect if the viewer can see the frame it happens on.
Two ways to make a step safe, and you need one of them:

1. **Drive the term to zero at the edge.** Use `ramp`/`pulse` so the value
   reaches zero on its own before the boolean flips, or pair the flip with a
   scale or opacity that already has. This is the common case.
2. **Cover the step frame with a flash.** At full flash opacity the frame is
   white, so nothing underneath it can pop.

The earlier hand-iterated scene demonstrates the second: it toggles whole-world
visibility with a hard boolean on a raw timestamp — an enormous discontinuity,
the entire frame changing at once — and it is completely invisible, because the
white flash is at full opacity on exactly that frame. The arm snap above pops for
the opposite reason: nothing covers it.

So `during()` is not forbidden. It is unguarded, and you have to supply the guard.
Given how reliably it misfires when you don't, prefer `pulse(t,'beat',a,b)` —
zero at both ends by construction — and reach for `during()` only when the thing
it gates is already invisible, or a flash is sitting on the boundary.

## An effect that finishes does not leave

Distinct from pops and stalls, and it bit twice in one scene. The shape: an
effect drives to the end of its ramp and **parks there**, holding its terminal
state for the rest of the film, because nothing ever turns it off.

Two instances, same shape:

- A sweep highlight whose position parked at the end of its travel — which
  happened to land inside the last sample's highlight window, so that one sample
  stayed lit for the remaining 28 seconds of the film.
- A particle burst scaled by `bump(u,0,1)`, which is **zero at `u==1`** — so the
  burst scaled itself back down to nothing at exactly the moment it was supposed
  to be at full size.

The second is a footgun in the kit this skill ships. `bump()` is rise-and-fall:
correct for "flash and go", wrong for "grow and stay". Reaching for `bump` when
you want `ss` is easy, because both read as "animate this in" at the call site.
Say which half of the curve you actually want before you pick.

**Switch an effect off at the end of its beat; do not trust it to leave.** Gate
the whole station's contribution with a closing ramp:

```js
const gate = 1 - ramp(t,'analyze',.90,1);      // explicit off-switch
bits[k].material.emissiveIntensity = (1 + lit*2.4) * gate;
```

Both instances are invisible in the beat they belong to — the beat they belong to
is correct. They only appear in *later* frames, which is why sampling one frame
per beat misses them entirely, and why the contact sheet is the instrument: a
station still lit three beats after its turn is obvious the moment the beats are
tiled side by side, and invisible when they are eleven separate images.

## Cyclic motion derives from progress, not from `t`

Any repeating motion tied to travel must be driven by the *progress* variable,
not by wall time, or it keeps cycling while the thing stands still. Feet slide,
wheels spin on a stationary cart, a conveyor runs under motionless boxes.

The flywheel walkthrough gets this right, and it is the best idea in the scene:

```js
const phase = s * Math.PI * 5.0;    // s = fractional station index, not t
const sw = Math.sin(phase) * .62 * v;
legL.rotation.x = sw; legR.rotation.x = -sw;
```

Gait phase comes from distance travelled, so when `s` stops advancing the stride
stops dead in whatever position it was in. Scaling the amplitude by the speed `v`
settles the pose rather than freezing mid-stride.

Generalizes past walking to anything whose cycle should be locked to travel:
wheels and rotors, footfalls, conveyor treads, a pulse stepping along a path, a
rotating drill advancing into a surface.

## Hard cuts are the one discontinuity you want

Model distinct settings (a workshop and a machine's interior; a datacenter and a
database's insides) as separate Groups offset far apart (y -60). Toggle
`.visible` per frame in `animate(t)`; jump the camera between them instantly.

**The one rule about cuts: hide them under a flash, completely.** A camera
interpolating between worlds shows empty void. Make the camera jump span ≤0.06s
between two adjacent keyframes, centered on a `CONFIG.flashes` midpoint. If the
exit keyframe is seconds before the world switch, add a holding keyframe just
before the cut — this exact bug shipped once and cost a re-render.

Use `rampS`/`pulseS` for the flash and the jump, never fractions: stretching a
cut window when the beat is retimed uncovers the cut.

This machinery earns its weight. An earlier hand-iterated scene, predating the
beats table, is built entirely on it: two worlds in one scene graph — an
establishing exterior and a cutaway interior — joined by two instantaneous camera
jumps under white flashes. That scene is the concrete instance behind the
establishing shot → dive in → pull back out structure recommended above. A
two-world film is not an exotic case; it is the default shape for anything with
an inside.

A cut is the one continuity break you *want*, so nothing flags it and nothing
needs to. Check it the only way that works: watch the two frames either side of
the cut, and confirm the flash is at full opacity on the frame the world changes.

---

# Axis 3 — Semantics: what fails when it looks right

Every frame is well composed, the motion is smooth, and the film still does not
explain anything. This axis is what the whole exercise is for, and it has the
weakest tooling: the test is a question you ask yourself.

## Cover the caption

**Hide the caption and ask what the beat is about.** If you cannot tell, the
geometry is not carrying the explanation and you have built a slideshow with a
3D background.

This replaces the older and much weaker "does the caption contradict what's on
screen?" — contradiction is rare and easy to spot. The common failure is a
caption that is doing all the work while the picture is merely present.

## A beat that asserts has no geometry

Beats that describe a *process* decompose into visible change almost by
themselves. Beats that state a *conclusion* do not, and the path of least
resistance is to run the claim as a caption over whatever happens to be on
screen.

The flywheel walkthrough's last two beats assert "The six stages are the easy
half" and "Signal quality decides whether it compounds". `animate()` gives them a
wheel spin and a sparkle burst. Nothing on screen represents signal quality,
easiness, or the comparison between the two. They are B-roll with a thesis
printed over them.

Two honest options:

- **Invent geometry for the assertion.** "Signal quality decides whether it
  compounds" wants two wheels side by side turning at visibly different rates
  from visibly different input — a comparison the viewer can see rather than read.
- **Cut the beat.** A film that shows six stages well and stops is better than
  one that shows six stages well and then asserts two things it cannot draw.

## The hazard of building a film from a document

This is where a source document leads you wrong. A doc's *mechanism* decomposes
into beats cleanly — that is what a mechanism is. A doc's *argument* does not,
and it is usually the part the author cared most about, so it survives into the
beats table and then has nothing to render.

Flag assertion-shaped beats while the table is still text. At that point the fix
is free.

## Motion that reads versus causality that reads

These are different problems and the second is harder. A sweep only has to be
perceived as motion — get the dwell right and it works. But a beat whose job is
"A drives B" fails if the viewer perceives *A moving and B moving*. Co-occurrence
is not causation, and no amount of extra beat length fixes it.

The lever is **phase and derivation, not duration**. If B's motion is visibly
locked to A's — same phase, amplified, or offset by a fixed lag — the coupling is
perceptible. If A and B are animated from independent expressions that merely
happen to overlap in time, it reads as two unrelated things moving. Drive B from
A's own expression rather than from `t` separately:

```js
const rise = ramp(t,'propose',.30,.80);
proposalDoc.position.y = lerp(.55, 2.05, rise);
evidence.position.y    = lerp(.55, 1.55, off * rise);   // derived from the doc's ramp
```

Verify it with a control: deliberately break the phase relationship and watch
again. If the broken version reads the same as the locked one, the locking was
not doing the work and the causality is not landing — go find another cue
(a connecting element, a lag, a colour that propagates).

Untested; recorded because it is the specific thing to watch a spike for.

---

# The iteration loop (this is the actual method)

1. `bun run build.js sheet <scene.html>` — contact sheet plus squint strip.
2. **LOOK at the sheet**, all beats at once. Composition checklist: Is the beat's
   subject in the middle third? Does the figure occlude the mechanism? Is
   anything floating or disconnected? Is detail hidden inside solid geometry?
   Washed out, or crushed dark? Are texture labels facing the camera? Then the
   squint strip: does each subject read as a shape?
   **Look for repeats** — the same error in three shots is one bug in a formula.
3. Fix coordinates and colours in source; re-render only the affected samples
   with `shoot.js sample`.
4. Budget 3-4 rounds on composition — that's the axis that converges with
   rounds. Continuity and semantics do not, no matter how many times you repeat
   this loop; they need the separate passes in steps 5-7 — see the worked
   instance above, where four composition rounds converged cleanly while two
   continuity defects rode along untouched to a confident all-clear.
5. `bun run build.js motion <scene.html>` — read the per-beat profile. Any beat
   far below its neighbours, or any dead air you did not intend, is a question.
   It will not find pops or stalls; grep your own source for the three shapes.
6. **Watch the film**, start to finish, at speed. This is the only instrument for
   the continuity axis that catches everything, and it takes as long as the film.
7. Cover the captions and watch it again. Any beat you cannot follow is a
   semantics failure — fix the geometry or cut the beat.
8. `bun run build.js all`, then spot-check the encoded mp4 at 2-3 timestamps
   INCLUDING mid-transition frames (`ffmpeg -ss <t> -frames:v 1`) — transition
   bugs hide between sampled beats.

Steps 5-7 are the ones that were missing. They are also the cheap ones.

# Determinism rules (breaking these breaks video/HTML parity)

- All randomness from the seeded pool `R[]`, indexed, never re-drawn.
- No `Date.now()`, no `performance.now()` outside the preview driver, no state
  accumulated across frames — `seekTo(8)` after `seekTo(2)` must equal
  `seekTo(8)` cold.
- Shared materials are state. Restate colour and intensity from a constant every
  frame; never adjust them incrementally. See the cookbook entry above.
- `renderer.setPixelRatio(1)` and `preserveDrawingBuffer: true` — screenshots
  need both.
- Physics is faked with closed forms: a drop is `y0 - k*(t-t0)²`, a wobble is
  `sin(t*ω) * ramp`, a screw-in is position + rotation both driven by the same
  ss() ramp.

## Where you will be tempted to break this

The rule above is easy to keep until the subject *is* a physical process. Any
scene depicting **momentum, decay, accumulation, charge, wear, growth, or
trails** pulls toward simulation, because the natural way to write "a flywheel
coasting down" is to carry velocity from the previous frame. That is state
across frames, and it breaks two things at once: `seekTo` stops being pure, and
the beat stops being independent of the beats before it.

Author the closed form instead. A coast-down is `ω0 * exp(-k*(t-t0))` evaluated
from `t`, never integrated. Accumulation is `count * ramp(t,...)`, not `count++`.
A trail is N samples of the same position function at `t - i*dt`, not a buffer of
past positions.

This is where the physical metaphor pulls against the architecture, and it is
worth knowing *before* writing the beat rather than after `smoke.js` fails the
determinism check. Physical-metaphor scenes are exactly the ones most likely to
reach for a simulator — and exactly the ones where a viewer would notice the
HTML loop and the MP4 disagreeing on the second pass.

Note the interaction with the continuity axis: the closed form that keeps you
deterministic is also the one that keeps velocity continuous across a beat
boundary. Summed per-beat ramps satisfy determinism and still stall.

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
frames are independent, so N headless pages can each shoot 1/N of the range with
zero correctness risk. Not implemented yet — the obvious fix if long pieces start
hurting.

# Delivering inline on GitHub

GitHub renders animated WebP and GIF inline, and — per one confirmed
still-image fetch plus one real-world report, see below — animated AVIF as
well. It does **not** render a repo-relative mp4 as a player, and it strips
`<script>`, so the HTML artifact is inert on github.com (Pages or a published
Artifact both run it fine).

The HTML scene is a fourth, co-equal delivery option alongside mp4, WebP and
AVIF — not a footnote to them. It is the interactive, deterministic source
itself, not a rendering of it: `build.js bundle` makes it a single
self-contained file that runs offline, and it plays fine served from GitHub
Pages or published as an Artifact. It does not run from github.com directly,
for the `<script>`-stripping reason above. A `build.js deploy` helper to
automate that publish step is a plausible future addition; it does not exist
yet.

WebP's cost is driven by how much of the frame changes per frame, which makes
the camera decision a file-size decision for WebP. AVIF does not have that blind
spot — it is cheap on both camera styles — but it buys the smaller file with a
cost that does not show up in a size table, so read the tradeoff below before
reaching for it.

| Scene | 12s template, 960px/24fps, moving camera | 11s held-camera diagram, 720px/12fps |
|---|---|---|
| mp4 | 0.52 MB | 0.23 MB |
| gif | 12.08 MB | — |
| webp | 15.56 MB | 0.20 MB |
| **avif** | **0.28 MB** | **0.029 MB** |

(A second measurement run reproduced this benchmark on the moving-camera case —
mp4 0.68 MB, webp 15.16 MB — close enough to the figures above to trust the
avif row as directly comparable to the rest of the table.)

AVIF is ~54x smaller than WebP on the moving-camera scene and ~7x smaller on
the held-camera one, and it beats the mp4 on both. Sway (`CONFIG.sway = 0.06`,
every pixel changing every frame) is what makes WebP expensive; AVIF does not
have the same blind spot.

### The size win costs decode at playback

This is the cost the table does not show, and it is the input that keeps this a
genuine tradeoff rather than a size contest. An animated AVIF is an **AV1
still-image sequence**, not a video stream: browsers and viewers decode it
frame by frame in software, and it does not get the hardware video-decode path
an mp4 gets. Animated WebP decode is far lighter. So the 29 KB AVIF that beats
a 200 KB WebP on disk can be *heavier to play* than the WebP it replaced — a
real cost to weigh against the size win, not a disqualifier.

This is observed, not just predicted. The repo owner watched the committed
animated AVIF play back with visible slowness, worse in macOS Preview than in
Chrome — i.e. the same file decodes at different costs in different decoders, and
the cost is high enough to see. Decode load scales with the viewer's machine, so
a weak or busy one will drop frames on the AVIF while the WebP plays smoothly.
One machine, two decoders — directional and consistent with the architecture,
not a mapped threshold. It is exactly the axis the size measurement was blind to:
bytes-on-disk and decode-cost-at-playback are different costs, and optimizing the
first said nothing about the second.

**The decode lever is resolution, not the encoder.** Because the player
software-decodes every AV1 frame live, the decode budget is
`width x height x fps` — pixels per second the viewer's machine must sustain. So
dropping the resolution buys smoothness directly: 1280→960 cuts the budget ~44%
(28 → 15.5 Mpx/s), and GitHub renders README images at well under native width
anyway, so the drop is invisible where it matters. A lower-resolution AVIF was
observed playing smoothly where a wider one stuttered — but on a capable machine.
**Whether any resolution stays smooth on genuinely low-end hardware is the open
question, not a settled result** — a real unknown to weigh when choosing
between a controlled-resolution AVIF and WebP.

Prefer cutting **resolution over frame rate**. On a moving-camera piece the fps
carries the motion cadence, and lowering it reintroduces judder — a different
defect than the decode stutter you were fixing. The command's `[width]` argument
is the lever; the default 720 is deliberately conservative on decode. The
encoder `-s` knob does **not** help — it trades encode time for file size and
leaves the bitstream's pixel throughput, which is what costs decode, unchanged.

There is a clean symmetry here: an AVIF software-decodes and an mp4
hardware-decodes, which is the same split that makes the mp4 play smoothly
everywhere *and* refuse to embed. Resolution is a playback cost for AVIF exactly
because it never touches the hardware path.

So this is a genuine tradeoff between two peer options, decided by context —
neither is the default:

- **WebP** — larger on disk (ruinous on a moving camera), but decodes cheaply
  and smoothly on any hardware, and its inline rendering on GitHub is the
  verified case. A reasonable pick when the audience hardware is unknown or
  weak, or when a moving camera isn't in play.
- **AVIF** — dramatically smaller on disk, lifts the held-camera constraint, and
  its decode cost is tunable by resolution (above). What is *not* yet confirmed
  is whether a controlled resolution stays smooth on genuinely low-end
  hardware — that test is still open. A reasonable pick when size or bandwidth
  matters most and the audience skews toward capable hardware; watch it on a
  low-end target in the browser you will embed for before relying on it there.

Holding the camera to fit a WebP loop under the 10MB inline cap is still a real
constraint if you ship WebP. AVIF removes it — at the playback cost above.

`loop` needs `img2webp` (`brew install webp`). Homebrew's ffmpeg ships without
libwebp, so `-c:v libwebp` fails with "Encoder not found".

## Encoding AVIF

```bash
bun run build.js avif <scene.html> [fps] [width]   # <name>.avif — defaults fps 12, width 720, same shape as loop
```

Under the hood: `avifenc --fps <fps> -q 60 -s 6`. Speed 6 is the measured knee
— `-s 8` gave 2.3x larger files for one second less encode time, `-s 4` gave no
further size gain for double the time. Encode cost is 11s for 288 frames,
negligible against a 65s shoot.

Visual check: decoded frames inspected by eye — crisp text, smooth gradients,
no blocking — and SSIM 0.97 against the source frames.

`avif` needs `avifenc` (macOS: `brew install libavif`), the exact parallel of
`img2webp` for `loop`.

## Why WebP (and, provisionally, AVIF) embed and mp4 does not

It is a content-type allowlist, not a markdown-syntax problem. Verified by
fetching from the URL a repo-relative reference resolves to:

| committed file | `raw` Content-Type | result |
|---|---|---|
| `.webp` | `image/webp` | renders inline; `ANIM`/`ANMF` chunks arrive intact |
| `.avif` (still) | `image/avif`, nosniff present but irrelevant since the type is correct | same allowlist mechanism as WebP, confirmed by fetch |
| `.mp4` | `text/plain; charset=utf-8` + `nosniff` | inert — no browser will treat it as media |

`<video>` being stripped from GFM is a second, independent block on the mp4 path.
Both have to be true for the workaround (an issue/PR attachment URL) to be the
only route to a player.

**The `.avif` row in THIS table was fetched as a still image.** Not the AVIF row
in the size table further up — those files are animated, verified at 132 and 288
frames with `avifdec --info`. The distinction matters because only one half of
the AVIF delivery path is actually confirmed:

| link in the chain | status |
|---|---|
| AVIF encodes small enough to ship inline | **measured** — 0.28 MB moving-camera, 0.029 MB held |
| the files are genuinely animated, not collapsed stills | **verified** — `avifdec --info` reports 132/288 frames, infinite repeat |
| GitHub serves `.avif` as `image/avif`, passing the allowlist | **verified by fetch** — but against a *still* |
| GitHub's image pipeline passes an *animated* AVIF through and it plays | **one real-world observation** |

That last row is the whole of the evidence: the repo owner committed an animated
AVIF and reported it renders and animates inline. Record it as exactly that — a
single confirming observation, not a bracket, and not the same class of evidence
as the fetch that backs the row above it.

An animated `.avif` is now committed beside the example specifically so this is
cheap to close: pointing the README's image at it is a one-line change, and
viewing the rendered README settles the last row either way. It is committed as
a peer delivery option and as the experiment that would settle the AVIF-inline
question — the README currently points its hero image at the WebP, the case
with real verification behind it; re-pointing it at the AVIF and writing down
what happens is the open follow-up.

Two traps that follow, plus one browser-support caveat:

- **Never track the loop under Git LFS.** `raw` returns the pointer file rather
  than the image and the README shows a broken image. This catches most repos
  that ship demo media.
- **Animated GIF, WebP and AVIF are all silent.** There is no format that gives
  inline motion *with audio* in a README. Audio requires the attachment player,
  which means the narration path and the inline path are different artifacts.
- **Animated AVIF is expensive to decode; WebP is not.** See "The size win
  costs decode at playback" above — this is a viewer-hardware cost, observed,
  and a real input to weigh against AVIF's size win.
- **Animated AVIF needs a newer browser than animated WebP.** Where the
  audience's browser is old or unknown, that argues for WebP; its numbers, and
  the fact that it renders and animates inline, are the well-verified ones in
  this file.

APNG is unverified — the issue-composer upload rejects `.apng`, and whether a
committed `.png` carrying APNG frames animates is undocumented. Do not rely on it
without testing.
