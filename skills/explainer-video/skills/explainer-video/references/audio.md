# Audio extension (designed, not yet wired)

The deterministic architecture makes audio a pure post-step: the beats table
already IS the narration script and the cue sheet. Nothing in the scene file
needs to change to add sound later — which is why this is a reference doc, not
template code.

## Design

Add an `audio` block to the spec, keyed to the same beats:

```yaml
audio:
  mode: narration-drives-timing   # default; or `fixed` to keep beat durations
  narration:            # one clip per named beat, or one continuous track
    - {beat: scan, text: "The pulse leaves the first station...", voice: "..."}
  music: {file: bed.mp3, gain_db: -18, duck_under_narration: true}
  sfx:
    - {t: 4.95, file: pop.wav}      # timed to animation events, e.g. the drop
```

## Pipeline (all ffmpeg, no scene changes)

1. **Narration**: generate per-beat clips with any TTS (macOS `say -o`, cloud
   TTS, recorded voice). Under the default `narration-drives-timing`, measure
   each clip with `ffprobe` and write the duration back into that beat's `dur`
   in `BEATS` — which is possible only because beats are named data. Under
   `mode: fixed`, keep the authored durations and treat a clip that overruns its
   window as an error. Prefer retiming the film to rushing the voice.
2. **Assemble the track**: place clips at their beat offsets on a silent base:
   `ffmpeg -f lavfi -i anullsrc=r=48000:cl=stereo -t <dur>` plus one
   `adelay=<t0*1000>` per clip, mixed with `amix`. Music bed via `amix` with
   `sidechaincompress` if ducking.
3. **Mux**: `ffmpeg -i video.mp4 -i track.wav -c:v copy -c:a aac -shortest out.mp4`
   — video stream untouched, so audio iterations never re-render frames.
4. **HTML version**: embed the same track as a base64 `<audio>` element; the
   driver already knows `t`, so sync is `audioEl.currentTime = t` on seek and
   plain play() during the rAF loop. Add only when actually needed.

## Why not bake audio into the scene file now

Silent-by-default keeps the artifact self-contained and small, TTS choice is a
user decision (voice, language, license), and the mux step is trivially
separable. When the first real narration request lands, implement steps 1-3 as
`build.js audio <scene.html> <audio-spec.yaml>` and keep the contract: the
beats table is the single source of timing truth.
