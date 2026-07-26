---
name: voice-match
description: >-
  Reproduce this specific user's writing voice from evidence: their phrasing in the
  current conversation, supplemented by a saved voice profile stored in their
  Claude config directory. Use when drafting anything that will go out
  under the user's name — an email or reply, a GitHub issue comment, a Slack
  message, a release announcement, a README intro, a standup note — and when they
  say "in my voice", "sound like me", "in my style", "match my tone", "the way I'd
  write it", or "don't make it sound AI-generated". Drafting from generic instinct
  produces exactly the flat register they are trying to avoid; the conversation and
  the profile carry the specific rhythm, vocabulary, and habits that make a draft
  read as theirs.
argument-hint: "[draft|reply|edit]"
metadata:
  last_verified: "2026-07-26"
---

# Write in the user's voice

## Read the voice from what is in front of you

Before reaching for a stored profile, read the conversation. The user's own
messages in this session are the freshest sample there is. Look for sentence
length and variance, how much hedging they use, whether they front-load or build
up, their punctuation habits, and the words they reach for repeatedly.

A saved profile at `<HOME>/.claude/writing-voice.md` supplements this. Live
evidence wins where the two disagree — voice drifts, and the profile may be old.

## Apply it

Match the observed patterns rather than an idea of "good writing". If the user
writes in fragments, write fragments. If they never use semicolons, do not
introduce them. Resist smoothing their voice into the house register: this skill
exists precisely to *not* do that.

If you have too little signal, say so and write plainly instead of guessing. A
confident wrong voice reads worse than a neutral one.

## Going deeper

- `references/profile-format.md` — the stored profile's format, how to update it
  from feedback, and how corrections accumulate across sessions.
- This skill overrides `plain-language-us` where they conflict. That skill is the
  owner's house style; this one is the user's own voice, and the whole point is
  that it wins.

`$ARGUMENTS`: `draft` for new prose, `reply` for a response to something
supplied, `edit` to rewrite existing text into the voice.
