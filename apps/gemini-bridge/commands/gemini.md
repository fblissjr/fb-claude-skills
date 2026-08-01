---
description: Send images to Gemini for perceptual comparison or analysis, and read the structured verdict back.
argument-hint: "[recipe] [files...] [question]"
---

Invoke the `gemini-multimodal` skill to run a Gemini call.

Arguments: $ARGUMENTS

Steps:

1. Read the skill at `skills/gemini-multimodal/SKILL.md` if it is not already loaded.
2. Pick the recipe. `gemini-bridge recipes` lists them; `perceptual-diff` is the
   default for comparing two images.
3. Choose a resolution using the guidance in the skill — `low` for storyboards
   and contact sheets, `high` for full-frame renders or when in-image text matters.
4. State in one line which files are being sent and which recipe is being used,
   then run `gemini-bridge ask`.
5. Read `response.json` from the run directory and summarize the verdict. Do not
   paste the whole file.
