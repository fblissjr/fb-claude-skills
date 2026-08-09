# Attaching media: routing, formats, resolution, cost

What happens to a file between `-f` and the model, for every modality. For
call parameters see `api.md`; for video specifics see `video.md`.

## One call, any mixture

A request carries as many attachments as the question needs, in **any
combination of kinds**: eight screenshots, or a video plus the two mockups it
should match plus a PDF spec, or an audio track alongside the frames it
belongs to. Each file is routed on its own kind, independently, inside the one
request — so a mixed set costs one call, not one call per modality. Attachment
order is preserved and the question is appended last.

The only per-kind differences are the ones below: how a file travels, and
whether it carries a resolution. Neither is something you select.

## The routing rule

Two ways a file reaches the API, and you do not choose between them:

| Kind | How it travels | Why |
|---|---|---|
| image | inline base64 | verified, no upload step, nothing left behind |
| document (PDF, CSV) | inline base64 | same |
| **video** | **uploaded, sent as a uri** | the only shape verified live |
| **audio** | **uploaded, sent as a uri** | same road as video |
| anything over ~70MB | **uploaded**, whatever its kind | past the inline cap |

Video is uploaded even when it is tiny. That is a verification decision, not a
size one: the SDK types say a video block accepts inline `data`, but only the
uri shape was ever probed, and a size threshold would send the smallest
files — the first thing anyone tests with — down the unproven path. The size
cap is a *second, independent* reason to upload, which is what makes a 90MB PDF
work.

## Formats

`gemini-bridge formats` prints the accepted mime types per kind, which
extensions get remapped, and the current size limits. It reads the same tables
the code enforces, so it cannot drift; that is why the list is not copied here.

Two things worth knowing before you go looking:

- **The type comes from the file extension**, not from sniffing the bytes. An
  unknown or absent extension is refused before anything is sent.
- **`.mkv` and `.m4v` are not accepted** and are the common surprises.
  `ffmpeg -i in.mkv -c copy out.mp4` remuxes without re-encoding, in seconds.

Python's own mime table disagrees with the API's accepted list in several
places and varies by platform — `.wav` is `audio/x-wav` locally, which the API
rejects. Those are remapped; `formats` shows which.

## Resolution

`--resolution` for subject files, `--context-resolution` for files attached
with `-c`. Values: `low`, `medium`, `high`, `ultra_high`.

**It applies to images and video only.** Audio and document blocks have no such
field (SDK), and the CLI strips it rather than sending a key that would 400.

Resolution is **per content item** — Gemini 3 and later. That is the point of
having two flags: spend tokens on what is being examined, not on the reference
material sitting beside it.

| Media | Setting | Tokens | When |
|---|---|---|---|
| Image | `high` | 1120 | full-frame renders; reading text in the image |
| Image | `medium` | 560 | |
| Image | `low` | 280 | context images that are not the subject |
| Image | `ultra_high` | 2240 | computer use only |
| Video | default / `low` / `medium` | **70 per frame, all identical** | motion, action, scene description |
| Video | `high` | 280 per frame | only when reading text or fine detail in frames |
| PDF | `medium` | 560 | quality saturates here |

Two non-obvious consequences:

- **Video has no cheap tier.** `low` and `medium` are treated exactly like the
  default. The only video decision is 70 vs 280 per frame, a flat 4x, and it is
  worth paying only when the question depends on reading something inside the
  frame.
- **The API's image default is `high`.** The recipes here set `low` because
  that was measured to be better for their cases, not because it is the
  API's default.

### Choosing an image resolution — measured, not guessed

From a control harness over four real image pairs, two runs each, at both
resolutions:

- **`low` is usually right.** On storyboard strips and contact sheets it found
  *more* differences than `high`, not fewer — the extra detail was noise for
  that task.
- **Use `high` for full-frame renders** — a 3D viewport, a full screenshot,
  anything where detail is spread across the whole frame. On a viewport pair,
  `high` found 5–6 differences where `low` found 1. This is the case that
  justifies roughly 3x the input tokens.
- **Use `high` when text in the image matters.** Reading small on-screen text
  is the documented case for it.

## Size and lifetime

| Limit | Value |
|---|---|
| Inline attachment | ~70MB per file (the API caps near 100MB; base64 inflates ~33%) |
| Uploaded file | 2GB |
| Upload quota | 20GB per project |
| Upload lifetime | 48 hours, then deleted automatically |

Uploads and interactions expire on **independent clocks**, so `store=false`
costs you the conversation, not the upload.

## What happens to an upload

1. The file is hashed and checked against the local cache.
2. If a live handle exists, it is confirmed with the server and reused.
3. Otherwise the bytes are uploaded and polled until they leave `PROCESSING` —
   a file is not usable the moment upload returns, and sending its uri early
   fails the interaction after the bytes were already spent.
4. The handle is recorded in the run directory (`uploads.json`) and the cache
   (`upload-cache.json`), before the interaction is attempted.

Reuse is keyed on **content**, so a re-rendered file always gets a fresh
upload — a stale handle can never answer for new bytes. The one staleness a
hash cannot see is server-side, which is why the handle is confirmed live
before reuse.

**An upload is a disclosure that outlives a failed call.** The bytes sit at
Google for 48h whether or not the question that followed them succeeded. That
is why the local record is written first. Unlike stored interactions, uploads
can be taken back:

```bash
gemini-bridge uploads            # what this project is holding, and for how long
gemini-bridge uploads --delete   # remove them now rather than waiting 48h
```

`gemini-bridge doctor` reports the count.

## What the guards do and do not cover

Two guards refuse rather than warn, and both run **before** any file is read or
uploaded:

- **Attached paths** are matched against built-in patterns for secret-shaped
  files plus anything in `.gemini-bridge.toml`.
- **The prompt** is scanned for secret-shaped content, along with the system
  instruction, schema, and label values.

Neither reads attachment contents. A screenshot showing a key, a CSV with a
credential in a cell, or a screen recording that pans past a terminal passes
both checks untouched. **Video is the worst case here** — a two-minute
recording of someone's editor is a hundred-plus frames of whatever was on
screen, and nobody reviews all of them. Say what you are sending before you
send it, and let the user confirm anything recorded off a real desktop.
