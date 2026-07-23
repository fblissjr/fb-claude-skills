last updated: 2026-07-23

# physics bake proposal (screenwright Phase 4, owner-prioritized)

The owner's direction, given 2026-07-23 during the bear-and-bees session:
relax screenwright's determinism *at authoring time* — "simulated
creativity without an LLM" — while keeping runtime playback pure. Of the
three tiers discussed (bake-time sim / seeded runtime sim / true
nondeterminism), **the owner chose tier 1: bake-time simulation**, which is
the founding plan's Phase 4 shape. Phase 4 therefore moves ahead of Phase 3
(the human face rig) in priority, starting after `bear-and-bees` ships.

This document exists so the next session inherits the constraints and the
eval criteria, not just the enthusiasm. The specific failure it guards
against, named by the owner: tier 1 quietly becoming tier 2 becoming tier 3
across sessions, each step looking like a small relaxation of the last.

## The invariant that does not move

**The shipped scene file remains a pure function of `t` at runtime.** No
simulator executes at playback. The bake step runs a physics engine ONCE at
build time, samples the result, and writes the samples into the scene as
data. Playback interpolates that data with closed forms — a baked track is
just another pure signal, like `ramp()` or the frozen `R[]` pool.

Everything the current verification stack relies on survives unchanged:
`seekTo` stays random-access (no replay), HTML/MP4 parity holds, smoke's
determinism check, the strip/sheet instruments, and byte-identical
pre/post comparisons all keep working with zero modification.

## Red lines (tier drift, requires explicit owner sign-off)

Any change that does one of the following is NOT tier 1, whatever it is
called in the moment:

1. Playback steps a simulator (even a "small" one, even fixed-timestep).
2. Any state carried across frames at runtime.
3. `smoke.js`'s determinism or seek-purity checks are weakened, special-
   cased, or given a per-scene opt-out "to accommodate the sim".
4. Wall-clock time or unseeded randomness anywhere in the pipeline.

Tier 2 (seeded runtime simulation, seek-as-replay) is a legitimate future
direction but it is a SEPARATE proposal with its own instrument redesign —
smoke's seek-twice-compare and the strip re-shoots both assume random
access. It is not an incremental relaxation of this one, and the owner has
not asked for it.

## Shape of the bake step

- `bake <scene>` as a build.js command (or sibling script): reads a
  declarative sim block from the scene (bodies, colliders, impulses),
  runs Rapier (exact version pinned) at a fixed timestep with
  `CONFIG.seed`, and splices the sampled trajectories into the scene file
  as a data block — the same one-file discipline as the vendored three
  bundle. The scene stays self-contained.
- Sim inputs are scene data next to BEATS, and impulses anchor to beats
  (`{beat:'hit', at:.3, impulse:[...]}`), so retiming a beat re-bakes
  cleanly instead of silently desynchronizing.
- Playback: per-object keyframe tracks, interpolated in closed form.
  Baked objects and closed-form objects mix freely in one scene; baked
  tracks drive transforms through the same restate-every-frame rule.
- v1 scope: rigid bodies and props. Characters stay closed-form (IK/gait
  on top of, or independent of, baked roots). No baked joints, no cloth,
  no fluids in v1.

## Eval criteria (measured, per method.md — no vibes)

1. **Re-bake determinism:** same seed + same inputs → byte-identical bake
   block, verified by a `bake --verify` that re-runs and diffs. This is
   the plan's own Phase 4 gate. Cross-MACHINE bake identity is an open
   question (Rapier is WASM; determinism claims need measuring, not
   trusting) — if it fails, the bake block is committed data and playback
   is unaffected; only re-bake reproducibility varies, and that gets
   documented honestly.
2. **Runtime gates unchanged:** smoke green on both backends with the
   UNTOUCHED checks; seek purity holds (`seekTo(8)` cold ==
   after `seekTo(2)`).
3. **Size bracket:** measure bake-block size on the gate film at 2-3
   sample rates before choosing one; the block should stay well under the
   1.09MB vendor bundle or the one-file discipline starts to hurt.
4. **The control (method.md's core rule):** author one beat both ways —
   closed-form fake vs baked — and confirm the baked version either reads
   better or authors dramatically cheaper. If it does neither, the
   machinery is decorative and Phase 4 stops.
5. **The film gate:** `rube-goldberg` ships and passes all three review
   axes. Note: sim gives physically consistent contacts for free, but NOT
   legible ones — the "geometric contact is not legible contact" rule
   still applies to staging.

## Spike list (answer by measuring, before building the pipeline)

- Rapier version pin + WASM determinism: re-bake identity on this machine,
  then across a second environment if available.
- Sample rate bracket (size vs smoothness at 12/30/60Hz sampling).
- Embedding format (JSON floats vs base64 Float32Array) — measure both on
  a real bake.

## Tracking

- Decision + session-start reminder: memory
  (`project_relax_determinism_exploration.md`; the MEMORY.md flag demotes
  once raised).
- Phase priority note: `screenwright_plan.md` Phase 4.
- This document is the constraint reference; the plan stays the hub.
