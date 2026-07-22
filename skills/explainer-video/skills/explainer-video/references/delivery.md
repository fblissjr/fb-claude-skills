# Delivering inline on GitHub

The delivery forensics: which formats render inline, the measured size and
decode tradeoffs, the encoder settings, and the content-type mechanism with
its evidence chain. Backend-agnostic — everything here operates on shot
frames, whatever rendered them. The method is `method.md`; the 3D cookbook is
`style-3d.md`.

GitHub renders animated WebP and GIF inline, and — per one confirmed
still-image fetch plus one real-world report, see below — animated AVIF as
well. It does **not** render a repo-relative mp4 as a player, and it strips
`<script>`, so the HTML artifact is inert on github.com (Pages or a published
Artifact both run it fine).

The HTML scene is a fourth, co-equal delivery option alongside mp4, WebP and
AVIF — not a footnote to them. It is the interactive, deterministic source
itself, not a rendering of it: `build.js bundle` makes it a single
self-contained file that runs offline, and it plays fine served from GitHub
Pages or published as an Artifact. It does not run from github.com directly,
for the `<script>`-stripping reason above. A `build.js deploy` helper to
automate that publish step is a plausible future addition; it does not exist
yet.

WebP's cost is driven by how much of the frame changes per frame, which makes
the camera decision a file-size decision for WebP. AVIF does not have that blind
spot — it is cheap on both camera styles — but it buys the smaller file with a
cost that does not show up in a size table, so read the tradeoff below before
reaching for it.

| Scene | 12s template, 960px/24fps, moving camera | 11s held-camera diagram, 720px/12fps |
|---|---|---|
| mp4 | 0.52 MB | 0.23 MB |
| gif | 12.08 MB | — |
| webp | 15.56 MB | 0.20 MB |
| **avif** | **0.28 MB** | **0.029 MB** |

(A second measurement run reproduced this benchmark on the moving-camera case —
mp4 0.68 MB, webp 15.16 MB — close enough to the figures above to trust the
avif row as directly comparable to the rest of the table.)

AVIF is ~54x smaller than WebP on the moving-camera scene and ~7x smaller on
the held-camera one, and it beats the mp4 on both. Sway (`CONFIG.sway = 0.06`,
every pixel changing every frame) is what makes WebP expensive; AVIF does not
have the same blind spot.

### The size win costs decode at playback

This is the cost the table does not show, and it is the input that keeps this a
genuine tradeoff rather than a size contest. An animated AVIF is an **AV1
still-image sequence**, not a video stream: browsers and viewers decode it
frame by frame in software, and it does not get the hardware video-decode path
an mp4 gets. Animated WebP decode is far lighter. So the 29 KB AVIF that beats
a 200 KB WebP on disk can be *heavier to play* than the WebP it replaced — a
real cost to weigh against the size win, not a disqualifier.

This is observed, not just predicted. The repo owner watched the committed
animated AVIF play back with visible slowness, worse in macOS Preview than in
Chrome — i.e. the same file decodes at different costs in different decoders, and
the cost is high enough to see. Decode load scales with the viewer's machine, so
a weak or busy one will drop frames on the AVIF while the WebP plays smoothly.
One machine, two decoders — directional and consistent with the architecture,
not a mapped threshold. It is exactly the axis the size measurement was blind to:
bytes-on-disk and decode-cost-at-playback are different costs, and optimizing the
first said nothing about the second.

**The decode lever is resolution, not the encoder.** Because the player
software-decodes every AV1 frame live, the decode budget is
`width x height x fps` — pixels per second the viewer's machine must sustain. So
dropping the resolution buys smoothness directly: 1280→960 cuts the budget ~44%
(28 → 15.5 Mpx/s), and GitHub renders README images at well under native width
anyway, so the drop is invisible where it matters. A lower-resolution AVIF was
observed playing smoothly where a wider one stuttered — but on a capable machine.
**Whether any resolution stays smooth on genuinely low-end hardware is the open
question, not a settled result** — a real unknown to weigh when choosing
between a controlled-resolution AVIF and WebP.

Prefer cutting **resolution over frame rate**. On a moving-camera piece the fps
carries the motion cadence, and lowering it reintroduces judder — a different
defect than the decode stutter you were fixing. The command's `[width]` argument
is the lever; the default 720 is deliberately conservative on decode. The
encoder `-s` knob does **not** help — it trades encode time for file size and
leaves the bitstream's pixel throughput, which is what costs decode, unchanged.

There is a clean symmetry here: an AVIF software-decodes and an mp4
hardware-decodes, which is the same split that makes the mp4 play smoothly
everywhere *and* refuse to embed. Resolution is a playback cost for AVIF exactly
because it never touches the hardware path.

So this is a genuine tradeoff between two peer options, decided by context —
neither is the default:

- **WebP** — larger on disk (ruinous on a moving camera), but decodes cheaply
  and smoothly on any hardware, and its inline rendering on GitHub is the
  verified case. A reasonable pick when the audience hardware is unknown or
  weak, or when a moving camera isn't in play.
- **AVIF** — dramatically smaller on disk, lifts the held-camera constraint, and
  its decode cost is tunable by resolution (above). What is *not* yet confirmed
  is whether a controlled resolution stays smooth on genuinely low-end
  hardware — that test is still open. A reasonable pick when size or bandwidth
  matters most and the audience skews toward capable hardware; watch it on a
  low-end target in the browser you will embed for before relying on it there.

Holding the camera to fit a WebP loop under the 10MB inline cap is still a real
constraint if you ship WebP. AVIF removes it — at the playback cost above.

`loop` needs `img2webp` (`brew install webp`). Homebrew's ffmpeg ships without
libwebp, so `-c:v libwebp` fails with "Encoder not found".

## Encoding AVIF

```bash
bun run build.js avif <scene.html> [fps] [width]   # <name>.avif — defaults fps 12, width 720, same shape as loop
```

Under the hood: `avifenc --fps <fps> -q 60 -s 6`. Speed 6 is the measured knee
— `-s 8` gave 2.3x larger files for one second less encode time, `-s 4` gave no
further size gain for double the time. Encode cost is 11s for 288 frames,
negligible against a 65s shoot.

Visual check: decoded frames inspected by eye — crisp text, smooth gradients,
no blocking — and SSIM 0.97 against the source frames.

`avif` needs `avifenc` (macOS: `brew install libavif`), the exact parallel of
`img2webp` for `loop`.

## Why WebP (and, provisionally, AVIF) embed and mp4 does not

It is a content-type allowlist, not a markdown-syntax problem. Verified by
fetching from the URL a repo-relative reference resolves to:

| committed file | `raw` Content-Type | result |
|---|---|---|
| `.webp` | `image/webp` | renders inline; `ANIM`/`ANMF` chunks arrive intact |
| `.avif` (still) | `image/avif`, nosniff present but irrelevant since the type is correct | same allowlist mechanism as WebP, confirmed by fetch |
| `.mp4` | `text/plain; charset=utf-8` + `nosniff` | inert — no browser will treat it as media |

`<video>` being stripped from GFM is a second, independent block on the mp4 path.
Both have to be true for the workaround (an issue/PR attachment URL) to be the
only route to a player.

**The `.avif` row in THIS table was fetched as a still image.** Not the AVIF row
in the size table further up — those files are animated, verified at 132 and 288
frames with `avifdec --info`. The distinction matters because only one half of
the AVIF delivery path is actually confirmed:

| link in the chain | status |
|---|---|
| AVIF encodes small enough to ship inline | **measured** — 0.28 MB moving-camera, 0.029 MB held |
| the files are genuinely animated, not collapsed stills | **verified** — `avifdec --info` reports 132/288 frames, infinite repeat |
| GitHub serves `.avif` as `image/avif`, passing the allowlist | **verified by fetch** — but against a *still* |
| GitHub's image pipeline passes an *animated* AVIF through and it plays | **one real-world observation** |

That last row is the whole of the evidence: the repo owner committed an animated
AVIF and reported it renders and animates inline. Record it as exactly that — a
single confirming observation, not a bracket, and not the same class of evidence
as the fetch that backs the row above it.

An animated `.avif` is now committed beside the example specifically so this is
cheap to close: pointing the README's image at it is a one-line change, and
viewing the rendered README settles the last row either way. It is committed as
a peer delivery option and as the experiment that would settle the AVIF-inline
question — the README currently points its hero image at the WebP, the case
with real verification behind it; re-pointing it at the AVIF and writing down
what happens is the open follow-up.

Two traps that follow, plus one browser-support caveat:

- **Never track the loop under Git LFS.** `raw` returns the pointer file rather
  than the image and the README shows a broken image. This catches most repos
  that ship demo media.
- **Animated GIF, WebP and AVIF are all silent.** There is no format that gives
  inline motion *with audio* in a README. Audio requires the attachment player,
  which means the narration path and the inline path are different artifacts.
- **Animated AVIF is expensive to decode; WebP is not.** See "The size win
  costs decode at playback" above — this is a viewer-hardware cost, observed,
  and a real input to weigh against AVIF's size win.
- **Animated AVIF needs a newer browser than animated WebP.** Where the
  audience's browser is old or unknown, that argues for WebP; its numbers, and
  the fact that it renders and animates inline, are the well-verified ones in
  this file.

APNG is unverified — the issue-composer upload rejects `.apng`, and whether a
committed `.png` carrying APNG frames animates is undocumented. Do not rely on it
without testing.
