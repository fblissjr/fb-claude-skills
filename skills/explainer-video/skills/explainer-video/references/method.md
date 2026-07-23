# Method: designing a sequence that reads

The backend-agnostic core: the three failure axes, the beats discipline, the
controls discipline, continuity and semantics review, and the determinism
rules. Everything here holds for any scene that implements the window
contract, whatever renders the pixels.

Two companion references hold what this file deliberately does not:

- `style-3d.md` — the three.js cookbook: lighting, the camera rail, texture
  labels, procedural-asset recipes, r185 API notes, the performance envelope.
- `delivery.md` — the GitHub delivery forensics: format tradeoffs, encoder
  settings, the content-type mechanism and its evidence chain.

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
- The wash rule was stated as universal law for months. Rendering one
  dark-palette scene refuted it. See `style-3d.md`, "Lighting and colour".
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

The rules here are about frames and framing, whatever draws them. The
renderer-specific halves of this axis — lighting and colour, texture labels,
camera lens choices, and the procedural-asset cookbook — live in
`style-3d.md`.

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

# Framing rules (breaking these breaks video/HTML parity too)

Determinism makes the HTML and the render agree about *when*. It does nothing
to make them agree about *what is in frame*. The render is always 1920x1080;
the HTML is whatever shape the reader's window is.

This shipped as a real defect and was invisible to the entire test surface,
because **no tool in the chain ever opens a non-16:9 viewport** — `shoot.js`
pins 1920x1080, `smoke.js` uses 640x360 and 1920x1080, `build.js` opens no
browser at all. Only a human resizing a window could see it. Measured on a
fixed world point at `(3,3,0)` in the 3D template, projected at four window
shapes: `ndc.x` went **0.913 → 1.161** (off-frame) from aspect 1.78 → 1.40,
while `ndc.y` held constant to four decimals. Vertical framing was exactly
aspect-invariant; horizontal was not. On the shipped `toybot-walk`, that cut
the sign out of the rack-focus shot at 1.40 — the exact failure that scene's
own comment ("both subjects must be visible") was written to prevent.

The fix is architectural, not a patch. An audit found **ten different implicit
reference frames** in the pipeline — the canvas scaled by window height, the
shot ladder by frame height, captions sized in fixed CSS px against the window
but positioned as a percentage of it, `smoke.js` measuring exposure at 640x360
and caption overflow at a hardcoded 1920, `motion`'s dead-air threshold against
a global median. Several disagreed. Every defect found in that audit came from
the same shape: **a measurement or a composition made against a frame nobody
declared.**

So one frame is now declared, in the scene, and everything resolves against it:

```js
const FRAME = { aspect: 16/9, px: [1920, 1080] };   // exported as window.FRAME
```

`shoot.js` sizes its viewport from `FRAME.px`; `smoke.js` measures overlay fit
against `FRAME.aspect`; the templates compose against it; the DOM overlays are
sized and positioned from CSS vars carrying the frame rect, so a caption is a
fraction of the frame rather than a fixed number of window pixels. That last
one is a **separate** parity gap the containment fix alone did not close.

It also makes non-16:9 output first-class: `{aspect: 9/16, px: [1080,1920]}` is
the entire edit for a vertical film. Note honestly that shot-size conventions
are aspect-dependent — a WS does not frame the same composition in vertical as
in landscape — so the ladder needs re-judging by eye, not merely re-running.

Both templates therefore compose against the declared **design frame** and
*contain* it:

- **2D** scales by `Math.min(canvas.width/VIEW_W, canvas.height/VIEW_H)` rather
  than by height alone.
- **3D** widens the vertical fov when the window is narrower than the design
  ratio, while the shot solver keeps using the **authored** lens for framing
  distance. That split is what makes it contain rather than merely zoom out.

Both are the identity at the design aspect, so every recorded frame is
byte-identical (verified across all shipped scenes at two timestamps). The
overlay change is not — it measures PSNR 79.0 dB (3D) / 74.0 dB (2D), above
this file's 70 dB imperceptible bar, with the difference localized to the
caption pill's antialiased edge.

**The guard.** `smoke.js` now samples the design frame at three window shapes
across three timestamps and fails if its contents change. Bracketed both ways:
known-bad pre-fix templates score 24-31 mean absolute luma difference, correct
scenes score 0.07-0.12, and the threshold sits at 8 in the gap. Two false
starts are worth knowing, because both produced a confident all-clear:

- The first version sampled a **single `t`** which landed on a near-blank title
  card, scored ~0 on a template known to crop, and passed. A blank frame is
  invariant under every window shape precisely because it contains nothing.
- The second read a **stale canvas**, sampling before the scene's own resize
  handler had run — which scored a correctly-fixed template *worse* than a
  broken one. Same class as the `smoke.js` sampling race already recorded in
  the generalization plan's postmortem. Any check that changes viewport must
  re-settle before it measures.

The lint is the floor, not the verdict: it can reject a scene, it cannot
approve one, and the render is always the design shape so it can never show you
this. `build.js aspect <scene> <t>` tiles one moment at four window shapes for
the looking half.

Three consequences to design around:

- The size ladder's `f` is a fraction of the **design frame** height, not the
  window's. The ladder constrains height and says nothing about width — which
  is why a subject wider than ~1.8x its declared height crops at `FS` and
  tighter regardless of window shape. Push in on a narrower named sub-subject
  rather than inflating `h`.
- A narrow window reveals world **above and below** the design frame, so
  **never hide an element by parking it off-frame.** Gate it with scale or
  opacity instead.
- Captions are fixed CSS px, so they size against the *window*, not the frame.
  That is a separate, still-open parity gap: `smoke.js` measures caption
  overflow at 1920 wide, so a caption can pass there and still clip in a
  1280-wide window.

The alternative that preserves the authored lens exactly is scissor-letterbox
(`renderer.setViewport`/`setScissor` into the largest 16:9 rect). It gives
pixel-exact composition parity at every window shape, at the cost of visible
bars and re-anchoring the DOM overlays. Contain is the default because it never
shows bars; reach for letterbox when the HTML must be a faithful preview of the
video.

# Determinism rules (breaking these breaks video/HTML parity)

- All randomness from the seeded pool `R[]`, indexed, never re-drawn.
- No `Date.now()`, no `performance.now()` outside the preview driver, no state
  accumulated across frames — `seekTo(8)` after `seekTo(2)` must equal
  `seekTo(8)` cold.
- Shared materials are state. Restate colour and intensity from a constant every
  frame; never adjust them incrementally. See the next section.
- `renderer.setPixelRatio(1)` and `preserveDrawingBuffer: true` — screenshots
  need both.
- Physics is faked with closed forms: a drop is `y0 - k*(t-t0)²`, a wobble is
  `sin(t*ω) * ramp`, a screw-in is position + rotation both driven by the same
  ss() ramp.

## Mutating a shared material is pure only if you restate it

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
for on a shared material: assign it outright every frame, never adjust it. The
principle is backend-agnostic — any shared object a frame mutates (a canvas
context's state, a DOM node's style) must be restated from constants, never
nudged from its previous value.

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
