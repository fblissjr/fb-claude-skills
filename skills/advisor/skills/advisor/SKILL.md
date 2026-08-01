---
name: advisor
argument-hint: "[--model opus|fable|sonnet] [--words N] [question]"
description: Consult a higher-tier advisor model about the current session. Reconstructs the session transcript into a digest, spawns a bounded advisor subagent on the model the user named, and reports its guidance. User-invoked only -- typing /advisor is the sole path that authorizes the spend, and the hooks enforce it.
disable-model-invocation: true
metadata:
  last_verified: "2026-08-01"
  review_interval_days: "90"
---

Consult a stronger model about what this session is doing, or configure how the
advisor behaves in this project.

This skill emulates the Claude API's [advisor tool](references/api-advisor-tool.md)
inside Claude Code. The API version lets a cheap executor pause mid-generation
and hand its full transcript to a stronger advisor. Claude Code cannot do that
directly: a subagent either inherits context (`fork`, same model) or takes a
model override (fresh, no context), never both. The bridge is the session
transcript on disk, reconstructed into a digest.

## Spending rule

**The advisor spawns only when the user types `/advisor`.** Not when a task
looks hard, not when you are stuck, not when it would obviously help.

This is enforced in three places rather than requested:

1. `disable-model-invocation: true` keeps this skill out of your context
   entirely, so you cannot load it on your own judgment.
2. The authorization that funds a spawn is minted only by a
   `UserPromptExpansion` hook, which fires solely on a user-typed command. You
   cannot reach that event, and running the preparation script yourself does
   not create one.
3. A `PreToolUse` hook denies any advisor spawn whose authorization is missing,
   expired, lacking user-typed provenance, or naming a different model.

If you believe a consult is warranted and the user has not asked, say so in one
sentence, say what you would ask, and continue without it.

## Run a consult

1. **Prepare.** Run, from the project root:

   ```
   bash <plugin-root>/skills/advisor/scripts/prepare-consult.sh
   ```

   It takes no arguments. The model, word cap, and digest budget come from what
   the user typed (and `.claude/advisor.json` defaults), already recorded in the
   authorization — so there is nothing here for you to choose or substitute.

   It prints `DIGEST=`, `MODEL=`, and `WORDS=`. The stderr line reports the
   digest size in characters and approximate tokens; relay that to the user,
   since it is what they are about to pay for on the input side.

   If it fails, stop and report why. Do not spawn anything, and do not try to
   create an authorization yourself — a spawn without one is denied.

2. **Spawn the advisor.** One `Agent` call:
   - `subagent_type: "advisor"`
   - `model:` exactly the `MODEL` value printed in step 1. The hook compares
     this against what the user authorized and denies a mismatch, so it cannot
     be substituted.
   - `prompt:` the text below, with the digest file read in or referenced by
     path, plus the user's question if they asked one.

   ```
   Read the session digest at <DIGEST path>.

   <If the user asked a specific question, put it here verbatim.
    Otherwise: "Assess where this session is and what I should do next.">

   Keep your guidance under <WORDS> words. I need a focused starting point,
   not a comprehensive plan.
   ```

   The word cap belongs in the prompt, addressed to the advisor directly.
   Anthropic measured that placement as the effective one — roughly a 7x
   reduction in advisor output, with the cap treated as a soft constraint, so
   ask for about 80% of your true ceiling.

3. **Report back.** Give the user the advice verbatim or near-verbatim. Do not
   summarize it away — they paid for those tokens. Then say what you intend to
   do about it.

4. **Weigh it properly.** Give the advice serious weight. If you follow it and
   it fails empirically, or you have primary-source evidence contradicting a
   specific claim, adapt. A passing self-test is not evidence the advice is
   wrong — it is evidence your test does not check what the advice checks.

   If you have already retrieved data pointing one way and the advisor points
   another, do not silently switch. Surface the conflict to the user and let
   them decide whether to spend a second consult reconciling it.

## When a consult is worth suggesting

The upstream guidance, which carries measured backing, is that advice pays off
at two moments: early, after enough orientation to describe the problem but
before committing to an approach; and late, after writes and test output exist,
on tasks that turned out to be hard.

It pays off least on short reactive work where the next action is dictated by
the tool output you just read.

Suggest a consult when the task has a genuine design fork, when an approach is
not converging, or when you are about to commit to an interpretation you cannot
cheaply reverse. Do not suggest one on every turn — a suggestion the user keeps
declining is noise.

## Install the project rule

`/advisor install` writes `<project-root>/.claude/rules/advisor.md` from
[`references/advisor-rule.md`](references/advisor-rule.md), verbatim. That rule
tells Claude in this project when to suggest a consult and how to weigh advice.
It is standalone: no plugin needed for the rule text to keep working, and
removing it is deleting the file.

If the file exists and differs, show the diff and ask before overwriting.

## Configure the checkpoint

`.claude/advisor.json` in the project root, all fields optional. A commented
template is at [`references/advisor.json.example`](references/advisor.json.example):

```json
{
  "checkpoint": "off",
  "defaults": { "model": "opus", "effort": "high", "words": 250, "maxChars": 40000 }
}
```

`checkpoint` controls the pre-write gate enforced by the `PreToolUse` hook:

| Value | Behavior |
|---|---|
| `off` (default) | Nothing. The hook exits immediately. |
| `warn` | First write with no consult on record prints a note. Does not block. |
| `block` | First write with no consult on record is denied. Only the user clears it. |

This is the "hard rule" from the upstream docs. Leave it `off` unless you have
seen the model skip planning on work that needed it. Anthropic's own numbers
have it raising Haiku pass rates by ~7.5pp on coding work while costing ~4pp on
retrieval-heavy workloads, and making Opus over-call. It is a real tradeoff, not
a free win. A consult anywhere in the session satisfies it permanently.

## Cost and control

Every lever is explicit and none is inferred:

| Lever | Set by | Effect |
|---|---|---|
| `model` | `/advisor --model`, recorded at mint, checked at spawn | Which tier answers |
| `effort` | `agents/advisor.md` frontmatter (`high`) | How hard it thinks |
| `maxTurns` | `agents/advisor.md` frontmatter (6) | Hard ceiling on advisor turns |
| `tools` | `agents/advisor.md` frontmatter (Read, Grep, Glob) | It cannot write, only look |
| `--max-chars` | `/advisor --max-chars`, recorded at mint | Input size |
| `--words` | `/advisor --words`, recorded at mint | Output size |

Everything the user types is captured when the authorization is minted, so
nothing downstream can substitute a different value. Authorizations expire after
5 minutes and fund exactly one spawn. A consult is never automatic, never
batched, and never inferred from context.

## Remove

Delete `<project-root>/.claude/rules/advisor.md` and `.claude/advisor.json`.
Uninstall the plugin to remove the hooks. Session state lives in
`$TMPDIR/claude-advisor/` and disappears on reboot.
