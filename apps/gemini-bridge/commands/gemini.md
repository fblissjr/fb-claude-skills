---
description: Send a question or media to Gemini and read the structured answer back.
argument-hint: "[recipe] [files...] [question]"
---

Invoke the `gemini-multimodal` skill to run a Gemini call.

Arguments: $ARGUMENTS

Steps:

1. Read the skill at `skills/gemini-multimodal/SKILL.md` if it is not already loaded.
2. Pick the recipe, or none. `gemini-bridge recipes` lists them; `perceptual-diff`
   is the default for comparing two images. When no recipe fits, call ad-hoc and
   set parameters directly (`--model`, `--thinking-level`, `--system-file`,
   `--schema-file`).
3. For media, choose a resolution using the guidance in the skill — `low` for
   storyboards and contact sheets, `high` for full-frame renders or when
   in-image text matters.
4. State in one line what is being sent and under which recipe (or that the call
   is ad-hoc), then run `gemini-bridge ask`.
5. Read `response.json` (or `response.md`) from the run directory and summarize
   the answer. Do not paste the whole file.
