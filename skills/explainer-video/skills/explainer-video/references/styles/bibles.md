# Style bibles: one object constrains every layer

A style *pack* (the other files in this directory) swaps the 2D `STYLE`
block. A style **bible** is the same idea grown to full register: one object
that constrains **palette, lights, post-processing, glass (default lens),
cut pace, and camera energy** — everything that is register, nothing that is
content. `BEATS`, the cast, the world geometry, and the `SHOT` list are
content; a bible never touches them.

Mechanically (3D template + `examples/toybot-walk.html`): a `BIBLES` table
and a one-line switch —

```js
const BIBLE='toybox';        // the whole film changes here
const STYLE=BIBLES[BIBLE];
```

The solver reads bible-level defaults: `STYLE.lens` (a long lens flattens
and tenses; a normal lens is friendly), `STYLE.cutDur` (a slower blend is a
deliberate dolly — cut pace IS register), `STYLE.energy`
(locked/steadicam/handheld). Lights, fog, world colors, the matcap stops,
and the post chain's bloom/DoF all resolve from the bible.

## The control pair (the proof, committed)

`toybot-walk.html` carries two bibles. Same beats, same eight shots, zero
geometry edits — one line apart. Only `toybox` ships as a committed AVIF;
`midnight` is a one-line render, which is the cheaper way to hold the claim
honest (a committed artifact can go stale against the scene, a re-render
cannot):

| bible | register | one-line summary |
|---|---|---|
| `toybox` (default — the committed `toybot-walk.avif`) | daylight paper-cutout | 42° lens, steadicam, .8s blends, warm keys, bloom only on the orb |
| `midnight` (flip `BIBLE` and render) | low-key neon noir | 30° lens, locked tripod, 1.3s dollies, magenta rim, bloom threshold .55 — glow carries the frame |

If a bible swap did NOT categorically change the film, the layers would not
actually be separated — this pair is the standing test that they are. The
crush lint fires at 84% on midnight; that is the register, judged by
looking, exactly as the neon-dark pack's hazard note predicted.

## Writing a new bible

Copy an existing entry and change values — every key is register:

- `bg / floor / ink / body / accent / trim / tree / trunk / matcap` — palette
- `toonSteps / outline` — how hard the cel reads
- `lights: {hemi, key, rim}` — the rig IS mood; noir = dim hemi, hot rim
- `lens` — the default glass; shots may still override per-shot `fov`
- `cutDur` — overrides per cut type; pace is register
- `energy` — locked / steadicam / handheld
- `post` — bloom strength/threshold (what glows), aperture (how shallow)
- `exposure` — see the wash/crush section in `style-3d.md`

Descriptive names only (`toybox`, `midnight`, `blueprint`) — never director
names. Cut-rhythm-as-average-shot-length is not a parameter yet; `cutDur`
is the pace lever until a film needs more.
