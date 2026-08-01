# The API advisor tool, and what this plugin does differently

Reference for the upstream feature this plugin emulates. Read this when
building against the Claude API directly, or when deciding whether a difference
in the emulation matters.

Source: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool>
(beta as of this writing; verified 2026-08-01).

## The API feature

A server-side tool. A cheap **executor** model pauses mid-generation, an
Anthropic-supplied **advisor** model reads the full transcript and returns
strategic guidance, and the executor continues. All inside one `/v1/messages`
request.

```json
{
  "type": "advisor_20260301",
  "name": "advisor",
  "model": "claude-fable-5",
  "max_uses": 3,
  "max_tokens": 2048,
  "caching": { "type": "ephemeral", "ttl": "5m" }
}
```

Beta header: `advisor-tool-2026-03-01`.

Mechanics worth knowing:

- The executor emits `server_tool_use` with `name: "advisor"` and an **empty
  input**. It signals timing; the server supplies context. Nothing the executor
  writes in `input` reaches the advisor.
- The result comes back as an `advisor_tool_result` block. With Opus 5, Fable 5,
  or Mythos 5 advisors it is `advisor_redacted_result` (encrypted, unreadable
  client-side); with Opus 4.8 it is plaintext `advisor_result`. Round-trip
  either verbatim on later turns.
- Omitting the tool on a follow-up turn while `advisor_tool_result` blocks
  remain in history returns `400 invalid_request_error`. To stop mid-conversation
  you must drop the tool **and** strip the blocks.
- The advisor runs without tools and without context management. Its thinking is
  dropped; only advice text reaches the executor.
- Advisor tokens are billed at the advisor's rate and reported separately in
  `usage.iterations[]` with `type: "advisor_message"`. Top-level `usage` counts
  executor tokens only, and top-level `max_tokens` does not bound the advisor.
- Errors (`overloaded`, `prompt_too_long`, `max_uses_exceeded`, …) come back
  inside the result block. The request itself does not fail.
- Valid executor/advisor pairs are constrained: the advisor must be Sonnet 4.6
  or better, and at least as capable as the executor.

## Measured guidance worth keeping

- `max_tokens: 2048` on the tool cut mean advisor output ~7x with near-zero
  truncation. The floor of 1024 cut ~10x but truncated ~10% of calls.
- A soft word cap addressed to the advisor **in the user message** works better
  than third-person description, because the advisor sees your prompts as
  quoted context. Ask for ~80% of your true ceiling.
- Advisor-side prompt caching breaks even around three calls per conversation.
  Below that the cache write costs more than the reads save.
- A mid-conversation nudge raised Haiku pass rates ~7pp, did nothing measurable
  on Sonnet, and slightly *lowered* Opus pass rates.
- The pre-write "hard rule" checkpoint raised Haiku coding pass rates ~7.5pp but
  cost ~4pp on a browse-comprehension benchmark.

## What this plugin changes, and why

| Aspect | API tool | This plugin |
|---|---|---|
| Who decides to consult | The executor model, mid-generation | The user, by running `/advisor` |
| Context the advisor sees | Full live transcript, server-supplied | A reconstructed digest from the transcript file |
| Advisor tools | None | Read, Grep, Glob — genuinely read-only, no Bash |
| Round trips | None, single request | A subagent call |
| Output bound | `max_tokens` on the tool, a hard cap | `maxTurns` plus a soft word cap in the prompt |
| Cost visibility | `usage.iterations[]` after the fact | Digest size reported before the spawn |

Three of these are deliberate departures rather than limitations:

**The user decides, not the model.** The API tool's premise is that the executor
knows when it needs help. That is reasonable when you are building an
application and have set a budget in advance. It is wrong for an interactive
session, where an autonomous frontier-model spawn is a surprise charge against
someone watching their own bill. So authorization is human and one-shot, and a
hook enforces it rather than a prompt requesting it.

**The advisor gets read tools.** The API advisor is deliberately toolless. Here
it reads a lossy reconstruction rather than the live context, so it needs a way
to check the record — otherwise compression artifacts become confident wrong
advice. Read-only is the compromise: it can verify, it cannot act.

**Context is reconstructed, not supplied.** This is the real limitation, not a
choice. Claude Code's `Agent` tool forces a pick: `subagent_type: "fork"`
inherits full context but ignores the model override, and any other agent takes
the override but starts empty. Neither gives both. The digest bridges that gap
and is necessarily lossy — one transcript in this repo reached 13 MB, far more
than the live window it came from ever held, because tool results are truncated
and compacted in-session but written to disk in full.
