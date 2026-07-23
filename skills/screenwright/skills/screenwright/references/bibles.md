# Style bibles v2: the whole look is one object

A bible is a single object that constrains everything about a film's look —
palette, exposure, post, lens, cut pace, camera energy — selected by ONE
line. Changing the film's register is changing that line; changing a field
mid-film is a bible violation (the look stops being coherent the moment two
registers mix).

## The v2 shape (node stack)

The template and solver already consume these STYLE fields directly, so a
bible needs no extra machinery — it IS the STYLE object:

| Field | Consumed by | Governs |
|---|---|---|
| `bg`, `exposure` | template | backdrop, tone-mapped exposure |
| `bloom`, `dof` | post pipeline | halation, rack-focus (per-frame pure) |
| `lens` | cinematography solver | default fov — long flattens, short dramatizes |
| `cutDur` | solver | cut personalities (`{blend, whip}` durations) |
| `energy` | solver | `locked` / `steadicam` / `handheld` camera nerves |
| palette keys | `buildWorlds()` by convention | every material color, emissive glow scale, fog depth |

```js
const BIBLES = {
  workshop: { bg: 0x182430, exposure: 1.15, energy: 'steadicam',
              gearIn: 0xc9a35c, /* ... */ markerGlow: .9 },
  neon:     { bg: 0x0a0e16, exposure: 1.0, energy: 'locked', lens: 24,
              cutDur: {blend: 1.2}, bloom: {threshold: .7, strength: .85},
              gearIn: 0x232b3a, /* ... */ markerGlow: 3.2 },
};
const STYLE = BIBLES.workshop;   // <-- the one line
```

## The committed control pair

`examples/gearbox.html` ships both bibles above. Verified 2026-07-23: same
beats, same geometry, one line — two categorically different films, both
byte-deterministic on both backends. `workshop` is a lit machine-shop
(steel and brass under a key light, steadicam); `neon` is a dark stage
where the machines are silhouettes and the LIGHT is the subject — bloomed
emissive markers, glowing time-history trails, locked long-lens camera,
slower dolly blends. Previews: `docs/media/gearbox.avif` (workshop) and
`docs/media/gearbox-neon.avif` in the repo.

## Register rules

- **One bible per film.** A film that needs two looks is two worlds under a
  cut, each still inside the bible, or it is two films.
- **The bible owns the post flags.** A dark emissive register (neon) turns
  bloom on and budgets markerGlow so only the payoff crosses the threshold;
  a lit register leaves bloom off rather than fighting a pale palette's
  halation (bloom is palette-conditional — `materials.md`).
- **Camera energy is register, not preference.** Technical/diagrammatic
  wants `locked` or calm `steadicam` + long lens; character registers earn
  `handheld` only in moments the story is unstable.
- **Palette keys are the scene's contract with the bible.** buildWorlds()
  reads colors ONLY from STYLE — a hex literal in a material is a look
  decision hiding from the bible switch (the control pair is the test:
  if switching bibles leaves a color behind, that color was hardcoded).
