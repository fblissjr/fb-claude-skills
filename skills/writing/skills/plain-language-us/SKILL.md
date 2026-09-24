---
name: plain-language-us
description: >-
  Rewrite bloated, hedged, or AI-sounding prose into this owner's plain-language
  house style. Use when a draft is wordy or padded, leans on passive voice and
  nominalizations, hedges, uses Title Case headings, or scatters bold and italics
  through paragraphs for emphasis, and when the user says "tighten this", "make it
  readable", "clean up the prose", "too wordy", "plain English", "plain language",
  or "house style". Applies the house rules: active voice, front-loaded content,
  sentence case, no bold or italics for emphasis, no em dashes. For reports,
  research write-ups, guidance, documentation, and summaries.
argument-hint: "[draft|edit|check]"
---

# Plain-language house style

Claude already writes clear prose. This carries only the calls that are
*preferences*, where a reasonable default differs from what this owner wants.

## The rules that actually bind

- **Front-load.** The conclusion goes first, then the reasoning. Not a build-up
  to a reveal.
- **Sentence case for headings.** Not Title Case. The same goes for titles and
  table headers: capitalize only proper nouns.
- **No bold or italics for emphasis.** If a sentence needs emphasis to land,
  rewrite the sentence. Bold is for genuine labels only, such as a literal
  interface element in an instruction (select Save). No ALL CAPS for emphasis
  either.
- **No em dashes.** Use a comma, a colon, or two sentences.
- **Active voice, named actor.** "The parser drops the row", not "the row is
  dropped".
- **Keep real terminology.** Do not simplify a domain term into a vaguer one;
  define it once and keep using it.
- **Cut the machine register.** No "it is important to note", no "delve", no
  "leverage" where "use" works, no "load-bearing", no "it is not X, it is Y",
  no marketing language, no three-item lists that exist for rhythm.

## American usage

- American spelling and word choice: organize, behavior, analyze, prioritize,
  canceled, catalog, license (noun and verb); toward, while, among, not
  towards, whilst, amongst.
- Double quotation marks, with periods and commas inside the closing mark.
- The serial comma before the final "and" or "or" in a list of three or more.
- Dates month-first (January 5, 2026); all-numeric dates in ISO form
  (2026-01-05), never 01/05/2026.
- "And", not "&", except in a registered name.
- "For example", "that is" and "such as", not e.g., i.e. or etc.
- No exclamation marks.

## Formatting

- Headings are front-loaded, unique and descriptive, under about 65
  characters, with no closing punctuation.
- A bullet list takes a lead-in line ending in a colon. Each bullet starts
  lowercase, holds one idea, and has no trailing "and"/"or", semicolon, or
  final period (unless the bullet is a full sentence).
- A numbered list only for steps followed in order; steps are full sentences.
- Link text says where the link goes; never "click here" or "read more".
- No FAQ sections: content that answers the reader's need does not need one.

## Terminology and audience

Plain means clear, not a smaller vocabulary. The test for a term is meaning,
not difficulty: keep a term that is precise and in current use in the field
(for a frontier-AI audience, KV cache, speculative decoding, logits); cut one
that is vague or that no practitioner uses, however technical it sounds.
Define a term only when part of the audience will not know it, once, in
passing.

## Modes

`$ARGUMENTS`: `draft` writes new prose in this style, `edit` rewrites supplied
text, `check` reports what violates the style without rewriting. Default is
`edit` when text is supplied and `draft` otherwise.
