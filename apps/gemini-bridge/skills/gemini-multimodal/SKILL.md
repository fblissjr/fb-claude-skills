---
name: gemini-multimodal
description: Send a task to a Gemini model and get a structured answer back - perceptual work Claude cannot do directly, or any ad-hoc question worth a second model's take. Handles images, video, audio, and PDFs, singly or mixed in one call. Use when comparing two renders or screenshots to find visual differences, when checking that a change had no visual effect, or when a visual question is being answered with pixel math, histograms, or diff statistics because looking at the images is not working. Use for anything involving a video or audio file, which Claude cannot open at all - "watch this video", "what happens in this screen recording", "turn this recording into code", "transcribe this audio". Also use when the user says "ask Gemini", "have Gemini compare these", "send this to Gemini", or names Gemini alongside a question or file. Calls need no recipe - model, thinking level, system prompt, and schema are all settable per call. Every call is an explicit, billed external request that leaves a run directory on disk.
---

Hand a perceptual task to a Gemini model when direct inspection is not working.

Two signals that this skill applies. The first is a hard capability wall: **there is a video or audio file in the task.** You cannot open either, and `ffprobe` metadata is not a substitute for watching it. The second is subtler and more common: **reaching for numpy, histograms or pixel-diff statistics to answer a question about what something looks like.** Mean squared error between two renders is not an answer to "did this change anything visible."

<before_calling>
Every call spends money and sends the attached files to Google, where they are retained for the project's window and cannot be deleted through the API.

- **Say what you are sending** in one line — the files and the recipe — before running the command. The CLI prints the full manifest to stderr before anything leaves the machine; your line is the intent, its manifest is the record, so leave stderr in view.
- **`--dry-run` first** when the attachment set is large or unfamiliar. It prints the same manifest and a cost estimate, says whether the call would be gated, and opens no connection.

Two guards refuse automatically: every path you name (`-f`, `-c`, `--prompt-file`, `--system-file`, `--schema-file`, `-r` as a path) is matched against secret-shaped patterns plus `.gemini-bridge.toml`'s list before it is opened, and the prompt is scanned for secret-shaped content. You compose the prompt after reading the user's files, so write questions that describe rather than quote key material. If a prompt refusal is a false positive, tell the user and let them decide on `--allow-prompt-secrets`.

**Neither guard reads attachment contents.** A screenshot showing a key, or a CSV with a credential in a cell, passes both. Before sending a screenshot of a terminal, editor or browser, or any document you did not generate, say so and let the user confirm.
</before_calling>

<how_to_run>
Every call is `gemini-bridge ask`; the recipe and the question are what change.

| Task | Start with |
|---|---|
| Compare renders or screenshots | `-r perceptual-diff -f before.png -f after.png` |
| Anything involving a video | `-r video-analysis -f clip.mp4` + a specific question |
| Ask about images or PDFs | `-r general -f page.png ...` + the question |
| Transcribe or describe audio | `-f take.wav` + what you need from it |
| A stance no recipe covers | no `-r`; `--system` / `--system-file` |
| Text-only second opinion | no `-r`, no `-f`, just the question |

**Ask once with everything attached.** `-f` is repeatable and kinds mix freely — six screenshots, or a video plus the two mockups it should match plus the PDF spec. Each file is routed by kind (images and PDFs inline, video and audio uploaded), order is preserved, and the question goes last. Use `-c` instead of `-f` for *reference* rather than *subject*: it rides at the cheaper resolution, which is the main way a multi-file call stays affordable.

```bash
gemini-bridge ask -r perceptual-diff \
  -f before.png -f after.png \
  "Compare these two renders. The first is BEFORE a change, the second is AFTER."

# mixed: the recording is the subject, the mockups are reference
gemini-bridge ask -f recording.mp4 -c mock-a.png -c mock-b.png \
  --resolution high --context-resolution low \
  "Where does the implemented flow diverge from either mockup?"
```

stdout is deliberately small: run path, status, token counts. **Read the answer from the run directory** — `response.json` for the structured verdict, `response.md` for prose — because tool output stays in context for the rest of the session.

| Flag | Use |
|---|---|
| `-f` / `-c` | subject file / context file at the cheaper resolution, both repeatable |
| `--resolution` | override the recipe (`low`, `medium`, `high`, `ultra_high`); images and video only |
| `--dry-run` | print what would be sent, call nothing |
| `--prompt-file` | read the question from a file |
| `--upload-timeout` | seconds to wait for video or audio processing |

Other subcommands: `recipes`, `formats` (what can be attached and how), `doctor` (credentials, config, gate health), `stats`, `stored` and `uploads` (what is held server-side).
</how_to_run>

<budget>
**The defaults are the cheap ones** — Flash, `thinking_level: minimal`, default media resolution — and they stay unless someone decides otherwise. Good enough is the default on purpose; perfect is a decision the user gets to make. What costs money is how much media you attach; `--dry-run` estimates it and `usage.json` records the exact count.

When the user has said what they want, or you are answering their question about a file they just handed you, go ahead. When a call is about to be expensive and you are choosing on their behalf, put the choice to them with real options and real numbers, recommend one, and make the cheap option the default:

> This recording is 8 minutes (~34k input tokens). I can:
> **(a)** trim to the 00:40–01:10 window you described (~2k),
> **(b)** send the whole thing at default resolution (~34k),
> **(c)** send it all at `high` for readable on-screen text (~134k).
> Default is (a) unless you'd rather I look wider.

Worth asking about: video over a couple of minutes, `--resolution high` across several files, switching to Pro, raising `--thinking-level`, and `--store`.

**The spend gate.** Above the per-call threshold (`max_unauthorized_tokens`), or with `--store`, `--thinking-level medium|high`, or a large `--max-output-tokens`, the CLI refuses unless the user has typed `/gemini-bridge:gemini-authorize`; the same applies once this session's cumulative spend passes `max_session_tokens`. `gemini-bridge doctor` prints both thresholds as configured. The estimate includes the question and system instruction, so a very large `--prompt-file` is gated on its own. Nothing you can run mints the authorization — that is the point of it.

On a refusal, the user decides: tell them what you wanted to send, what it would cost and what you expected to learn, then stop. The alternative that needs no authorization is the cheaper call the refusal suggests — a trimmed clip, fewer files, a lower resolution — when it still answers the question. The gate's settings and scope belong to the user: keep the call the size the question needs rather than splitting it under the threshold, and leave `.gemini-bridge.toml`'s `[authorization]` section and `TMPDIR` as they are. If `doctor` reports the gate as BROKEN (`jq` missing, an unreadable session id), tell the user; in that state no call can be authorized.
</budget>

<ad_hoc>
`-r` is optional. For a text-only question, a one-off stance, or a schema invented for this task:

```bash
gemini-bridge ask --model gemini-pro-latest --thinking-level high \
  "Critique this design: ..."

gemini-bridge ask --system-file stance.md --schema-file verdict.json \
  -f page.png "Does this match the spec?"
```

Every recipe parameter is a flag (`--thinking-level`, `--seed`, `--max-output-tokens`, `--service-tier`, `--schema-file`, `--label k=v`, `--store`); precedence is flag > recipe > default, and the run is labeled `adhoc`.

- Thinking still defaults to `minimal`; when you raise it, say why.
- `--store` opts into server-side storage, which `--continue-from` requires and which cannot be deleted. One-shot questions run unstored.
- `--system` / `--system-file` do not combine with `-r`, because a run labeled with a recipe's name must carry that recipe's stance. An ad-hoc stance that proves itself twice becomes a recipe file, versioned instead of retyped.
</ad_hoc>

<video_and_audio>
Attaching either uploads the file and sends a reference to it. In the order they bite:

1. **The prompt is where the quality is.** A video with no context returns a plot summary. Say what the file is, what decision the answer feeds, what to ignore and what shape the answer takes. Use `-r video-analysis` for the ordinary stance and spend the effort on the question. A bare attachment with no question runs a generic default and warns; it exists so the call is not refused, not as a way to use this.
2. **The upload is a disclosure with a 48-hour life.** Neither guard reads inside it — a two-minute screen recording is a hundred-plus frames of whatever was on that desktop. Uploads can be taken back (`gemini-bridge uploads --delete`), unlike stored interactions. Identical bytes upload once, so follow-up questions on the same file are cheap.
3. **It is slow, and length is the cost.** Upload and processing can outrun a default Bash timeout; give the command more time, and raise `--upload-timeout` if processing is what runs long.

Frames are sampled at 1 FPS and the API has no clip, offset or fps control, so trim with ffmpeg rather than paying for ten minutes to ask about fifteen seconds, and expect sub-second events to be missed. ffmpeg one-liners, worked examples, per-minute cost and when to send frames instead: `references/video.md`.
</video_and_audio>

<resolution>
One rule per modality; the measured evidence and token table are in `references/media.md`.

- **Images: `low` is usually right**, and on storyboards and contact sheets it measurably beat `high`. Go `high` for full-frame renders, where detail spreads across the frame, and whenever in-image text matters.
- **Video: leave it alone unless there is text to read.** `low`, `medium` and the default cost the same per frame; `high` is a flat 4x.
- **Audio and PDFs take no resolution**; the CLI strips the field rather than sending a key that would 400.
</resolution>

<verdict>
`perceptual-diff` returns `{identical, confidence, differences[]}`; each difference carries `region`, `kind`, `description`, `severity`.

- **`identical: true` is a real result.** The recipe is built to confirm that a change had no visual effect, and it produced no false positives against null pairs (an image compared with itself).
- **Route on `identical` and `differences`, not `confidence`.** It did not vary across the control runs, so it carries no information yet; it is recorded, not acted on. `scripts/diff_control.py` reproduces those runs.
</verdict>

<constraints>
- **No `temperature`.** The API accepts and silently ignores it; recipes reject it. Use `seed` for reproducibility.
- **Storage cannot be undone.** `interactions.delete` returns HTTP 501, so anything stored persists for the retention window. Every recipe is `stateful: false` unless the task needs follow-up turns.
- **Thinking bills at the output rate**, and an unset level is the expensive path; recipes set `thinking_level: minimal`.
</constraints>

<recipes>
A recipe fixes the stance; the caller supplies the question. That keeps the stance versioned and diffable, and with a pinned `seed` and model two runs are comparable. A recipe is a markdown file — YAML frontmatter for parameters, body for the system instruction — and needs no code change; copy the shape of `references/recipes/perceptual-diff.md`.

Before trusting a new comparison recipe, run it on a **null pair**: the same file twice. A recipe that reports differences between an image and itself is worse than none, and the failure is invisible when it is only tested on inputs that genuinely differ. `scripts/diff_control.py` runs that control.
</recipes>

<references>
Read the relevant one before the first call of a kind you have not made before.

| Reference | Read it for |
|---|---|
| `references/api.md` | models, thinking, seed, structured output, storage, service tiers, token accounting, what the API and CLI deliberately do not expose, source URLs |
| `references/media.md` | how each modality is attached, formats, resolution and token cost per kind, size limits, what the guards miss |
| `references/video.md` | video and audio end to end: the 1 FPS constraint, ffmpeg prep, worked examples, when video is the wrong tool |
</references>
