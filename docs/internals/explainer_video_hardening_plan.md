last updated: 2026-07-22

# explainer-video: hardening plan

What the batched test run found, grouped by root cause, and what to do about it.

Companion to [explainer_video_test_cases.md](explainer_video_test_cases.md)
(the exercise sheet and per-case outcomes) and
[explainer_video_generalization_plan.md](explainer_video_generalization_plan.md)
(the arc). This document is the **remediation**: eleven films built by seven
agents plus two built in the main loop produced ~51 distinct findings, and they
collapse into two root causes.

---

## The diagnosis

### Root cause 1 — instruments that generalise from a single sample

Every measuring device in the pipeline samples **one point** and then reports
about a whole film. One timestamp. One viewport. One scratch directory. One
renderer. One text layer. Whole-frame statistics standing in for "what moved".

The sharpest proof came from three controls on one scene:

| control | scene | `smoke.js` says |
|---|---|---|
| stateful, rotor visibly moving at t=1.0 | non-deterministic | **FAIL** (correct) |
| same bug, diagram fades in during the title | non-deterministic | passes the determinism check; fails by luck on a **9-byte, 0.16% margin** |
| same bug, faint structure drawn from t=0 (an ordinary design choice) | non-deterministic | **`all scenes pass`, 0 warnings** |

`smoke.js:147` is `const t = Math.min(1, dur / 3)`, which for any film ≥3s is the
**constant 1.0s** — inside the title card the workflow tells you to write first.
t=1.0 was the only timestamp in that film where the scene was clean, and it is
the only one the check looks at. **The skill's central guarantee can report green
on a scene that provably violates it.**

The same shape, everywhere: the framing lint (fixed and re-bracketed mid-run) had
it; the contact sheet's fixed fraction lands inside world-cut flashes and inside
lightning, blinding exactly the highest-risk beats; `motion`'s per-beat **mean**
is invariant to distribution, so a 0.73s end-of-beat freeze moved it by 0.00;
five independent agents hit fixed scratch directories, worst case encoding
**3 frames from one film and 70 from another** with no warning.

### Root cause 2 — vocabulary that promises more than it measures

Names that mean something narrower than they say:

- **`h`** is documented as the subject's height. It must mean *the extent that has
  to stay in frame*. Three independent films cropped their own payoff — a robot's
  antenna, a cross-section slab, a pelican's umbrella.
- **`w`** (added in 0.17.0) is an axis-aligned world-X scalar the solver never
  rotates. Measured: same rung, same declared size, varying only `angle` — 0°
  fits, −26° **clips at the frame edge**, −45° fits. Non-monotonic, because it is
  the projected extent of a 3D box.
- **`SIZES`** has a vertical anchor and no horizontal one, in *both* backends. An
  agent ported the ladder to 2D and used **one of its seven rungs**, because the
  rungs carry human-figure meanings (waist-up, chest-up) with no referent for a
  region, and once a subject is a bounding box "fit this box" is the only op.
- **`cut:'whip'`** differs from `blend` only in duration. There is no motion blur,
  so it reads as a fast snap with a stutter. The word promises what the renderer
  cannot deliver.
- **`focus`** is one of six documented shot properties and does nothing in the
  base template, which has no `BokehPass`.
- **a bible swap** is "one line" only for scenes that never author an emissive:
  emissive intensity lives in `animate()`, and the bible layer has no gain.
- **`solveShot`** has no clamps at all — it will place the camera *inside* the
  subject (measured: 2.79 units from a head on a body extending 3.7 units back)
  or *below the ground plane*.

---

## The rule that keeps this open-ended

The point of this skill is that a user can ask for *any* scene — any subject, any
character, any register. Hardening must not narrow that. So every change here
obeys one rule:

> **A fix may make an instrument honest, or let an author say something they
> already meant. It may not add a required shape to a scene.**

Operationally: every new field is **optional, defaulting to today's behaviour**;
every new primitive is a **pure function of `t`** that composes with the existing
kit; no fix introduces a content template, a mandatory beat, or a required
structure. Where a finding could be answered either by a feature or by a
constraint, prefer the feature — a constraint spends the user's freedom, and
this skill's whole thesis is that only geometry and caption register change by
domain.

---

## How to read the fixes below

The temptation with 51 findings is 51 patches. Most of them are one class wearing
different clothes, so each group below leads with the **structural** change that
removes the class, and then names the few places where a **bandaid is genuinely
the right answer** — because sometimes it is, and pretending otherwise is its own
kind of over-engineering.

A useful test: *if a new check, a new command, or a new scene were added
tomorrow, would it get this right for free?* If yes, the fix is structural. If it
would have to remember, it is a bandaid and should be labelled one.

---

## Group 1 — Instrument integrity

### Structural: the harness has no shared notion of "how to sample a film"

Every check hand-rolls its own sampling, which is why the same defect appears
independently in the determinism check, the blank check, the contact sheet, and
(until mid-run) the framing lint. The fix is not "sample three timestamps in the
determinism check" — that is the 1-of-N patch, and the next check written will
have the bug again.

Add a **sampling layer** that every instrument draws from. It knows what the
harness already knows and no individual check does: the beat table, the flash
windows, the duration, and where the motion peaks are.

```
plan = samplePlan(scene, {mode: 'uniform'|'beats'|'peaks', n, avoid: 'flash'})
```

- `uniform` — n fractions across DURATION (what exposure already does by hand)
- `beats` — one per beat at a given fraction (what `sheet` does by hand)
- `peaks` — where per-beat frame delta is maximal, which is the only mode that
  can see a 0.5s jump inside a 2.0s beat. `motion` already computes the numbers.
- `avoid: 'flash'` — nudges off any `CONFIG.flashes` window, which is what blinds
  the highest-risk beats of any two-world film

Two properties matter as much as the modes:

1. **Every check states its plan and prints the samples it used.** A green result
   becomes auditable instead of authoritative. The three-control proof above was
   only possible because someone went looking for *which* timestamp was checked.
2. **A check declares `all` or `any`.** Determinism is `all`. Blankness is `all`.
   "Something legible happens" is `any`. Today every check is implicitly `any`
   with n=1, which is the weakest possible claim stated as the strongest.

Consequence: `build.js kinematics` (the state-space probe) is then a *new
consumer of the same layer*, not another bespoke sampler. It is worth building on
its own merits — bracketed at boundary/interior **1.0001 vs 0.0531** and spread
**1.003x vs 72.7x** on scenes `motion` called indistinguishable — but the point
here is that it inherits correct sampling for free.

### Structural: runs are not isolated, and nothing verifies provenance

Five agents hit fixed scratch directories independently; the worst case encoded
**3 frames from one film and 70 from another** silently. Suffixing each of the
six hardcoded names with a pid is the bandaid, and it is the wrong shape: the
seventh command someone adds will hardcode a seventh name.

Instead: **one `workspace(scene, tag)` helper that every command must go through
to get scratch space**, plus a **provenance assertion** — the frames a command
reads must be the frames it wrote (count against `fps × DURATION`, and a manifest
written at capture time). The assertion is the part that generalises: it catches
*any* future desync, not just the concurrent one, including the stale-tail class
`build.js` already carries three comments about.

### Genuine bandaids here, and they are fine

- **A ≥99% near-black frame becomes a failure, not an advisory.** This really is
  just a threshold moved from "warn" to "fail". There is no class behind it — a
  black frame is never a design, and the only reason it needs saying is that a
  342-frame all-black render currently reports `all scenes pass`.
- **GL backend selectable, hardware default.** One flag, currently hardcoded.
- **`shoot.js` runs `ensureVendor` and honours `FRAMES_DIR`.** Two lines bringing
  one tool in line with its sibling. (Though note *why* it drifted: `build.js`
  grew the self-healing and `shoot.js` was never revisited — an argument for the
  workspace helper above being the single door.)

---

## Group 2 — Framing that measures what it promises

### Structural: declarations are never checked against the thing they describe

Three films cropped their own payoff — a robot's antenna, a cross-section slab, a
pelican's umbrella. The bandaid is a doc line saying "remember to include props
in `h`". It will not work; it did not work, and the docs already say `h` is the
subject's height, which is exactly the misleading part.

The structural fix is that **the tool measures what the author declared**. At load,
walk the named object's scene-graph bounding box and compare it to the declared
extent. Under-declaration throws; over-declaration warns. An author then cannot
declare `h:7.8` for a bot that is 9.6 tall to the antenna, because the antenna is
in the box.

This is the same move that made the match-cut constraint trustworthy — a rule
with an enforcement mechanism stayed true, and every rule that shipped as prose
drifted. It also subsumes several separate findings at once: the wide-subject
crop, the "ladder silently becomes fraction-of-width" surprise, and the
camera-inside-the-subject case, because all three are the solver reasoning from a
number nobody verified.

With extents honest, the solver can then do the thing it always claimed:

- fit the **projected** box (rotate by `angle`/`elev`) rather than an
  axis-aligned scalar — the current `w` is non-monotonic in angle, measured
  fitting at 0° and −45° and **clipping at −26°**
- derive clamps *from the extent itself* — never inside the subject, never below
  the floor — rather than the two hand-added magic numbers two agents wrote
  independently
- accept `subject: ['plank','hammer']` and solve the union, because every causal
  beat is two objects and the space between them

### Genuine bandaids here

- **A rung between `WS` (.50) and `FS` (.95).** A missing table entry. "Full body
  with a little air" is the workhorse framing of a character film.
- **A horizontal anchor** alongside the vertical one. A missing field.

Both are honestly just gaps, and neither has a class behind it.

### Deliberately NOT fixed structurally: the rung names

`MS`/`MCU`/`CU` carry human-figure meanings with no referent for a region, which
is why an agent ported the ladder and used one of seven rungs. The structural fix
would be a second ladder for regions — and that is a vocabulary the films have
not asked for. Documented as a limitation instead. This one is a bandaid *on
purpose*.

---

## Group 3 — The kit has beat-addressing and no time-shaping

### Structural: the missing half of the kernel

`ramp`/`pulse`/`rampS`/`during` all answer **"where am I inside this beat?"**.
Nothing answers **"how does time itself run here?"** — and four separate findings
are all that gap:

| finding | what the author wanted to say |
|---|---|
| chain reactions run backwards | "start when *that* finished, and stay" |
| no slow-motion | "run this stretch at quarter speed" |
| loops hard-cut every cycle | "make this term periodic over DURATION" |
| holds need hand-integration | "coast, then hold, then coast" |

These are one idea: **build a monotone (or periodic) reparameterisation of `t`,
then evaluate closed forms through it.** Add them as a small, composable time
algebra in the kernel — `latch`, `warp`, `cyc`, `progress` — all pure functions
of `t`, all obeying the prime directive, none constraining content.

The chain-reaction finding is why this is structural rather than four utilities:
taking "drive B from A's expression" literally on an *impulsive* coupling
produces a **reversible chain** — a hammer's ringdown retracted the driver by 54%
of a contact width and an entire fallen domino row stood back up. Derivation
propagates **onset**, not **persistence**, and `latch` is the primitive that
expresses the difference. Without it the docs give advice that is wrong for half
the cases it covers.

### Structural: make the text helper good enough that turning text off is possible

Two findings look unrelated and are not: `label()` is unusable for real
typography (centre-align only, no weight, no measure — every 2D film replaced it
within minutes), and the semantics test cannot see canvas text (only 2 of 8 beats
in the external-doc film survived a strict cover-*all*-text pass).

Fix them together. Ship a text helper worth using (`txt()` with align/weight/
measure, which the blueprint pack already assumes exists), and then a
`?strip=text` mode the template honours by skipping every draw that goes through
it. The instrument for the semantics axis falls out of making the helper good —
and it only works *because* everyone uses the helper.

### Genuine bandaids here

- **Flash width as a parameter.** Hardcoded ±0.25s; one film's whole beat was
  shorter than the shortest expressible flash. A missing argument.
- **`rampE()` returning `{u, e}`.** Three agents gated on an eased value having
  read the warning not to. Making the correct path the easy path is a one-function
  bandaid, and the right one — the alternative is a louder warning, which is what
  already failed.
- **World-anchored DOM labels.** Genuinely additive; two films shipped unlabelled
  because a world→screen projection would have to be hand-rolled identically by
  every author.

---

## Group 4 — The method describes a narrower world than the tool serves

Mostly documentation, and mostly *restatement* rather than addition — the
findings show the existing rules are right about explainers and stated as
universals.

- **Semantics**: "cover the caption" is undefined with no caption, removes the
  film when text is the subject, and becomes "is it funny" for a gag. Restate as
  **"cover everything except the geometry"**, with the `?strip=text` instrument
  above making it a standing pass.
- **Pacing**: the ~3s floor derives from *mechanism comprehension*. A gag beat
  carries a single-token state change; four beats under 2s read fine. And the
  converse is undocumented — a domino falls in 0.30s while beats want 3-4s, so
  **physical durations fight beat durations**, and the docs only cover the
  opposite case ("transit eats the content window").
- **Dead air is structural** in comedy (a comic rest is by construction longer
  than the minimum and below the floor) and in fine-line registers.
- **`style-3d.md` corrections**: the SwiftShader failure is not "PMREM is
  broken" — PMREM works for LDR and HDR; only `Sky` into a **half-float** target
  fails, it poisons *direct* lighting on every `MeshStandardMaterial`, and a
  fallback verified equal across backends to 0.2% exists. Bloom threshold should
  read "above the **sky-lit** luminance of your brightest material". The
  no-env-map fallback holds for semi-rough metal, not metalness ~1.
- **Caption facts that are load-bearing and undocumented**: the pill's top edge
  at ~0.883 of frame height is a binding layout constraint; a `blend` cut makes
  the caption **lead the picture by up to 0.65s**; `#cap` is `nowrap`, single
  line, with nowhere to put a legend.

## Group 5 — Ergonomics (bandaids, all of them, and that is correct)

ffmpeg banners off stdout; `shoot.js` progress to stderr; the oversize warning
acts rather than printing a command; 2D shadow/bloom unit traps documented with a
`camAt(t)` accessor so screen-constant quantities are expressible. None of these
has a class behind it; they are friction, and friction is fixed one piece at a
time.

---

## What we deliberately do NOT build

Keeping faith with the earn-in discipline, and with the open-endedness rule:

- **No 2D shot solver.** The film that was built to want one concluded the
  `{x,y,zoom}` rail was expressively sufficient; it earns three small things
  instead (seconds-anchored keyframes, an exposed `camAt(t)`, a documented hold
  idiom). Porting the ladder would buy least and cost most.
- **No register-aware lint engine.** Two candidate instances exist; no film has
  been *blocked*. Revisit when one is.
- **No content templates, scene presets, or genre scaffolds.** This is the line
  that protects "any scene you want".
- **No motion blur** for `whip` — instead, stop promising it: rename or document
  it as a fast cut until a film pays for the sub-sample pass.

---

## Addendum — what the two-character scene taught (2026-07-22)

Pass three shipped, then a fight scene between two existing characters was built
as an end-to-end exercise. It confirmed the plan's central bet and added one
finding the eleven earlier films had produced without anyone naming it.

**The earn-in rule worked, in both directions.** `warp` was deferred in pass
three as "no film is blocked on it" — every film that wanted slow motion had
shipped without it. One scene later a film genuinely needed it, and it shipped
then. That is the rule functioning, not an exception to it. Conversely, this
scene did **not** earn a `build.js contact` checker (below), and it did not get
one.

**A fourth root cause, hiding in plain sight: contact points are never
declared.** Four films had already hit this and each was written off as a
one-off — a payload dot arriving at empty space, a hammer head hanging clear of
its plank, a domino sweeping between the paddles, a body descending offset from
the gate that opened it. The fight made it a pattern: **`h`/`w` describe the
FRAMING extent, and the interaction point is a different number that nothing
records.** Authors reach for the number that is written down.

This is the same shape as root cause 2 — *vocabulary that promises more than it
measures* — one level further in. `h` was corrected from "the subject's height"
to "the extent that must stay in frame"; it still says nothing about where the
thing actually touches. Resolved by documentation plus the measurement technique
(`Box3` through `page.evaluate`, the same probe the cross-section film used),
**not** by an instrument: four films hit it and none was *blocked*.

**One process failure worth recording against myself.** Five rounds were spent
tuning multipliers before anything was measured, and each round made the scene
worse. The fix took minutes once the offsets were read. This is precisely the
"iterate by looking, not by hoping" failure `method.md` documents — committed by
the author of the pass that added the measuring instruments, in the same
session. The lesson is not "measure more"; it is that **the pull toward tuning a
coefficient is strongest exactly when a thing is nearly right**, and that is the
moment to stop and instrument.

**Still open on that scene:** geometric contact is not legible contact. Both
blows now overlap on all three axes and still read as clipping rather than
impact, because the contact point sits behind a body. The rule is written down
(`method.md`); the scene has not been re-staged.

## Sequencing

1. **Group 1 first**, because every subsequent measurement depends on it, and
   because two of its items (single-sample determinism, black-frame-as-advisory)
   are the two ways this pipeline can currently ship something broken while
   reporting success.
2. **Group 2**, verified against the three films that cropped their own payoff.
3. **Group 3**, each primitive landed with the control that motivated it.
4. **Group 4/5** docs, harvested last so they describe what actually shipped.

**Verification standard for the whole plan:** re-run every committed example plus
the test films from clean, isolated directories — the concurrency defect means
several of this run's own motion numbers cannot be trusted as measured, and the
re-run is the control on the fix.
