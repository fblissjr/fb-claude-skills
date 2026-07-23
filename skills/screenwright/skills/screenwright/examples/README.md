# screenwright examples

last updated: 2026-07-23

Each example is a complete, self-contained film: open the `.html` straight
from disk and it plays. **WebGPU is not required** — the embedded
`WebGPURenderer` falls back to WebGL2 transparently, so any WebGL2-capable
browser plays these; with a WebGPU adapter present it is used automatically.
These are the skill's teaching baselines — SKILL.md and the references point
at them — and every one passed the full instrument suite (smoke on both
backends, sheets, motion, independent review).

Rendered previews live in [`docs/media/`](../../../../../docs/media/) at the
repo root, NOT here: the plugin subtree ships to every installed user (and
is cached per version), so it carries only what the skill itself needs.

## gearbox

The regression film against frozen explainer-video: the same scene body on
both stacks, judged side-by-side. Five beats, 16.5s, seamless loop by
construction.

![gearbox](../../../../../docs/media/gearbox.avif)

The same file carries the committed style-bible control pair: switch
`const STYLE = BIBLES.workshop` to `BIBLES.neon` — one line — and the same
beats render as a dark stage where the light is the subject:

![gearbox neon](../../../../../docs/media/gearbox-neon.avif)

## menagerie

The Phase 2 character-scaffold gate demonstration: a furred bear, a
fabric-shirted human, and a text-invented three-eyed strider — three
proportion vectors through ONE `buildCharacter`, walking in on their own
gaits (lateral-sequence quadruped, biped, long-stride biped), stopping,
looking at camera. Squint-distinct silhouettes, strip-checked planted feet,
byte-deterministic on both backends. Open the HTML — no rendered preview by
policy (the scene file plays from disk at full quality; previews are cut on
request only).

## bear-and-bees

The Phase 2 film deliverable — a 21.3s comedy short carrying the
comedic-timing half of the gate: a furred bear ambles in, nose-boops a
hanging hive, and the film HOLDS (2.6s of near-stillness, one scout bee at
the bear's eyeline, a double blink to camera) before 1.1s of everything at
once. Locked silent-comedy camera; the gag reads with zero captions (nocap
pass). Every contact is probe-measured in all three axes: the boop solves
to a surface graze (normalized 1.02), and the flee passes UNDER the hive
with measured clearance. Open the HTML — no rendered preview by policy.

## materials

The pack showcase: one film, three beats, three surfaces — TSL-native cel
banding, subsurface scattering through thin ears, transmissive glass with
dispersion over an emissive core (the overlapping-transparency ordering
case). Recipes and measured gotchas: `../references/materials.md`.

![materials](../../../../../docs/media/materials.avif)
