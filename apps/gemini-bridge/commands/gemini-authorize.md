---
description: Authorize one expensive Gemini call (long video, raised thinking, or --store).
argument-hint: "[--max-tokens N]"
---

You have authorized one expensive `gemini-bridge` call.

Arguments: $ARGUMENTS

The authorization was already created by the time you read this — typing the
command is what creates it, and nothing else can. It is single-use, expires in
ten minutes, and carries a token ceiling (200,000 by default, or `--max-tokens
N`).

Now make the call that was blocked. Say in one line what is being sent and the
estimated cost before running it. If the refusal named a specific fix — a
larger ceiling, a trimmed clip — apply that rather than re-running the same
command unchanged.

If nothing was blocked and the user ran this pre-emptively, say so and ask what
they want sent, rather than inventing a call to spend it on. An unused
authorization simply expires.
