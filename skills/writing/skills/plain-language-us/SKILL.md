---
name: plain-language-us
description: >-
  Write and edit in this owner's plain-language house style: plain English, active
  voice, front-loaded content, sentence case, no bold or italics for emphasis, and
  no em dashes. Use when writing or editing reports, research write-ups, guidance,
  documentation, summaries, or any prose where clarity matters, or when the user
  says "plain language", "plain English", "tighten this", or "house style".
argument-hint: "[draft|edit|check]"
metadata:
  last_verified: "2026-07-26"
---

# Plain-language house style

Claude already writes clear prose. This carries only the calls that are
*preferences*, where a reasonable default differs from what this owner wants.

## The rules that actually bind

- **Front-load.** The conclusion goes first, then the reasoning. Not a build-up
  to a reveal.
- **Sentence case for headings.** Not Title Case.
- **No bold or italics for emphasis.** If a sentence needs emphasis to land,
  rewrite the sentence. Bold is for genuine labels only.
- **No em dashes.** Use a comma, a colon, or two sentences.
- **Active voice, named actor.** "The parser drops the row", not "the row is
  dropped".
- **Keep real terminology.** Do not simplify a domain term into a vaguer one;
  define it once and keep using it.
- **Cut the machine register.** No "it is important to note", no "delve", no
  "leverage" where "use" works, no three-item lists that exist for rhythm.

## Going deeper

- `references/style-details.md` — American English conventions, formatting
  specifics, and how far to shift for a given audience. Read when a specific
  call is contested, not before drafting.
- `references/self-check.md` — the pass to run over a finished draft.

`$ARGUMENTS`: `draft` writes new prose in this style, `edit` rewrites supplied
text, `check` reports what violates the style without rewriting. Default is
`edit` when text is supplied and `draft` otherwise.
