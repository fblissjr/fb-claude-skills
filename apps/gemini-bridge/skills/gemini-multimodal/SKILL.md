---
name: gemini-multimodal
description: Send a task to a Gemini model and get a structured answer back - perceptual work Claude cannot do directly, or any ad-hoc question worth a second model's take. Handles images, video, audio, and PDFs, singly or mixed in one call. Use when comparing two renders or screenshots to find visual differences, when checking that a change had no visual effect, or when a visual question is being answered with pixel math, histograms, or diff statistics because looking at the images is not working. Use for anything involving a video or audio file, which Claude cannot open at all - "watch this video", "what happens in this screen recording", "turn this recording into code", "transcribe this audio". Also use when the user says "ask Gemini", "have Gemini compare these", "send this to Gemini", or names Gemini alongside a question or file. Calls need no recipe - model, thinking level, system prompt, and schema are all settable per call. Every call is an explicit, billed external request that leaves a run directory on disk.
metadata:
  last_verified: "2026-08-01"
  freshness: "cascade"
---

Hand a perceptual task to a Gemini model when direct inspection is not working.

Two signals that this skill applies. The first is a hard capability wall:
**there is a video or audio file in the task.** You cannot open either, and no
amount of `ffprobe` metadata substitutes for watching the thing.

The second is subtler and more common: **reaching for numpy, histograms, or
pixel-diff statistics to answer a question about what something looks like.**
That substitution is the symptom. Comparing two renders and reporting mean
squared error is not an answer to "did this change anything visible."

## Before calling

Every call spends money and sends the attached files to Google, where they are
retained for the project's window and **cannot be deleted through the API**.
Two things to do:

1. **Say what you are sending.** Name the files and the recipe in one line
   before running the command.
2. **`--dry-run` first** when the attachment set is large or unfamiliar. It
   prints the manifest and calls nothing — it opens no connection, so nothing
   leaves the machine.

Two guards run automatically and refuse the call rather than warning:

- **Attached paths** are matched against built-in patterns for secret-shaped
  files plus anything configured in `.gemini-bridge.toml`.
- **The prompt** is scanned for secret-shaped content. This one matters most
  here, because *you* compose the prompt after reading the user's files. Do not
  paste key material, tokens, or credential blocks into a question. If a refusal
  is a false positive, say so and let the user decide rather than reaching for
  `--allow-prompt-secrets` yourself.

Neither guard is a substitute for judgement about what belongs in the question.

**Neither one reads attachment contents.** A screenshot showing a key, or a CSV
with a credential in a cell, passes both checks -- the path guard sees a
filename, the scanner reads only the prompt. If you are about to send a
screenshot of a terminal, an editor, or a browser, say so and let the user
confirm. The same goes for any document you did not generate yourself.

## Where to start, by task

Every call is `gemini-bridge ask`. It takes any modality; the recipe and the
question are what change.

| Task | Start with |
|---|---|
| Compare renders or screenshots | `-r perceptual-diff -f before.png -f after.png` |
| Anything involving a video | `-r video-analysis -f clip.mp4` + a specific question |
| Ask about images or PDFs | `-r general -f page.png ...` + the question |
| Transcribe or describe audio | `-f take.wav` + what you need from it |
| A stance no recipe covers | no `-r`; `--system` / `--system-file` |
| Text-only second opinion | no `-r`, no `-f`, just the question |

**`-f` is repeatable and the kinds can be mixed freely.** One call takes as
many files as the question needs, in any combination — six screenshots, or a
video plus the two mockups it is supposed to match, plus the PDF spec. Each
file is routed on its own kind (images and PDFs inline, video and audio
uploaded), attachment order is preserved, and the question goes last. Nothing
here is one-file or one-modality per call, so do not split a question into
several calls that would have been better asked once with everything attached.

Use `-c` instead of `-f` for anything that is *reference* rather than
*subject* — it rides at the cheaper resolution, which is the main way a
multi-file call stays affordable.

```bash
gemini-bridge ask -r perceptual-diff \
  -f before.png -f after.png \
  "Compare these two renders. The first is BEFORE a change, the second is AFTER."

gemini-bridge ask -r video-analysis -f flow.mp4 \
  "At what timestamp does the list first render duplicate rows?"

# mixed: the recording is the subject, the mockups are reference
gemini-bridge ask -f recording.mp4 -c mock-a.png -c mock-b.png \
  --resolution high --context-resolution low \
  "Where does the implemented flow diverge from either mockup?"
```

stdout stays small on purpose: run path, status, token counts. **The answer is
in the run directory** — read `response.json` for the structured verdict, or
`response.md` for prose. Do not ask the CLI to print the whole answer; tool
output stays in context for the rest of the session.

Useful flags:

| Flag | Use |
|---|---|
| `-f` | subject file, repeatable |
| `-c` | context file, attached at the cheaper resolution |
| `--resolution` | override the recipe (`low`, `medium`, `high`, `ultra_high`); images and video only |
| `--dry-run` | print what would be sent, call nothing |
| `--prompt-file` | read the question from a file instead of the command line |
| `--upload-timeout` | seconds to wait for a video or audio file to finish processing (default 300) |

Other subcommands: `recipes` lists what is available, `formats` prints what can
be attached and how each kind travels, `doctor` checks credentials and config,
`stats` summarizes past calls, `stored` and `uploads` show what is held
server-side.

## Budget: frugal by default, and say the number

**The defaults are already the cheap ones** — Flash, `thinking_level: minimal`,
default media resolution. Do not quietly upgrade them because a task feels
important. Good enough is the default on purpose; perfect is a decision
somebody should get to make.

What actually costs money is **how much media you attach**, not which knobs you
set. Roughly: an image is ~280–1120 tokens, a minute of video ~4,200. The CLI
prints an estimate in `--dry-run`, warns before sending anything large, and
reports exact counts afterwards in `usage.json`.

**Ask before spending, when the answer isn't already in the conversation.**
If the user has said what they want — or you are simply answering a question
they asked about a file they just handed you — get on with it. But when a call
is about to be expensive and you are choosing on their behalf, put the choice
to them with real options and real numbers:

> This recording is 8 minutes (~34k input tokens). I can:
> **(a)** trim to the 00:40–01:10 window you described (~2k),
> **(b)** send the whole thing at default resolution (~34k),
> **(c)** send it all at `high` for readable on-screen text (~134k).
> Default is (a) unless you'd rather I look wider.

Name the numbers, recommend one, and make the cheap option the default. The
triggers worth asking about: video over a couple of minutes, `--resolution
high` across several files, switching to Pro, raising `--thinking-level`, and
`--store` (which cannot be undone).

### Some calls are gated, and you cannot clear the gate yourself

Above ~20,000 estimated input tokens — or with `--store`, or
`--thinking-level medium|high` — the CLI refuses unless the user has typed
`/gemini-bridge:gemini-authorize`. Nothing you can run mints that
authorization; that is the point of it.

If you are refused: **do not retry, do not split the call into smaller ones to
get under the limit, and do not turn the gate off in `.gemini-bridge.toml`.**
Say what you wanted to send, what it would cost, and what you expected to
learn, then stop and let the user decide. Often the better move is the cheaper
call the refusal suggests — a trimmed clip or a lower resolution usually
answers the question and needs no authorization at all.

`--dry-run` tells you whether a call would be gated without sending anything,
so check there rather than discovering it by being refused.

## Going deeper

SKILL.md is the routing layer. Three references carry the detail, and it is
worth reading the relevant one before a first call of a kind you have not made
before:

| Reference | Read it for |
|---|---|
| `references/api.md` | models, thinking, seed, structured output, storage, service tiers, token accounting, what the API and the CLI deliberately do not expose, and the source URLs |
| `references/media.md` | how each modality is attached, accepted formats, resolution and token cost per kind, size limits, what the guards miss |
| `references/video.md` | video and audio end to end: the 1 FPS constraint, ffmpeg prep, worked examples, when video is the wrong tool |

## Recipe-free calls

`-r` is optional. When no shipped recipe fits — a text-only question, a
one-off stance, a schema invented for this task — call ad-hoc:

```bash
gemini-bridge ask --model gemini-pro-latest --thinking-level high \
  "Critique this design: ..."

gemini-bridge ask --system-file stance.md --schema-file verdict.json \
  -f page.png "Does this match the spec?"
```

Every recipe parameter is a flag: `--thinking-level`, `--seed`,
`--max-output-tokens`, `--service-tier`, `--schema-file`, `--label k=v`,
`--store`. Precedence is CLI flag > recipe value > default. The run is labeled
`adhoc` in the run directory and ledger.

Three things to keep straight:

- **Thinking still defaults to `minimal`.** Raising it is an explicit,
  per-call decision — say why when you do.
- **`--store` is the opt-in to server-side storage** (required for
  `--continue-from`); stored interactions cannot be deleted, so do not pass it
  for one-shot questions.
- **`--system`/`--system-file` do not combine with `-r`** — a run labeled with
  a recipe's name must actually carry that recipe's stance. If an ad-hoc
  stance proves itself twice, promote it to a recipe file so it is versioned
  and reproducible instead of retyped.

## Video and audio

Attaching either uploads the file and sends a reference to it. Three things
that follow, in the order they will bite:

1. **You write the prompt, and that is where the quality is.** A video with no
   context returns a plot summary. Say what the file is, what decision the
   answer feeds, what to ignore, and what shape you want the answer in. Use
   `-r video-analysis` for the ordinary stance and put your effort into the
   question; reach for `--system` when the stance itself is the task.
   Attaching media with **no** question runs a generic default and warns —
   that exists so a bare call is not refused, not as a way to use this.
2. **The upload is a disclosure with a 48-hour life.** Say what you are sending
   before you send it, and remember that neither guard reads inside a file — a
   two-minute screen recording is a hundred-plus frames of whatever was on
   that desktop. Uploads *can* be taken back, unlike stored interactions:
   `gemini-bridge uploads --delete`. Identical bytes upload once, so follow-up
   questions about the same file are cheap.
3. **It is slow, and length is the cost.** Roughly 4,200 input tokens per
   minute of video. Uploading and processing can outrun a default 120s command
   timeout; give it more time, and raise `--upload-timeout` if processing is
   what runs long.

Frames are sampled at 1 FPS and cannot be clipped or retimed, so trim with
ffmpeg rather than paying for ten minutes to ask about fifteen seconds — and
do not expect sub-second events to be seen at all. Everything else, including
the ffmpeg one-liners, worked examples, and when to send frames instead:
`references/video.md`.

## Choosing a resolution

One rule per modality; the measured evidence and the token table are in
`references/media.md`.

- **Images: `low` is usually right**, and on storyboards and contact sheets it
  measurably beat `high`. Go `high` for full-frame renders, where detail is
  spread across the whole frame, and whenever in-image text matters.
- **Video: leave it alone unless there is text to read.** `low`, `medium`, and
  the default all cost the same 70 tokens per frame; `high` is a flat 4x.
- **Audio and PDFs take no resolution at all** — those content types have no
  such field, and the CLI strips it rather than sending a key that would 400.

## What the verdict means

`perceptual-diff` returns `{identical, confidence, differences[]}`. Each
difference carries `region`, `kind`, `description`, `severity`.

**`identical: true` is a real result, not a failure.** The recipe is explicitly
built to confirm that a change had no visual effect, and it was validated
against null pairs — the same image compared with itself — with zero false
positives across every case tested.

**Do not route on `confidence`.** It returned `high` in all 32 control runs
across four different kinds of image, so it carries no information yet. It is
recorded, not acted on.

## Constraints that are not negotiable

- **No `temperature`.** The API accepts it and silently ignores it — verified
  live. Recipes reject it outright. Use `seed` for reproducibility.
- **Storage cannot be undone.** `interactions.delete` returns HTTP 501, so
  anything stored persists for the project's whole retention window. Every
  recipe is `stateful: false` unless the task genuinely needs follow-up turns.
- **Thinking is on by default and bills at the output rate.** Recipes default
  to `thinking_level: minimal`; an unset level is the expensive path, not the
  cheap one.
- **Video frames are sampled at 1 FPS and cannot be clipped.** No fps, no start
  or end offset — the API has no such controls. Trim with ffmpeg before
  sending, and do not expect anything shorter than about a second to be seen.

## Adding a recipe

A recipe fixes the *stance*; the caller supplies the question. That division is
the point — the stance becomes versioned and diffable instead of depending on
how it happened to be phrased that session, and with a pinned `seed` and model
two runs are actually comparable.

A recipe is a markdown file: YAML frontmatter for parameters, body for the
system instruction. Nothing in code changes. See
`references/recipes/perceptual-diff.md` and copy its shape.

Before trusting a new recipe, run it against a **null pair** — the same file
twice. A comparison recipe that reports differences between an image and itself
is worse than no recipe, and that failure is invisible if you only ever test it
on inputs that genuinely differ.
