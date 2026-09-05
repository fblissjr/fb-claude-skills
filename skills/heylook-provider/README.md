# heylook-provider

*Last updated: 2026-09-04*

Integration knowledge for [heylook](https://github.com/fblissjr/heylookitsanllm)
(`heylookitsanllm`), a local multimodal LLM server on Apple Silicon serving
MLX and gguf models. For applications adding it as an inference provider —
not for working inside the server codebase.

## Installation

```bash
/plugin install heylook-provider@fb-claude-skills
```

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `heylook-provider` | "add heylook as a provider", "heylook API", a 422/400/503 from a heylook request, parsing its SSE stream, cancelling an in-flight request, sending images to a local model | Runtime model discovery against install-local ids, capability gating, client-side image resize, and the deliberate differences from Anthropic's spec |

## Invocation

```
/heylook-provider:heylook-provider
```

Or automatically, when a session is wiring an app to heylook or debugging a
request against it.

## What it carries

heylook exposes one inference route, the Anthropic Messages-conformant
`/v1/messages` (the OpenAI-compatible `/v1/chat/completions` was removed in
heylook 1.79.66). An Anthropic SDK habit mostly transfers; what does not is
everything following from the server being **local and single-user**:

- Model ids are **install-local** — the registry is override-only, so the
  served roster is whatever the operator downloaded. Discovery is not
  optional, and a literal id in source is a 400 on another machine.
- **Capabilities are per-model**, and narrower than the declared modalities.
  Gating on them is necessary and not sufficient: gguf carries no capability
  guard, an operator can override a model's list outright, and the refusal
  that follows has two shapes — a 400, or an in-band error event on a stream.
- `/v1/messages` has **no server-side image resize**; the client downscales.
- `max_tokens` is **optional** — absent means the server's sampler cascade
  decides, so a client-side default carried over from Anthropic code
  silently overrides the model's configured floor.
- A busy server answers **503 with `Retry-After`**, which is a queue rather
  than a quota.
- A cold model load happens **before the response begins**, putting nothing on
  the connection — indistinguishable from a hang on a non-streaming call.
  `POST /v1/models/{id}/load` moves that wait somewhere you can label it.
- Hanging up on a non-streaming request does not stop it. There is no
  disconnect polling, so an abandoned run keeps the GPU and blocks the queue;
  `X-Request-ID` is the handle and `DELETE /v1/requests/{id}` is the stop.

Plus the deliberate spec differences (`thinking` is a bool not a config
object, no tools, no `stop_sequences`, and heylook's request and stream
extensions). That list is hand-maintained and has shipped incomplete, so the
skill says so and defers to the server's `/openapi.json`.

Beyond the skill body: four reference files (full wire reference, porting off
the removed OpenAI route, Gemini migration, working client code in Python and
TypeScript) and a
stdlib `probe.py` that prints a capability matrix from a live server.

## Source of truth

The skill's frontmatter names the heylookitsanllm version it was verified
against — one home for that number, so this page does not carry a copy to
drift. It cites the running server's `/openapi.json` — generated from the
code at boot, with no committed artifact to drift — as authoritative over
its own prose. The longer-form version of the same contract lives in that
repo at
[docs/api_integration.md](https://github.com/fblissjr/heylookitsanllm/blob/main/docs/api_integration.md).

Reverify when heylook's schema module or Messages route changes. That is the
signal; nothing here runs on a calendar.
