---
name: wait-what
description: >-
  Rewrite the last message when it did not land: re-pitched with more context,
  in plainer terms, using the project's own vocabulary for things.
disable-model-invocation: true
metadata:
  last_verified: "2026-08-13"
  review_interval_days: "365"
---

Wait. I don't follow where you've got to.

Re-pitch that last message. Give me enough context to place it, write it in
ASD-STE100 Simplified Technical English, and use this project's own terms for
things — the glossary or `CONTEXT.md` if one exists, otherwise the names the
code and docs already use. Don't introduce a new word for something that already
has one here.

<!--
User-invoked by necessity, not preference: the model cannot detect that its own
message failed to land, so there is no trigger for it to fire on. That is the
definitional case for disable-model-invocation.

Deliberately short. The whole value is that it is one instruction the user can
fire mid-conversation, inside any other skill, without derailing what is
running.

Adapted from wait-what in mattpocock/skills (MIT). Changed here: the original
assumes a CONTEXT.md ubiquitous-language file; this repo has none, so the
instruction degrades to whatever vocabulary the project already uses.

Related: plain-language-us rewrites the register of a draft; show-me replaces
prose with structure. This one repairs a specific message that already failed.
-->
