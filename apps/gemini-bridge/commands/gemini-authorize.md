---
description: Authorize one expensive Gemini call (long video, raised thinking, or --store).
argument-hint: "[--max-tokens N]"
disable-model-invocation: true
---

<!--
`disable-model-invocation` is load-bearing here, not hygiene. The gate's whole
argument is that only a human keystroke can reach `UserPromptExpansion`; every
other command in this plugin is one Claude is meant to run, and this is the one
it must not. Without the flag the command's description enters context and the
SlashCommand tool can reach it, so the entire premise rests on an assumption
about which paths fire that event -- exactly the shape of the 0.11.0 no-op,
where a single unexamined assumption about the environment turned the gate off
silently.

Precedent: `skills/advisor` guards the same threat with three layers --
`disable-model-invocation`, its mint hook, and a `PreToolUse` matcher refusing
model-initiated loads. This ships the first two. The third is not added because
it would guard a path this flag already closes, and `doctor` cannot detect a
regression in either, which is stated in the README rather than left to be
discovered.
-->


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
