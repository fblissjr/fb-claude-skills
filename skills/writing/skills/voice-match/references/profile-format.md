# Voice profile format and maintenance

last updated: 2026-07-26

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
