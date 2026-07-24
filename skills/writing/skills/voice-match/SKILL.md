---
name: voice-match
description: "Write in the user's own voice by learning it from the conversation and from a saved voice profile. Use when the user says 'write this in my voice', 'match my tone', 'sound like me', 'in my style', or wants a draft, reply, or doc to read as if they wrote it."
metadata:
  last_verified: "2026-07-24"
  review_interval_days: "365"
---

Write so the result reads as if the user wrote it. Learn the user's voice from two places: the current conversation, and a saved voice profile that persists across sessions. Match voice and register; never change the meaning, and never copy mistakes.

This skill pairs with `plain-language-us` but does not require it. When both are active, the house style sets the floor and this skill sets the voice (see "Working with plain-language-us").

## Read the voice

Build a read of the user's voice from their own messages in the thread, and from any saved profile. Attend to:

- sentence length and how much it varies; short and punchy against long and winding
- punctuation habits: em dashes, semicolons, parentheticals, ellipses, lists
- contraction use, directness against hedging, warmth against neutrality
- vocabulary register (casual, formal, technical) and any signature words or phrases
- person (I, we, you) and how the user opens and closes
- structure tendency: prose against bullets, front-loaded against narrative

## Apply the voice

- Write the deliverable in those traits while keeping the meaning and the facts intact.
- Match durable voice, not transient chat artifacts. Typos, dropped punctuation, all-lowercase, terse fragments, and quick chat shorthand are not a style to reproduce in a finished piece, unless the user asks for exactly that.
- Weak signal means fall back to a neutral, clear default. Do not invent a voice from one or two short messages.
- Voice bends rhythm, register and word choice. It never bends accuracy.

## Remember the voice across sessions

Persist the voice in a profile so it survives across conversations. Use two layered stores.

- Global: `<HOME>/.claude/voice-profile.md`. The user's durable writing voice, applied everywhere.
- Project: `.claude/voice-profile.local.md` in the repo root. Per-repo adjustments, because a formal work repo often reads differently from a personal one.

Keep the project profile personal, not shared. It reflects how one person writes and is not team configuration. Ensure `.claude/voice-profile.local.md` is gitignored; add it to `.gitignore` if it is not already there.

Learning modes control when the profile is written, not when it is read. Reads always layer global then project. The user sets the mode, and a per-request instruction always overrides it:

- `session` - use the thread and the profile, but persist nothing this session
- `project` - learn into the project profile
- `global` - learn into the global profile
- `off` - never write; treat both profiles as read-only

Default: when learning, write to the project profile inside a repo, otherwise the global one. Honor explicit per-request overrides such as "just this session", "save that globally", or "do not learn from this one".

On activation:

1. Read the global profile if it exists, then the project profile. Merge them, with project traits overriding global ones on conflict.
2. Combine the stored profile with the live conversation signal. When the live signal clearly contradicts a stale stored trait, the live signal wins.
3. If no profile exists and the thread has enough signal, offer to save one before writing.

Learn and update:

- After a substantial writing task, if you saw consistent, durable traits not already recorded, update the profile in place. Keep it a concise card, not a log or a diff history.
- Do not rewrite the profile from a single message, and do not overfit to one deliverable's register.
- Record durable voice traits only: rhythm, vocabulary, directness, structure, punctuation habits. A trait that holds everywhere goes in the global profile; a repo-specific one goes in the project profile.
- Never store personal identifiers, secrets, or the content of what was written. The profile describes how the user writes, not who they are or what they wrote.

## Feedback and correction

The profile updates dynamically, when wanted. Two triggers:

- Explicit feedback always updates immediately. When the user says a draft did not sound like them, or names a habit ("I never use em dashes", "shorter sentences"), record it and apply it at once.
- Inferred signal updates modestly. After a substantial task you may refine the card, but keep the change small and always leave it inspectable.

A user correction is a fixed preference. Record it in the profile's "corrections (fixed)" field and do not override it from later inference. Inference fills gaps; it does not fight a stated preference.

The user can inspect and steer all of this with the `/writing:voice` command, or in plain language ("show my voice profile", "that did not sound like me").

## Profile format

A short structured card. Fill only the fields you have real signal for.

```markdown
# voice profile

- register: <casual | neutral | formal | technical, and how it shifts by context>
- sentence rhythm: <short and punchy | mixed | long and layered; typical length>
- directness: <blunt | measured | hedged>
- punctuation: <habits and dislikes, for example: uses em dashes freely; avoids semicolons>
- structure: <prose | bullets | mixed; front-loads or builds up>
- person and address: <I | we | you; how they open and close>
- signature words and phrases: <recurring terms, with any words to avoid>
- corrections (fixed): <preferences the user stated outright; never overridden by inference>
- learning: <session | project | global | off>
- notes: <anything durable that the fields above miss>
```

## Working with plain-language-us

When `plain-language-us` is also active, use voice within the rules:

- The house style's accessibility and correctness rules always hold: American spelling, sentence case, front-loading, descriptive links, no ALL CAPS, no Latin abbreviations, and the ban on machine-generated filler phrasing (load-bearing, delve, "it is not X, it is Y" and the like).
- Punctuation and rhythm follow the user's real voice, not the house default: em-dash use, contractions, and sentence length come from the profile. The house style's em-dash caution is aimed at the machine habit of overusing them, not at a person who genuinely writes with them.
- In short: `plain-language-us` sets the floor, `voice-match` sets the voice. Clarity is never traded for imitation.

## Before you finish: self-check

- Would the user recognize this as their own writing, read aloud?
- Is the meaning and every fact unchanged from what was asked for?
- Did you match durable voice rather than copy chat shorthand or errors?
- If you learned something durable, did you update the right profile (global or project), and keep it concise?
- If the user corrected the voice, did you record it as a fixed preference that inference will not override?
- If `plain-language-us` is active, did the clarity rules still hold while the voice came through?
