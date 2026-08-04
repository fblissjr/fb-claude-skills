---
name: gemini-multimodal
description: Send a task to a Gemini model and get a structured answer back - perceptual work Claude cannot do directly, or any ad-hoc question worth a second model's take. Use when comparing two renders or screenshots to find visual differences, when checking that a change had no visual effect, or when a visual question is being answered with pixel math, histograms, or diff statistics because looking at the images is not working. Also use when the user says "ask Gemini", "have Gemini compare these", "send this to Gemini", "what does Gemini see", "get Gemini's take", or names Gemini alongside a question, image, or screenshot. Calls need no recipe - model, thinking level, system prompt, and schema are all settable per call. Every call is an explicit, billed external request that leaves a run directory on disk.
metadata:
  last_verified: "2026-08-01"
  freshness: "cascade"
---

Hand a perceptual task to a Gemini model when direct inspection is not working.

The signal that this skill applies is usually not "there is an image" — it is
**reaching for numpy, histograms, or pixel-diff statistics to answer a question
about what something looks like.** That substitution is the symptom. Comparing
two renders and reporting mean squared error is not an answer to "did this
change anything visible."

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

## Running it

```bash
gemini-bridge ask -r perceptual-diff \
  -f before.png -f after.png \
  "Compare these two renders. The first is BEFORE a change, the second is AFTER."
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
| `--resolution` | override the recipe (`low`, `medium`, `high`, `ultra_high`) |
| `--dry-run` | print what would be sent, call nothing |
| `--prompt-file` | read the question from a file instead of the command line |

`gemini-bridge recipes` lists what is available. `gemini-bridge doctor` checks
credentials and config. `gemini-bridge stats` summarizes past calls.

## Recipe-free calls

`-r` is optional. When no shipped recipe fits — a text-only question, a
one-off stance, a schema invented for this task — call ad-hoc:

```bash
gemini-bridge ask --model gemini-3.6-pro --thinking-level high \
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

## Choosing a resolution

Measured, not guessed — a control harness over four real image pairs, two runs
each, at both resolutions:

- **`low` is the default and is usually right.** On storyboard strips and
  contact sheets it found *more* differences than `high`, not fewer.
- **Use `high` for full-frame renders** — a 3D viewport, a full screenshot,
  anything where detail is spread across the frame. On a viewport pair, `high`
  found 5–6 differences where `low` found 1. This is the case that justifies
  roughly 3x the input tokens.
- **Use `high` when text in the image matters.** Reading small on-screen text
  is the documented case for it.

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
- **Video and audio are not wired up yet.** They need the Files API plus ffmpeg
  preprocessing, because the API exposes no frame-rate or clipping controls.
  The CLI refuses them with a clear message rather than failing obscurely.

## Adding a recipe

A recipe is a markdown file: YAML frontmatter for parameters, body for the
system instruction. Nothing in code changes. See
`references/recipes/perceptual-diff.md` and copy its shape.

Before trusting a new recipe, run it against a **null pair** — the same file
twice. A comparison recipe that reports differences between an image and itself
is worse than no recipe, and that failure is invisible if you only ever test it
on inputs that genuinely differ.
