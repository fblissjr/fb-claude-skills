# The character scaffold

One parametric skeleton family. A character is a **point in proportion
space** plus a **material choice** — never a shipped mascot, never a fetched
asset. The kit lives in `templates/scene.character.template.html` inside the
`CHARACTER` parity fence; copy that template when a film has figures, the
plain 3D template when it does not (the block costs nothing when absent).

Doctrine, from the founding plan: scaffold-as-data, authored once, committed;
the skill must never grow a runtime asset-fetch path. Every kit function is a
pure function of its inputs — posing is closed-form (two-bone IK, distributed
chain bends), so `seekTo` purity is untouched. The IK and the plant-grid gait
are ports of the predecessor's proven walker, measured lessons and all.

## Conventions

Characters face **+X**. The sagittal plane is XY; z is lateral. Chains built
by the kit use: `rotation.z` = curl (sagittal), `rotation.x` = wag (lateral),
`rotation.y` = twist/turn.

## The API

| Call | What it does |
|---|---|
| `propDefaults()` | the full proportion vector with defaults — override per character |
| `buildCharacter(P, matFor)` | skeleton + lathed/capsule shells -> `rig`. `matFor(part)` supplies materials per `'torso'|'head'|'muzzle'|'limb'|'foot'|'tail'` — the seam where shading packs plug in |
| `solveLimb(limb, dx, dy)` | analytic two-bone IK, target relative to the limb's attach point |
| `gaitPose(rig, s, vAmp, opts)` | plant every planted limb from distance travelled `s`; returns the stride |
| `gaitBob(s, stride)` | the shared gait phase (`sin(pi*s/stride)`) for bob/lean/arm swing |
| `footTarget(s, phase, stride, swingH)` | the raw plant-grid cycle, if you need targets directly (hops) |
| `chainCurl(chain, rad, axis)` | distribute a total bend evenly across a chain (neck aim, tail lift) |
| `chainWave(chain, phase, amp, lag, axis)` | phase-lagged follow-through — procedural secondary motion, pure in its phase argument |

The `rig`: `root` (place/rotate the character; limbs attach here at fixed
frames), `body` (torso/neck/head/tail — bob and lean THIS, so cosmetic motion
never moves the IK attach frames and planted feet stay planted), `head`,
`neckChain`, `tailChain`, `limbs.{HL,HR,FL,FR}`, `planted`, and the framing
estimates `height` and `length` (nose-to-tail — use as the subject's `h`/`w`;
for quadrupeds declare `w` or the solver frames empty air).

## The proportion vector

See `propDefaults()` in the template for every field and its comment. The
constraints the kit enforces loudly (build-time throw, not silent
hyperextension): `hindUpper+hindLower > hipH`, and for quadrupeds
`foreUpper+foreLower > shoulder height` (which is
`hipH + cos(torsoTilt)*torsoLen`). Two more that bite visually, learned on
this template's first renders: `shoulderW/2` must clear `chestR` or hanging
arms embed in the torso; near-equal overlapping shell radii z-fight (the
torso is one lathed profile for exactly that reason).

Worked starting points (tune by looking, not by faith):

- **Biped (the template demo):** the defaults, plus
  `{tailLen:1.8, tailSegs:4, muzzle:.4}` for a creature register; drop the
  tail and muzzle for a human silhouette. `quadruped:false` hangs the
  forelimbs as arms (swing them from `gaitBob`, flex `mid.rotation.z`).
- **Quadruped (bear-shaped), verified building and walking:**
  `{quadruped:true, torsoTilt:80, hipH:1.85, torsoLen:2.4, pelvisR:.95,
  chestR:1.05, neckLen:.7, neckSegs:2, neckTilt:55, headR:.55, muzzle:.55,
  tailLen:.5, tailSegs:2, tailTilt:30, shoulderW:1.6, hipW:1.5,
  foreUpper:1.2, foreLower:1.15, foreR:.34, hindUpper:1.1, hindLower:1.05,
  hindR:.38, footLen:.65, footH:.22}`
- **A text-invented creature** is the same move: read the description,
  choose tilts/lengths/radii/segments, add scene-level features.

## Gait

Everything derives from **distance travelled `s`, never wall time** — feet
freeze mid-plant when the body stops. Drive `s` from a named closed form of
`t` (the demo's `walkerXAt`) that SUBJECTS also reads, so camera and body
cannot disagree. `vAmp` is the motion envelope (a `pulse` over the walk
beat): gaitPose blends to a staggered rest stance as it dies, or the last
cycle leaves feet mid-stride.

Phases are per-limb: biped `HL 0 / HR .5`; quadruped lateral-sequence walk
`HL 0, FL .25, HR .5, FR .75`. Each planted limb's plant column rides its own
attach x, which is what lets one grid serve a foreleg planting a
torso-length ahead. Verify planting the project's way: `build.js strip` over
a mid-walk window — a planted foot must hold its ground position across
cells while the body passes over it.

Hops are IK targets, not pose freezing (proven-walker lesson): bypass
gaitPose during airtime and call `solveLimb` with targets tucked toward the
body, asymmetrically, or the feet read as one.

## Fur (shell layers) and fabric (sheen)

**Fur** is kit code: `furCharacter(rig, ['torso','limb','tail'], opts)` furs
every mesh of the named parts (identified by their shared per-part material,
so scene add-ons are never furred by accident), or `addFur(mesh, opts)` for
one mesh. Each of `opts.layers` (8) shells is the same geometry displaced
along its own normals by `opts.len` — real shell fur riding every IK
transform — with TSL noise coverage that thins toward the tips and darkens
toward the roots. Alpha-test discard via `alphaTestNode` (node slot, per the
materials.md rule), NOT transparency: fur stays on the opaque pipeline and
never joins the sortObjects ordering bill. Verified byte-deterministic on
both backends on the quadruped vector above. Shells cast no shadows —
L casters per part is shadow-map noise that pays nothing on screen.

**Fabric** is a material recipe for `matFor`, verified rendering on r185
(the sheen rim brightens grazing angles on a rough base — look for it on
shoulder edges):

```js
const m = new THREE.MeshPhysicalNodeMaterial({color: 0x7a3550, roughness: .9});
m.sheenNode = THREE.float(1.0);
m.sheenRoughnessNode = THREE.float(.4);
m.sheenColorNode = THREE.color(0xffd9e0);
```

Node slots again — the plain `sheen` property is presumed unreliable the
same way `transmission` measurably is (materials.md).

## Features are scene add-ons

The scaffold ships anatomy; the scene ships character. Attach features to
the rig's groups — the demo's eyes ride `rig.head` (two spheres, four
lines), which is also what makes facing unambiguous: a bare sphere reads the
same front and back, and the first render's front shots looked like back
shots until the face existed. Ears, horns, props, markings all follow the
same pattern. If a feature needs to move, drive it from `t` like everything
else.

## Not here yet (deliberately)

Fur shells and fabric packs land later in Phase 2, tested on the characters
they exist for; the face morph basis, expression library and hands are
Phase 3 (`the-briefing` gates them). Secondary motion stays procedural
(`chainWave`) or baked — never integrated at runtime.
