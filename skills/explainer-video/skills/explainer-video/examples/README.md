# Examples

Six films, each built with this plugin. Every one is a **single self-contained
`.html`** — three.js is embedded, so you can open any of them straight from disk
with no build step, no server, and no network.

## Open the `.html`, not the `.avif`

The `.html` **is** the film. It runs at your display's refresh rate, at full
resolution, and it is the same file the renderer reads — nothing is lost.

The `.avif` beside it is a heavily compressed recording, kept only so the films
show up inline on GitHub, which cannot run a script tag. It is **960px wide at
15fps** against the HTML's full resolution at 60fps, with lossy compression on
top. Motion judders, gradients band, and fine linework softens. It is a
thumbnail, not the work — judge any of these by opening the HTML.

| | `.html` | `.avif` |
|---|---|---|
| resolution | full | 960px wide |
| frame rate | display (60fps typical) | 15fps |
| compression | none | lossy, aggressive |
| plays on github.com | no (script tags stripped) | yes, inline |

## The films

**`heat-pump`** — 36.6s, 10 beats. Where winter heat comes from. **Three worlds**
— the street outside, the sealed refrigerant loop, the molecular scale — joined
by four hard cuts, each hidden under a flash at full opacity on the exact frame
the world changes. The longest film here and the one that shows the
establishing → dive in → pull back out structure end to end.

**`chain-reaction`** — 16s, 5 beats. A six-link Rube Goldberg machine. Each
link's trigger time is derived from the previous link's own curve, which is what
makes it read as *causation* rather than six things happening near each other.
Built to test that distinction, and it holds.

**`pelican-walk`** — 17.8s, 5 beats. A pelican walks home from work in a
thunderstorm. No explaining to do; it exists to show the pipeline carrying mood.
Rain is 1600 instanced streaks whose height is `mod(t)`, and the lightning is
three exponential decays at fixed offsets — both pure functions of `t`, which is
the only reason a storm can be scrubbed frame-exactly.

**`toybot-dance`** — 12.6s, 5 beats, **no captions at all**. The groove is one
continuous phase with beats shaping only its amplitude, and the speaker pumps on
the same expression that drives the dance, so the music visibly causes the
motion. The counterexample to "this skill only makes explainers".

**`toybot-walk`** — 14s, 8 shots. The cinematic reference: cel shading with
inverted-hull outlines, analytic two-bone IK, rack-focus depth of field, and
bloom through a post chain that stays byte-deterministic. Authored with **zero
hand-written camera keyframes** — every framing comes from the shot list, and it
carries a compiler-verified match cut. Also carries two style bibles: change
`BIBLE` to `midnight` and re-render for a low-key neon-noir version of the same
film, zero content edits.

**`one-scene-every-format`** — 20.8s, 6 beats. The Canvas2D backend in the
paper-cutout pack, explaining this plugin's own pipeline. Held camera, flat
vector, no three.js at all — the source file is the artifact.

## Copying from these

They are meant to be read and stolen from. The two templates in
`../templates/` are the clean starting points; these are what the templates look
like once a real film has been built on them. `toybot-walk` is the best model for
a character or shot-driven piece, `one-scene-every-format` for a diagram,
`heat-pump` for anything with an inside.
