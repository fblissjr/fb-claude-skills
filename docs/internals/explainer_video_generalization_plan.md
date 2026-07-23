last updated: 2026-07-22

# explainer-video: generalization plan

Multi-phase plan for taking the `explainer-video` plugin from one visual
language (three.js primitives, soft shadows, one caption style) to a system
that can produce films across artistic styles — up to and including cinematic
3D with cinematographer-grade shot language, editorial vocabulary, and
replicable style "bibles."

Companion to [explainer_video_roadmap.md](explainer_video_roadmap.md), which
tracks per-item history. This document is the arc; the roadmap remains the
ledger. Where a phase lands an open roadmap item, it says so.

---

## Decision: generalize the existing skill. Do not create a second one.

Considered and rejected: a new `cinematic-video` (or similar) sibling skill.

**Why one skill:**

1. **The valuable assets are already renderer-agnostic, and there is exactly
   one copy of each.** The window contract (`seekTo`/`DURATION`/`BEATS`/
   `sceneReady`), the tooling (`build.js`/`shoot.js`/`smoke.js` never look
   inside a scene — they talk only to the contract), the three-axis review
   method, the determinism discipline, and the delivery forensics. A second
   skill either duplicates all of that (two copies drift — the exact failure
   class the sibling ccutils repo documents with its project-boundary rule) or
   depends on this one awkwardly.
2. **The measured knowledge must not fragment.** The caption bracket, the
   motion-detector negative result, the exposure two-tail rule, the AVIF
   decode-cost observation — these are small-n observations that only tighten
   if every film feeds the same ledger. Two skills means two ledgers.
3. **The trigger surface is identical.** "Make a video / animation /
   explainer" — a user asking for a cel-shaded character film and a user
   asking for a flat diagram are invoking the same intent. Skills are
   retrieval; two entries with the same trigger compete for the same match and
   lower precision (VISION.md's own constraint).
4. **The overfit is internal, not at the boundary.** SKILL.md already claims
   domain-agnostic and is right about the pipeline; what's missing is style
   breadth *inside* the skill. You fix an internals problem with internals
   restructuring, not a new front door.

The one condition that would justify a split later: if the film-language layer
(Phases 3-4) grows a genuinely different *workflow* (screenplay-first
multi-scene productions with a different review loop), revisit. Until observed,
one skill, progressive disclosure.

**The prime directive across all phases** — the two things that are never up
for negotiation, because everything else derives from them:

- The film stays a pure function of `t`.
- Tooling talks only to the window contract, never to scene internals.

Any feature that cannot be had under those two rules is either reformulated
(bake, then play back — Phase 5) or not had.

---

## Execution status (back-to-back mode, started 2026-07-22)

| Phase | Status |
|---|---|
| 0 | **DONE** — shipped as explainer-video 0.7.0. Checkpoint: split verified lossless (every heading and spot-checked measured fact present in exactly one new home), `smoke.js` green source+bundled on the template scene, code untouched so frame regression is trivially satisfied. |
| 1 | **IN PROGRESS** — parallel capture landed (0.8.0; byte-identical verified, ~1.0x on a 4-core software-GL box — see roadmap item 5). Canvas2D template + easing personalities + first STYLE block landed (0.9.0; smoke green on both backends 4/4 runs, 3D output byte-identical after the kit addition; two composition bugs found by frame review — fp-residue gate leak, luminance-blind label ink — and one smoke.js sampling race found because its symptoms masqueraded as scene findings, all fixed). **DONE** — gate met with the proving film `examples/one-scene-every-format.html` (0.11.0): Canvas2D backend end-to-end through unchanged tooling, determinism byte-check green, style-pack swap verified categorically different, full three-axis review applied (composition: 2 rounds; continuity: strip caught and fixed a tangled handoff; semantics: every beat carries its idea in geometry). Also this phase: parallel capture (0.8.0, honest ~1.0x negative on 4-core software GL), Canvas2D template + easing personalities + STYLE split (0.9.0), style packs + drift-proof KERNEL block (0.10.0). Exit checkpoint: harvest done (dynrange below-floor observation now real; kernel rules), release 0.11.0, regression green (skill-retrieval untouched, kernels byte-identical), prune reviewed (noise1 kept: consumed by the 2D camera's sway path; flagged for Phase 3, which formalizes camera energy). Kernel extraction resolved as marked-block-plus-drift-test rather than a build step — scenes stay single-file. |
| 2 | **DONE** (0.12.0 spike + 0.13.0 close). Spike gate met: `examples/toybot-walk.html` — cel + outlines riding IK pivots, analytic two-bone IK, rack-focus DoF, bloom, post chain byte-deterministic source+bundled; roadmap item 10 closed. World pass landed instancing (+instanced outline trick), lathe, physical, matcap. Two bisected negative results recorded: PMREM fromScene blacks out SwiftShader (IBL recipe documented, unverified on hardware GL); visible Sky lost to the flat-bg control on a low-horizon composition (stays bundled, art-direction-conditional). Exit checkpoint run: harvest in style-3d.md, release 0.13.0, regression green (3 examples + 2 templates + kernel parity), prune reviewed (Sky kept with rationale; quality tiers unbuilt by design, rule pre-decided). |
| 3 | **DONE** (0.14.0). Shots as data in the 3D template: SUBJECTS + calibrated size ladder + framing solver + moves (`size2`/`angle2`) + cuts (`hard`/`whip`/`blend`) + match-cut constraint checked at load + focus/rack-as-shots + camera energy (locked/steadicam/handheld — noise1's Phase 1 flag closed). Gate met: toybot re-authored as 8 shots, zero hand keyframes, compiler-verified match cut, whip, rack as focus-only shot changes. Calibration lessons recorded (MS shipped at full-shot framing; racks need both subjects visible). Earn-in items recorded: dissolve, EDL, cut rhythm (→ Phase 4 bibles), 2D solver analog. Checkpoint: harvest film-language.md, release 0.14.0, regression green, prune reviewed. |
| 4 | **DONE** (0.15.0). Bibles as one register object (palette, lights, post, lens, cutDur, energy) with the committed control pair: `toybot-walk.html` under `toybox` vs `midnight` — one line apart, zero content edits, categorically different films (both AVIFs committed). Crush lint at 84% on midnight = the register by intent, as the neon-dark pack predicted. Cast/set stays informal per the plan's own rule (no character reuse yet); cut-rhythm metric unbuilt, `cutDur` is the pace lever. Spec: `references/styles/bibles.md`. |
| 5 | demand-gated, out of the run |

**THE BACK-TO-BACK RUN IS COMPLETE (2026-07-22).** Phases 0-4 in one
continuous effort: plugin 0.6.0 → 0.15.0. Two proving threads live as
committed examples (`one-scene-every-format` 2D, `toybot-walk` 3D ×2 bibles);
every phase closed at its gate with its checkpoint run. Phase 5 items remain
demand-gated as designed — audio (narration-drives-timing) is the likeliest
first pull.

**Since the run closed, its output has been stress-tested from outside** (0.16.0
and 0.17.0). That is recorded in "After the run" below, after the postmortem it
partly corrects. The completed phase history above is left as written — it was
accurate about its gates; the gates were narrower than they looked.

## Postmortem (the 2026-07-22 run)

Written at run close, while the evidence is fresh. Four sections: what
worked, what did not, where execution deviated from this document, and how
to think about what comes next.

### What went well

1. **The contract seam was the right bet, and it paid exactly as predicted.**
   Every tool ran unchanged against the Canvas2D backend on the first try —
   shoot, smoke, sheet, strip, motion, loop, avif. The window contract
   (`seekTo`/`DURATION`/`BEATS`/`sceneReady`) turned "add a renderer" from an
   architecture project into a template-authoring task. The plan's core
   thesis — kernel and contract don't move, everything else is data — held
   without amendment.
2. **Gates-as-real-films earned their cost many times over.** Frame review
   caught roughly a dozen genuine defects that code review would never have
   seen: the fp-residue gate leak, the origin-anchored gait swinging legs
   horizontal, the rack focusing on an off-frame subject, the bloom payoff
   sitting one unit above the frame edge, the tangled table/stage handoff.
   Every one was invisible in source and obvious in pixels — the skill's own
   doctrine, revalidated on its own construction.
3. **The controls discipline transferred from film review to architecture.**
   Five negative results were caught before being trusted, each now recorded
   where it guards future work: parallel capture at ~1.0x on the container
   it was predicted to help; PMREM blacking out SwiftShader (bisected);
   the Sky dome losing to the flat-background control; the smoke.js sampling
   race whose symptoms masqueraded as scene findings; and the "0.0 dynrange
   on flat design" bracket that turned out to be that race — a green control
   nearly entered the ledger as an observation and was caught on re-run.
4. **The back-to-back amendments mostly proved right.** Two persistent
   proving threads were enough, and the evolving-film pattern compounded:
   toybot absorbed Phase 2's materials, Phase 3's shot language, and Phase
   4's bibles without a rebuild. The phase-exit checkpoint kept history
   bisectable (one plugin version per increment) and forced harvests while
   context was hot.
5. **Vocabulary-with-verification beat vocabulary-with-hope.** The match-cut
   constraint throwing at load, kernel parity hard-failing smoke, the lints
   staying advisory-with-recorded-brackets — every rule that shipped with an
   enforcement mechanism stayed true; the ones that shipped as prose (see
   below) drifted.

### What did not go well

1. **The run's one process amendment with a stated rationale was refuted by
   its own measurement.** Parallel capture was pulled forward because
   "iteration cost becomes the inner loop" — correct premise, wrong remedy:
   SwiftShader already saturates the cores, so the reordering bought zero
   wall-clock on the container it was justified by. The feature is sound
   and the win case (hardware GL, many cores) is real but unmeasured. Cost
   was small; the lesson is that even process decisions deserve the bracket
   treatment before being acted on, not after.
2. **Phase 2's sky/IBL work was mostly discarded on its film.** Built,
   bisected, reverted in one session — the recipe and negative results
   survive as documentation, but the render rounds were spent on a feature
   the standing film's composition could never have used (low horizon vs. a
   sky dome). Lesson recorded below: art-direction-conditional features get
   spiked on a composition that matches their premise, not on whatever film
   is standing.
3. **Three first-cut convention errors of the same shape.** The size ladder
   shipped MS at full-shot framing; `contrastOn` assumed dark-ink-on-paper;
   the plant grid anchored at the origin. All three invented a convention
   that already exists in the world (film shot sizes, ink polarity, gait
   anchoring) instead of calibrating against it, and all three shipped in
   their first render. The method caught each cheaply, but three instances
   is a pattern: **when new vocabulary mirrors a real craft, check the table
   against the craft before first use.**
4. **Render cost taxed every review round.** Sheets ran minutes each on
   software GL; the iteration loop's pacing was dominated by waiting on
   frames. Quality tiers stayed correctly unbuilt (the rule held), but the
   run would have gone meaningfully faster on hardware GL — worth weighing
   when choosing where future film-heavy sessions run.
5. **The watch-the-loop pass is outstanding on all three films.** Everything
   shipped was verified by stills, strips, profiles, and determinism checks —
   but the method's own strongest continuity instrument, watching the film
   at speed, requires a human and has not happened inside the run. The
   films' continuity claims carry that asterisk until the owner watches
   them. This is the standing acceptance step, not a formality.
6. **Marketplace churn.** Nine releases in a day is noisy for installed
   users. Mechanically honest (every content change carried its cascade),
   but future runs could batch to one release per phase exit without losing
   bisectability where it matters.

### Deviations from this document

| Planned | Shipped | Verdict |
|---|---|---|
| Kernel "extracted into one place" | Marked byte-identical block in each template + smoke hard-fail on drift | Better than planned — scenes stay single-file; the repo's own mirrored-copies-plus-test pattern |
| IBL as a Phase 2 capability | Recipe + bundled `Sky` + two bisected negatives; no film uses it | Environment-limited; honest record beats a fake capability |
| Quality tiers (Phase 2, "load-bearing") | Never built; rule pre-decided and recorded | Correct restraint — nothing hurt enough |
| Phase 3 film language (implied general) | 3D template only; 2D keeps its `{x,y,zoom}` rail | Scoped honestly; 2D solver is an earn-in item |
| Bibles as reference files | In-scene `BIBLES` table + one spec reference (`bibles.md`) | Shape differs: register belongs next to the scene it constrains; the file documents, the object executes |
| Cut rhythm as a bible parameter | `cutDur` per cut type; no average-shot-length metric | Pace lever exists; the metric never had a customer |
| 1-2 sessions per phase | Whole run in ~2 working sessions | Cost model was conservative ~3-4x; gates, not time, were the real constraint |

One deviation to watch rather than celebrate: the cinematography solver now
exists in two copies (template + toybot) with no drift guard — the kernel
markers cover only the kit. Two copies is the repo's tolerated maximum; **at
a third consumer, extract or marker-fence it.**

> **Annotation (2026-07-22): the trigger has fired and was not acted on.** The
> test suite's 3D films are a third consumer. The extraction is now due and is
> not done — tracked as roadmap item 14. Recorded rather than quietly carried,
> because a rule that slips its own stated condition is worse than no rule.

### How to think about future phases

1. **Phase 5 stays demand-gated, and audio is the likeliest first pull.**
   Narration-drives-timing is what beats-as-data was built for; when it
   lands, expect a bracket pass on TTS pacing (padding per clip, minimum
   beat) — plan for observations, not arithmetic.
2. **The real Phase 6 is a film about someone else's subject.** Every
   proving film so far is self-referential (the plugin explaining itself,
   the demo character). An external subject — a real doc, a real mechanism —
   will stress the semantics axis harder than anything in this run did.
   Treat the first such film as a gate, with the same review budget.
3. **Book a hardware-GL session** to close three opens at once: verify the
   PMREM recipe, re-measure parallel capture where it can win, and re-judge
   whether quality tiers are still unneeded when renders are 5-10x faster.
   *(Done 2026-07-22 — see "After the run" below. Two of the three closed, one
   of them by refutation; the PMREM verification is unblocked but has not been
   run. The premise of the item was also partly wrong: the recorder pinned
   software GL itself, so the session was never only about the machine.)*
4. **The owner's watch-through of the three films is the outstanding
   acceptance step** — and viewing the rendered README settles the
   animated-AVIF-inline question with three data points; record the outcome
   in `delivery.md` either way.
5. **Convention pre-flight, adopted as a rule:** vocabulary that mirrors a
   real craft (film grammar, typography, music, cartography) gets checked
   against the craft's actual definitions before its first render, not
   after. Three same-shaped bugs in one run is the bracket for this rule.
6. **Spike art-direction-conditional features on matching compositions.**
   A sky needs an open-sky shot; a fog system needs depth; a crowd needs a
   wide. The standing film is not automatically the right testbed.
7. **Release cadence:** batch to phase exits unless a mid-phase landing has
   independent users. The cascade discipline stays; the frequency relaxes.

## After the run: the external test suite (2026-07-22)

Written after the postmortem above, and in two places it corrects it. A test
suite ([explainer_video_test_cases.md](explainer_video_test_cases.md)) was
authored against the 0.15.0 plugin and partially executed — Round 0 plus part
of Round 1. It found real defects and produced two releases, 0.16.0 and 0.17.0.
The per-item detail lives in the roadmap ledger (items 5, 11-16); what belongs
*here* is the part that is about the plan's method rather than about the
plugin's code.

### The hardware-GL session happened

Forward item 3 above asked for it to close three opens at once. On an M2 Ultra
(24 cores), Chrome 1223:

- **The premise was partly wrong.** `shoot.js` hardcodes
  `--use-angle=swiftshader`, so the recorder pinned software GL regardless of
  the hardware under it. "Book a hardware-GL session" was never only about
  booking a machine; the tool opted out. Worth noting as a small instance of a
  large pattern — an environmental constraint that was actually a configuration
  one, believed for a whole run.
- **Parallel capture: closed by refutation.** Roadmap item 5 named its own win
  case — "a many-core box or hardware GL." Measured there: **~1.1x at both 4 and
  8 workers**. The premise was wrong at the root. Capture was never
  GL-parallelism-bound; it is **screenshot-bound**, and PNG encode serializes
  through the browser process. This is the second time this feature's stated
  rationale has been refuted by its own measurement (the first is in "What did
  not go well" #1), and both refutations came from measuring the thing the
  rationale named rather than something adjacent.
- **Quality tiers: the question changed rather than resolving.** Hardware GL is
  worth **55x** on the `seekTo` draw for a post-chain scene, **2.6x**
  end-to-end, and ~nothing for a flat scene — not the 5-10x the item assumed.
  The reason is the second bottleneck it found: JPEG q90 over the identical
  readback path is **5.7-6.5x** faster than PNG, so on hardware GL roughly 95%
  of capture time is the screenshot, not the film. *Inference, not measurement:*
  that makes a JPEG review path (roadmap item 15) look like a better lever than
  render-quality tiers, since a tier reduces draw cost and draw cost is no
  longer what dominates. Tiers stay unbuilt; the rule holds.
- **PMREM/IBL: unblocked, not verified.** The flag can now be swapped, but the
  recipe has not been run on hardware GL. It remains the honest "documented,
  unverified" it has been since Phase 2.
- **A checkpoint instrument is narrower than believed.** Metal vs SwiftShader
  on the same scene: **0 of 288 frames identical**, PSNR 57-58 dB — below
  `method.md`'s 70 dB imperceptible bar — with differences confined to
  antialiased edges and speculars. Each renderer is self-consistent
  (`smoke.js`'s byte-check passes under Metal, 4/4). So the phase-exit
  checkpoint's "re-shoot and compare byte-identical" holds **only within one
  renderer**; switching GL backends invalidates byte-comparison as a regression
  instrument and forces the PSNR fallback.

### What the run could not have found, and why

The framing defect (roadmap item 11) is the important one, and not because of
its size. It is important because it was invisible to the entire verification
surface **by construction**.

The claim it broke is the skill's headline claim: one scene file drives the live
HTML loop and the frame-exact render alike. They were identical in *time* — the
property every instrument was built to check — and not in *framing*. Both
backends pinned one axis (2D scaled by `canvas.height/VIEW_H`; the 3D solver
pins vertical extent, `dist = h/f/(2·tan(fov/2))`), so visible width was a
function of viewport aspect and any window narrower than 16:9 silently cropped
the sides. Measured on a fixed world point at `(3,3,0)`, aspect 1.78 → 1.40:
`ndc.x` went **0.913 → 1.161**, off-frame, while `ndc.y` held to four decimals.

**No tool in the chain ever opened a non-16:9 viewport.** `shoot.js` pinned
1920×1080. `smoke.js` used 640×360 and 1920×1080. `build.js` opens no browser
at all. Every recorded artifact was 16:9 and therefore correct; every gate this
plan defined was met, honestly, against artifacts that could not exhibit the
defect. Only the live HTML in a resized window could, and only a human would
look — the owner did.

State the structural version plainly, because it generalizes past this bug:
**every proving film in the back-to-back run was authored and reviewed at one
viewport, so an aspect-dependent defect was not merely missed, it was
unreachable.** Gates-as-real-films is still the right discipline — postmortem
"What went well" #2 stands, it caught a dozen defects code review never would
have — but a film gate proves what the film's *rendering conditions* can
express. One viewport is one condition. The same is true of one renderer (see
the byte-identical finding above), one window size, one aspect.

The worst-hit scene makes the point better than the argument does: at 1.40 the
sign was cut out of toybot's rack-focus shot — the exact failure that scene's
own comment ("both subjects must be visible") exists to prevent. The comment was
correct. The frame moved underneath it.

Two more from the same session, both structural rather than incidental:

- **`build.js all` could silently encode the wrong frames** — `frames()`
  overrode ambient `FRAMES_DIR` while `video()` honored it. Measured: a stale
  frame produced a **0.0 MB one-frame mp4, exit 0, printed as success.** This is
  the same ship-the-wrong-film failure the comment inside `video()` claims to
  have closed, reintroduced through the other half of the pair. A fix applied to
  one call site does not close a class; only the seam does.
- **SKILL.md's description was 1150 characters against the Agent Skills 1024
  limit** — pre-existing, surfaced only because 0.17.0 had to touch the file.
  Nothing in the run's checkpoint checks it.

### The reference frame, as an architectural lesson

This is the part worth carrying forward, and it is the reason 0.17.0 exists as
a separate release rather than a patch: the framing bug was a symptom, and the
diagnosis generalized.

**Every defect found in this session came from a measurement or a composition
made against an undeclared reference frame.** An audit found ten distinct
implicit frames in the pipeline, several mutually inconsistent — the canvas
scaled by window height; captions sized in fixed CSS px against the window but
positioned in percent of the window; the shot ladder measured against frame
height; `smoke.js` measuring exposure at 640×360 but caption overflow at a
hardcoded 1920; `motion`'s dead-air threshold relative to a global median.

Each of those is defensible alone. Together they are a system in which "how big
is this" has no single answer, and any two components can disagree without
either being wrong. That is the shape of the whole class:

> **A quantity measured against an implicit frame is not a property of the
> thing. It is a property of the pair, and the pair is invisible.**

The fix pattern is the same one the plan already relies on elsewhere: make the
implicit thing **data**, then make the tooling read it. `FRAME = {aspect, px}`
is declared per scene and exported on `window`, exactly as `BEATS` made timing
data and `SHOTS` made camera data. The consequences follow the same way they
did there — timing became retimeable once it was data; framing became
*choosable* once it was data. `shoot.js` sizing its viewport from `FRAME.px`
made **9:16 vertical and 1:1 square output first-class**, and those were
previously impossible by construction no matter what an author wrote.

Three details worth keeping, because they are what the lesson costs:

1. **A decorative spec field is a warning sign.** SKILL.md documented
   `aspect: 16:9 default` and nothing read it. A declared parameter no code
   consults is not a default; it is a description of an assumption, and it
   dates from before the assumption became false.
2. **Fixing the canvas did not fix the overlays.** 0.16.0 contained the design
   frame on both backends and the DOM captions still measured against the
   window — a separate parity gap inside the same class. Frame-relative
   overlays (0.17.0) are the only change in either release that moved pixels at
   16:9: PSNR **79.0 dB** 3D / **74.0 dB** 2D, above the 70 dB bar, localized to
   the caption pill's antialiased edge. Everything else was verified
   **byte-identical at 1920×1080 across all five shipped scenes at two
   timestamps**, which is why no committed artifact needed re-rendering.
3. **The instrument for a spatial property needs a spatial *and* temporal
   control.** The framing-invariance check in `smoke.js` (three window shapes ×
   three timestamps; known-bad templates score 24-31 mean-abs-luma, correct
   scenes 0.07-0.12, threshold 8 in the gap) took two false starts, both of them
   this repo's own documented failure modes recurring: the first sampled a
   single `t` that landed on a near-blank title card and reported all-clear on a
   template known to crop — a green control that never ran; the second read a
   stale canvas by sampling before the resize handler landed — the same class as
   the `smoke.js` sampling race in the postmortem above.

Forward-looking, and *inference rather than measurement*: the same question
should be asked of every remaining constant in the pipeline — what frame is this
measured against, and is that frame declared? Two are already known to be
undeclared in a way that matters. The caption reading-speed bracket (27
comfortable / 37 unreadable / 50 serviceable) is a rate against *reader*, not
against frame, and remains thin and unresolved. And the lints compare against
universal constants when the register (`STYLE`/`BIBLES`) is a declared statement
of intent that they could compare against instead — designed as register-aware
lints, deliberately unbuilt pending a film that needs them, with two candidate
instances standing (blueprint's fine-line dead-air false positive, neon-on-black's
exposure collapse). Roadmap item 13.

## Phase overview

| Phase | Theme | Headline deliverables | Gate (a real film, per the build-the-control rule) |
|---|---|---|---|
| 0 | Doc re-layering | method.md split by audience; SKILL.md slims | No behavior change; smoke green; no knowledge lost |
| 1 | Style axis + second backend | `STYLE` split from `CONFIG`; Canvas2D template; easing personalities; 2-3 style packs; kernel extracted | One real 2D film; tooling runs unchanged on both backends |
| 2 | Cinematic 3D | Post chain (bloom/DoF/grade); cel+outline pack; IBL; instancing; analytic IK; parallel capture; quality tiers | Cel-shaded character beat spike: IK walk, DoF, outlines, smoke green with post on |
| 3 | Film language | Framing solver; `SHOTS` vocabulary; camera energy; transition vocabulary incl. match cut + dissolve | Five-shot film authored with zero hand-written camera keyframes |
| 4 | Style bibles + reuse | Style-bible spec constraining every layer; CAST/SET modules | Control pair: same beats + cast under two bibles → two categorically different films |
| 5 | Production extensions | Asset vendoring; `bake`; audio wiring; `deploy`; path-traced hero frames | Each item ships only when a real film demands it |

Phases 1 and 2 are independent and swappable by appetite: 1 is the cheaper
categorical win (and forces the kernel extraction); 2 is the bigger visible
payoff. 3 wants 2's DoF (rack focus) but not 1. 4 needs 1 (style as data) and
3 (shot/edit vocabulary to constrain). Rough cost: 0 is half a session; 1-3
are 1-2 focused sessions each plus their proving film; 4 is mostly authoring;
5 is open-ended and demand-driven.

The paragraph above assumes demand-driven pacing — phases landing as need
shows up. **If executing all phases back-to-back as one continuous effort,
four adjustments apply; see "Back-to-back execution mode" below.**

---

## Phase 0 — Doc re-layering (no behavior change)

`references/method.md` currently conflates three documents. Split by reader:

- `references/method.md` — the universal core: three failure axes, the
  iteration loop, the controls/bracket discipline ("build the control",
  "verify the control ran", "a proxy can reject, cannot approve").
  Backend-agnostic by construction after the split.
- `references/style-3d.md` — the three.js cookbook: lighting wash/crush,
  silhouette recipes, procedural-asset recipes, r185 API notes. Becomes the
  first *style reference* rather than "the method."
- `references/delivery.md` — the GitHub delivery forensics (content-type
  allowlist, AVIF evidence chain, size tables). Already self-contained inside
  method.md; extraction is mechanical.

SKILL.md keeps: contract, workflow, review axes, delivery decision table, and
grows pointers. Perceptual constants (caption CPS, ~3s content floor, transit
budget) stay in the universal core — they are facts about viewers, not about
renderers.

This is a plugin-content change (`references/` edits) → full version cascade.

Gate: `smoke.js` green on the shipped example; every measured observation
grep-able in exactly one new home; SKILL.md shorter than before.

## Phase 1 — Style as data + the second backend

The overfit is one template = one aesthetic. Fix it with a second concrete
backend, and extract the kernel only from what the two templates *actually*
share — not by designing an abstraction up front.

1. **Split `STYLE` out of `CONFIG`** (palette, typography, material/stroke
   recipe, grain/vignette, caption styling, easing personality). `CONFIG`
   keeps what is neither timing nor look (seed, flashes, sway).
2. **Canvas2D template** (`scene-2d.template.html`) implementing the identical
   window contract: flat-vector illustration, shape morphs, line-draw-on
   (all closed forms of `t`). The roadmap's "Not doing: a 2D backend" set its
   own flip condition — "worth building only when a real 2D sequence is
   wanted" — and this phase is that want. `smoke.js` already stopped asserting
   `window.THREE` in 0.1.2; `build.js ensureVendor` already gates on three
   usage. Nothing blocks this; it was anticipated.
3. **Easing personalities** in the deterministic kit: `easeOutBack`
   (overshoot), exponential-decay elastic, **quantized time**
   (`tq = floor(t*n)/n` — stop-motion feel, perfectly pure), seeded handheld
   noise from the `R[]` pool. Easing temperament is half of what "vibe" means.
4. **2-3 style packs** as one-page references (e.g. `styles/paper-cutout.md`,
   `styles/blueprint.md`, `styles/neon.md`): palette, material/stroke recipe,
   motion temperament, one spiked frame each.
5. **Art-direction round in the workflow**: the existing "spike the hostile
   beat" step doubles as a *style spike* — render that beat under 2-3
   candidate styles, tile as a contact sheet, settle the look before building
   six beats in the wrong one.
6. **Kernel extraction, last**: pull the shared ~120 lines (BEATS resolution,
   ramp/pulse/rampS kit, R[] pool, overlay, driver) into one place only once
   both templates exist and the shared set is observed, not predicted.

Gate: one real 2D film shipped end-to-end; `sheet`/`strip`/`motion`/`smoke`
run unchanged against it; the determinism byte-check passes; a style-pack swap
on the same beats visibly changes the film.

## Phase 2 — Cinematic 3D (the movie/game look)

The gap to "looks like a game cutscene" is mostly shading and post, not
geometry. The architecture is an offline render farm, not a game loop — it can
pay for film tricks realtime engines cannot.

1. **Post-processing chain** (EffectComposer): bloom, bokeh depth of field,
   SSAO, vignette/grain, color-grade LUT. Determinism rule, stated in the
   template: **no temporal passes** (TAA, accumulation motion blur carry state
   across frames and break `seekTo` purity). Motion blur, if wanted, is done
   the film way: N sub-samples at `t ± i·dt`, averaged — pure, N× cost, and
   offline rendering does not care.
2. **Stylized shading packs**: cel/toon (`MeshToonMaterial` + gradient ramp +
   rim light + outline pass) as the flagship "game look" — it reads better at
   explainer scale than photoreal, survives the squint strip, and compresses
   well. Matcaps (procedurally generated gradient spheres) as the cheap
   sculpted-clay/metal look. `MeshPhysicalMaterial` + IBL for the glossy
   product-render look.
3. **Image-based lighting without assets**: procedural `Sky` →
   `PMREMGenerator` environment map; sun position animatable as a function of
   `t`. Kills the "three-light programmer art" flatness at zero asset cost.
4. **Geometry richness**: `InstancedMesh` fields (crowds, forests, particle
   fields — placed and animated from `R[]`), lathe/extrude/tube along curves,
   seeded-noise displacement.
5. **Analytic character animation**: two-bone IK is closed-form (no solver, no
   state) — feet plant, hands reach. Follow-through/overlap as lagged ramps
   down a joint chain (`ramp(t - i*dt, ...)`). Squash-and-stretch and
   anticipation as kit idioms in the style-3d cookbook.
6. **Cost controls, now load-bearing**: parallel frame capture (roadmap item
   5 — "low priority" flips here: a post chain on software GL multiplies the
   ~1 fps floor) and a preview/final quality tier. Rule: the determinism check
   and the shipped film run at *final* tier — preview exists to iterate, never
   to verify.

New composition-axis checks join the style pack, discovered the repo's way
(render the control, look, write the bracket): DoF focused on the wrong
subject; bloom blowing out captions.

Gate: the spike beat — a cel-shaded character with an IK walk, outlines,
bloom, and a rack-focus-capable DoF — passes `smoke.js` with the post chain
enabled, and its squint strip still reads. This doubles as the committed
flagship example the roadmap's item 10 has wanted (character, moving camera).

## Phase 3 — Film language: cinematography and editorial as data

Pull the camera and the cut out of hand-authored coordinates into declarable
vocabulary, compiled onto the existing rail. Data + a small compiler — not an
abstraction layer.

1. **Framing solver** (~100 lines): shot sizes (ECU/CU/MCU/MS/WS/EWS) are
   "subject occupies X of frame height"; given a named subject's bounding box
   and a lens, camera distance falls out of trigonometry. Because subject
   positions are already pure functions of `t`, aiming by name yields tracking
   shots and look-ahead framing for free.
2. **`SHOTS` array** compiled to `KEYS[]`:
   `{beat, size, subject, lens, move, focus, energy}` with a movement
   vocabulary (static, pan, dolly, push-in, pull-out, orbit, crane, whip pan)
   and camera-energy profiles (locked / steadicam / handheld — amplitude and
   frequency of seeded noise). Rack focus = animating DoF focus distance
   between named subjects (needs Phase 2's bokeh pass).
3. **Transition vocabulary**, split by an architectural line:
   - *In-scene, parity-preserving*: hard cut, flash cut (exists), whip-pan cut
     (accelerate, cut mid-smear), and **match cut as a compiler constraint** —
     shot N's exit framing must equal shot N+1's entry framing; the solver can
     verify it, turning the strongest cohesion device in film into a checkable
     property.
   - *Composited*: dissolve/wipe via two render targets blended on a
     fullscreen quad, mix a function of `t` — pure, costs a second render on
     transition frames only. (An ffmpeg-`xfade` edit-decision-list in
     `build.js` is the mp4-only power alternative; it forks MP4 from HTML, so
     it stays opt-in and clearly labeled.)
4. **Cut rhythm** as a parameter (average shot length, cut-on-action vs
   cut-on-rest) — a huge fraction of perceived vibe is this one number.

Vocabulary enters the compiler only after a film needed it: v1 is the solver,
the six sizes, three moves, two cut types. Orbits, match-cut constraints, and
dissolves earn their way in.

Semantics-axis upgrade for method.md: a shot list makes "why this shot?" a
reviewable authorial decision per beat, alongside "cover the caption."

Gate: a five-shot film authored entirely through `SHOTS` — zero hand-written
camera keyframes — including one match cut verified by the solver and one
whip-pan transition.

## Phase 4 — Style bibles and cast/set reuse

"Vibe" is every layer making consistent choices. A style bible is one
reference file that constrains all of them at once — palette and material
finish, lens set, framing rules, camera energy, cut rhythm and transition
vocabulary, easing temperament, texture/grain, caption typography. Descriptive
names (`planimetric-pastel`, `neo-noir`, `saturday-cartoon`,
`documentary-handheld`), never director names.

1. **Bible spec + 2-3 bibles**, each one page, each with a spiked frame.
2. **The control pair** (this phase's gate and its reason to exist): the same
   `BEATS` + cast rendered under two bibles must produce two categorically
   different films with zero beat or geometry edits. If a bible swap does not
   visibly change the film, the layers are not actually separated — that
   result would be a Phase 1-3 bug report, and finding it is the point.
3. **CAST/SET as reusable modules** — a character defined once (rig recipe,
   costume, motion idioms) and referenced by name from shots and blocking.
   Deliberately informal until a second film actually reuses a character;
   promoting it earlier is speculative abstraction.

## Phase 5 — Production extensions (opt-in, demand-driven)

Each of these is designed, none is built until a real film demands it — the
same discipline that has audio.md sitting unwired today.

- **Asset vendoring** (`build.js vendor-assets`): base64-embed a CC0 GLB or
  HDRI into the bundle. Keeps single-file/offline/deterministic
  (`sceneReady` already exists to gate on load). Relaxes the "no files" rule
  per scene, opt-in; bundle-size cost hits the HTML artifact, not the MP4
  path.
- **`build.js bake`**: the film-industry answer to the simulation ban. Run
  cloth/particles/ragdoll once at fixed timestep as a build step, write
  sampled results into the scene as data, play back by interpolation — again
  a pure function of `t`; `smoke.js` still passes. Sim → cache → playback.
- **Audio** (roadmap item 3): narration-drives-timing as designed in
  `references/audio.md` — possible at all because beats are data.
- **`build.js deploy`** (roadmap item 9's forward note): publish the bundled
  HTML scene to Pages / as an Artifact — the only delivery that keeps
  interactivity and sidesteps the raster tradeoff.
- **Path-traced hero frames** (exploratory): deterministic per-frame-seeded
  path tracing for still/short "money shots"; offline capture makes slow
  affordable, parallel capture makes it tolerable.

---

## Back-to-back execution mode

The phase contents above hold; four sequencing/scoping choices change when
the phases run continuously instead of demand-driven.

1. **Parallel frame capture moves to Phase 0/1.** Its "low priority, add
   anytime" verdict (roadmap item 5) assumed occasional films on local
   hardware GL. Back-to-back, render-look-edit is the inner loop for the
   whole effort and Phase 2's post chain multiplies the ~1 fps software-GL
   floor. Infrastructure that cheapens every subsequent iteration ships
   first; it touches no scene code, so pulling it forward is risk-free.
2. **Two persistent proving threads instead of a film per phase.** A 2D
   diagrammatic thread (born in Phase 1) and a 3D character thread (born in
   Phase 2, gains shots/editorial in Phase 3, becomes the Phase 4 control
   pair). Gates attach to the threads' milestones rather than to fresh
   throwaway films. Two threads, never one: a single evolving film would
   overfit the system to itself — the disease this whole plan exists to cure.
3. **Order is fixed: 0 → 1 → 2 → 3 → 4.** The 1↔2 swap option is for
   appetite-driven pacing only. Running continuously, the kernel must be
   extracted (Phase 1) before Phase 2 piles post-chain and quality-tier churn
   onto the 3D template — extracting shared code from a moving target is how
   the extraction goes wrong.
4. **"All phases" means 0-4.** Phase 5 is demand-gated *by design*; building
   bake/asset-vendoring/path-tracing speculatively is exactly the
   overcomplication failure mode. Pull a Phase 5 item into the run only when
   one of the two proving threads concretely hits its need (audio via
   narration-drives-timing is the likeliest candidate).

**Phase-exit checkpoint (mandatory in this mode).** Demand-driven pacing has
natural pauses where observations get harvested; back-to-back momentum blows
through them. Every phase ends with, in order:

- Harvest: new brackets, gotchas, and negative results into `method.md` /
  the style references, and the phase's status into the roadmap ledger.
- Release: cut the plugin version (the cascade), so history stays bisectable
  per phase instead of one mega-release at the end.
- Regress: re-shoot the fixed sample timestamps of every committed example
  and compare (byte-identical or the PSNR technique in `method.md`); a phase
  may not open while a prior phase's example renders differently unexplained.
  *(Annotation 2026-07-22: byte-identical holds only **within one renderer** —
  Metal vs SwiftShader is 0/288 identical at PSNR 57-58 dB. Change GL backends
  and this step must fall back to PSNR. And it compares one viewport: see
  "After the run".)*
- Prune: anything built this phase that the proving threads did not use gets
  removed before the next phase starts, not "kept for later."

---

## Cross-cutting rules (all phases)

1. **Every phase gates on a real film**, not on code review — the repo's own
   "build the control" applied to architecture. What the proving film did not
   need does not ship.
2. **Tooling talks only to the window contract.** If a phase tempts a tool to
   parse scene internals, the contract is missing an export (the `window.BEATS`
   precedent) — extend the contract instead.
3. **New perceptual rules ship with brackets** — an observation on each side
   or an honest "unbracketed, single observation" label, per method.md's
   existing standard. New instruments ship with a verified positive control.
4. **Determinism red lines per phase**: no temporal post passes; shared
   materials restated every frame; sims baked, never live; quantized time and
   seeded noise are pure — use them freely.
5. **Version cascade** fires on every phase that touches `templates/`,
   `references/`, or `examples/` (CLAUDE.md invariant 1) — which is all of
   them except this document.
6. **Duration stays the user's spec input; nothing in any phase assumes
   long-form.** "Film language" here means craft density, not runtime: the
   shot vocabulary, editorial grammar, and style bibles must read correctly
   on a 10-second three-shot explainer exactly as on a 40-second piece —
   `duration_s` and the beats table remain the only place length exists,
   set per spec by what the content needs. Every proving film in this plan
   is explainer-scale (the 15-40s SKILL.md pacing guidance), and a phase
   deliverable that only works at length is overfit and fails its gate.
