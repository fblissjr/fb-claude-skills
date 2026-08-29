# heylook-provider

*Last updated: 2026-08-29*

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
| `heylook-provider` | "add heylook as a provider", "heylook API", a 422/400/503 from a heylook request, parsing its SSE stream, sending images to a local model | The wire contract, capability discovery, and the divergences from the APIs heylook resembles |

## Invocation

```
/heylook-provider:heylook-provider
```

Or automatically, when a session is wiring an app to heylook or debugging a
request against it.

## What it carries

heylook exposes an Anthropic Messages-conformant `/v1/messages` and an
OpenAI-compatible `/v1/chat/completions`. An SDK habit mostly transfers; what
does not is everything following from the server being **local and
single-user**:

- Model ids are **install-local** — the registry is override-only, so the
  served roster is whatever the operator downloaded. Discovery is not
  optional, and a literal id in source is a 400 on another machine.
- **Capabilities are per-model**, and narrower than the declared modalities.
- `/v1/messages` has **no server-side image resize**; the client downscales.
- `max_tokens` is **optional** — absent means the server's sampler cascade
  decides, so a client-side default carried over from Anthropic code
  silently overrides the model's configured floor.
- A busy server answers **503 with `Retry-After`**, which is a queue rather
  than a quota.

Plus the closed list of deliberate spec differences (`thinking` is a bool
not a config object, no tools, the `error` stop reason, and heylook's
request and stream extensions).

Beyond the skill body: four reference files (full wire reference, the OpenAI
wire, Gemini migration, working client code in Python and TypeScript) and a
stdlib `probe.py` that prints a capability matrix from a live server.

## Source of truth

The skill is written against heylookitsanllm 1.79.39 and cites the running
server's `/openapi.json` — generated from the code at boot, with no committed
artifact to drift — as authoritative over its own prose. The longer-form
version of the same contract lives in that repo at
[docs/api_integration.md](https://github.com/fblissjr/heylookitsanllm/blob/main/docs/api_integration.md).

Reverify when heylook's schema module or Messages route changes; the skill
declares a 90-day review interval as a backstop, not as the primary signal.
