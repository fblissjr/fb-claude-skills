# Instruments: what each check can and cannot see

Every check in this pipeline has a measured limit. This file is the ledger of
those limits, because the failure mode that costs the most is not a check that
fails — it is a check that **passes and should not have**.

`method.md` holds the method; this holds the instruments' brackets. Read it when
you are deciding whether a green result means anything.

## The rule these all serve

> **A proxy can reject. It cannot approve.**

A passing score in a region where the proxy has no authority means nothing, and
must not read as approval. Every threshold below is either bracketed by
observation on both sides, or explicitly labelled unbracketed.

---

## `smoke.js`

| check | quantifier | what it catches | what it cannot see |
|---|---|---|---|
| contract | — | a missing `seekTo`/`DURATION`/`stopPlayback`/`sceneReady` | — |
| determinism | **all** of 4 sampled points | state across frames, `Math.random()`, wall-clock | state that only desyncs at unsampled times |
| blank frame | **all** of 4 sampled points | a pipeline shooting empty frames | a frame that is dark but not empty |
| near-black | worst of 3 | a broken render (GL backend, post chain) | a legitimately dark register above 99% |
| kernel parity | file set | two scenes carrying different kits | drift inside a scene |
| solver parity | file set | two scenes carrying different solvers | — |
| framing invariance | 3 shapes × 3 times | a scene that crops instead of containing | composition quality at any single shape |
| caption speed / overflow | per beat | a caption too fast or too wide **for the frame** | canvas text; vertical collision |
| exposure | 3 times, worst | washed out or crushed | whether the register intended it |

**The determinism check was the sharpest lesson in this whole file.** It used to
sample `Math.min(1, dur/3)` — the constant 1.0s for any film over 3s, inside the
title card the workflow tells you to write first. Three controls on one scene:

| control | truth | verdict |
|---|---|---|
| stateful, rotor moving at t=1.0 | non-deterministic | **FAIL** (correct) |
| same bug, diagram fades in over the title | non-deterministic | determinism passed; failed by luck on a **9-byte margin** |
| same bug, faint structure drawn from t=0 | non-deterministic | **`all scenes pass`, 0 warnings** |

t=1.0 was the only timestamp in that film where the scene was clean. Quantifying
over a sample plan is why all three now fail. **When a check reports absence, ask
what a positive result would have looked like.**

## `build.js motion`

Reports per-beat motion energy and dead air. Its limits are measured, not
assumed:

- **It does not detect pops or stalls.** That was built and cut: a known 0.35 rad
  limb step measured **1.00x its own local baseline**, and a stall detector fired
  at *every* beat boundary on a known-good film.
- **It measures textured pixels, not motion.** A title beat with a real 14° camera
  orbit scored 0.54 because the frame is mostly flat sky; a comparable push over a
  detailed frame scored 3.09. Bars are **not comparable across beats of different
  texture density**.
- **It measures moving area, not significance.** A payoff beat where the whole
  argument resolves scored 0.23 against a neighbour's 8.23, because it is two
  small dots against a large block crossing frame.
- **The bar is normalised to the peak beat**, so one loud beat flattens every
  other into a single `#`.
- **The per-beat value is a mean**, so it is invariant to distribution: a 0.73s
  end-of-beat freeze moved it by 0.00.
- **Dead air is structural in some registers.** A comic rest is by construction
  longer than the minimum and below the floor; fine, low-contrast linework
  animates without registering at all. Both produce true-positive flags on
  correct films.

## `build.js strip`

Consecutive frames tiled — the only pixel-level look at continuity available to a
reviewer who cannot play the film. **Bracketed both ways**: a 1.2-unit whole-body
jump (~15% of frame height) is obvious between adjacent cells; a 0.35 rad limb
rotation (~2% of frame area) is invisible. So it reaches world- and object-level
breaks and stops short of limb-level ones, and it does better on a held camera.

It is the one instrument that caught a whole-mechanism stall a full render of
`motion` called indistinguishable — beads visibly frozen across nine cells.

## `build.js sheet`

One frame per beat, plus a `.squint.jpg` silhouette strip.

- **Its fixed fraction is a blind spot.** At 0.6 it misses effects that park; the
  0.95 end-of-beat pass exists for that and is a standing step. But **both** land
  inside a `CONFIG.flashes` window on the beats that bracket a world cut — the
  highest-risk moments in a two-world film — and inside any bright in-scene
  effect. A defect duly hid there.
- **It cannot see a short physical event.** A 0.5s jump inside a 2.0s beat is
  invisible at 0.6 and at 0.95.
- Tiled beats are what reveal a *systematic* error; the same mistake in six shots
  reads as six small problems one at a time and as one bad formula when tiled.

## `build.js aspect`

Tiles one moment at four window shapes. Complements the framing-invariance lint:
the lint can **reject** a scene whose design frame changes with the window, and
cannot **approve** one — and the render is always the design shape, so it can
never show you this. Read the cells; every one must be the same composition.

Caveat: cells are padded into a common square box, so four window shapes render
at four scales. A correctly contained subject can *look* like it drifts. When in
doubt read the individual frames rather than the sheet.

## What has no instrument

Recorded honestly, because these are where films actually ship broken:

- **Watching the loop at speed.** The strongest continuity instrument, and it
  needs a human. No agent can do it.
- **Semantics.** "Cover everything except the geometry" is a question you ask
  yourself. The `?nocap` switch removes the DOM caption; it does **not** remove
  canvas text, which is where a diagrammatic film's meaning actually lives — in
  one external-doc film only 2 of 8 beats survived a strict cover-*all*-text pass.
- **Whether a beat is funny, warm, or tense.** No still answers it.
- **Cross-machine reproducibility.** `seekTo` purity is a property *within* a
  renderer. Frames are not byte-identical across GL backends (measured PSNR
  57–58 dB, differences confined to antialiased edges and speculars), so a
  byte-comparison regression must fix the backend on both sides.
