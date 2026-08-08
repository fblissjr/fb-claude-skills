# Video and audio

Read this before sending a video. Two constraints below change what you should
send, not just how you send it.

## What happens when you attach a video

`gemini-bridge ask -f clip.mp4 "..."` uploads the file to the Files API, waits
for it to finish processing, and sends a reference to it. You do not opt into
this and there is no flag for it — video and audio always take that route,
because it is the only shape verified against the live API.

Consequences worth knowing before the first call:

- **The upload is a disclosure.** The bytes are at Google for 48 hours whether
  or not the question that followed them succeeded. Unlike a stored
  interaction, an upload can be deleted: `gemini-bridge uploads` lists what
  this project is holding there, `gemini-bridge uploads --delete` removes it.
- **Identical bytes upload once.** The handle is cached by content hash for
  the 48h window and confirmed with the server before reuse, so asking five
  questions about one recording costs one upload. Edit or re-render the file
  and the hash changes, so a stale handle can never answer for new bytes.
- **It is slow.** A large upload plus processing can exceed a default 120s
  Bash timeout. Raise the tool timeout for long clips, and raise
  `--upload-timeout` (default 300s) if processing is the part that runs long.
- Limits: 2GB per file, 20GB per project.

## Sampling is fixed at 1 FPS, and there is no clipping

The Interactions API exposes **no fps, no start offset, no end offset**. The
legacy `video_metadata` field is explicitly unavailable here. That is not a gap
in this tool; it is the API surface.

Two things follow, and both are yours to handle before the file is attached:

**Anything faster than about a second may not be sampled at all.** A one-frame
flash, a 200ms transition, a single dropped frame — the model may never see it.
If the question is about something that fast, video analysis will not answer it;
extract the frames yourself and send them as images.

**You pay for the whole clip.** There is no way to ask about seconds 40–55 of a
ten-minute recording other than sending ten minutes. Trim first:

```bash
# seconds 40 to 55, no re-encode, near-instant
ffmpeg -ss 40 -to 55 -i recording.mp4 -c copy clip.mp4

# downscale a screen recording that does not need full resolution
ffmpeg -i recording.mp4 -vf scale=1280:-2 -c:v libx264 -crf 28 clip.mp4

# drop the audio track when the question is purely visual
ffmpeg -i recording.mp4 -an -c:v copy clip.mp4
```

The CLI deliberately does not run ffmpeg for you. A transcode is lossy,
slow, and silently destructive, and doing it inside an attach would mean the
bytes analysed are not the bytes you named.

## Resolution

For video there is no cheap tier: `low`, `medium`, and the default all cost the
same 70 tokens per frame. `high` costs 280 — a flat 4x, worth paying **only**
when the question depends on reading text or fine detail inside the frame.

So the whole decision is: is there text to read? If not, leave it alone.

## Writing the question

This is where the quality actually comes from, and it is the part no default
can supply. You know what the recording is of, what change it is meant to
demonstrate, and what the answer feeds into. The model knows none of that.

A question with no context gets a plot summary. Give it:

- **What the file is** — "a screen recording of our checkout flow", "a render
  turntable of the same asset before and after a shader change".
- **What decision the answer feeds** — "I am trying to find where the layout
  reflows", "I need to reproduce this animation in CSS".
- **What to ignore** — "the recording software's cursor highlight is not part
  of the UI", "ignore the first three seconds, that is me clicking record".
- **The output shape you want** — a timeline, a list of defects, a set of
  timestamps, JSON against a schema.

Pair it with `--system` when the stance matters more than the question does:

```bash
gemini-bridge ask -f flow.mp4 \
  --system "You are reverse-engineering a UI interaction so it can be
rebuilt in HTML and CSS. Report geometry, timing, and easing as
concretely as the footage allows. State when a value is inferred rather
than observed, and never round a duration to a nice number to make it
look confident." \
  "Trace the drawer open animation. For each stage give the timestamp,
what moves, how far, and roughly how long it takes."
```

If you attach media and give no question at all, the CLI runs a generic
default and warns you. That path exists so a bare call is not refused, not
because it is a reasonable way to use this.

## Audio

Same road: uploaded, referenced by uri, and it carries no `resolution` (the
audio content type has no such field). Ask for timestamps and speaker labels
explicitly if you want them.

The API also has a `transcription_config` — word-level timestamps, speaker
diarization, custom vocabulary — which this CLI does **not** expose yet. For
now, ask for those in the prompt and accept that they are the model's estimate
rather than a transcription feature's output.
