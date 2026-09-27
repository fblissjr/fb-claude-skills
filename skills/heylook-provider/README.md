# heylook-provider

*Last updated: 2026-09-27*

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
| `heylook-provider` | "add heylook as a provider", "heylook API", a 400/403/409/422/503 from a heylook request, parsing its SSE stream, cancelling an in-flight request, sending images to a local model, using its conversation store or presets | Runtime model discovery against install-local ids, capability gating, client-side image resize, and the deliberate differences from Anthropic's spec |

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
  optional, a literal id in source is a 400 on another machine, and there is
  no default model to fall back on.
- **Capabilities are per-model**, and narrower than the declared modalities.
  Gating on them is necessary and not sufficient: gguf carries no capability
  guard, an operator can override a model's list outright, and the refusal
  that follows has two shapes — a 400, or an in-band error event on a stream.
  Context length, the thinking-depth vocabulary and the request fields an
  engine reads come from each model's `engine` object.
- `/v1/messages` has **no server-side image resize**; the client downscales,
  and `/v1/models/{id}/image-plan` reports what a size costs the model.
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
- There is no inference key and no CORS, and a Host check answers 403 to a
  hostname the server does not know.

Plus the deliberate spec differences (`thinking` also takes a bool, depth is
each model's own `reasoning_effort` vocabulary, tools are a 422,
`response_format` is OpenAI's shape, removed and misspelt fields are refused
while other unknown fields are ignored, and heylook's stream extensions). That
list is hand-maintained and has shipped incomplete, so the skill defers to the
server's `/openapi.json`.

Beyond the skill body: reference files (full wire reference, every heylook
route grouped by who calls it, with the conversation store's differences from
`/v1/messages`, every version
boundary for servers older than the verified one, porting off the removed
OpenAI route, Gemini migration, and client code run against a live server:
streaming, a cancellable non-streaming call, the conversation store, preset
expansion, thinking controls)
and a stdlib `probe.py` that prints a capability matrix from a live server,
with each model's context length and thinking-depth vocabulary.
The body states current behaviour only, so it stays under the size at which
it would be truncated when re-attached after compaction.

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
