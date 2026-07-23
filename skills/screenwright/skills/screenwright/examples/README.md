# screenwright examples

last updated: 2026-07-23

Each example is a complete, self-contained film: open the `.html` straight
from disk and it plays. These are the skill's teaching baselines — SKILL.md
and the references point at them — and every one passed the full instrument
suite (smoke on both backends, sheets, motion, independent review).

Rendered previews live in [`docs/media/`](../../../../docs/media/) at the
repo root, NOT here: the plugin subtree ships to every installed user (and
is cached per version), so it carries only what the skill itself needs.

## gearbox

The regression film against frozen explainer-video: the same scene body on
both stacks, judged side-by-side. Five beats, 16.5s, seamless loop by
construction.

![gearbox](../../../../docs/media/gearbox.avif)

The same file carries the committed style-bible control pair: switch
`const STYLE = BIBLES.workshop` to `BIBLES.neon` — one line — and the same
beats render as a dark stage where the light is the subject:

![gearbox neon](../../../../docs/media/gearbox-neon.avif)

## materials

The pack showcase: one film, three beats, three surfaces — TSL-native cel
banding, subsurface scattering through thin ears, transmissive glass with
dispersion over an emissive core (the overlapping-transparency ordering
case). Recipes and measured gotchas: `../references/materials.md`.

![materials](../../../../docs/media/materials.avif)
