---
name: heylook-provider
description: Wire an application to heylook (heylookitsanllm), a local multimodal LLM server on Apple Silicon serving MLX and gguf models over one Anthropic Messages-conformant /v1/messages endpoint (the OpenAI-compatible /v1/chat/completions was removed in heylook 1.79.66). Use when adding heylook as an inference provider alongside Gemini, OpenAI or Anthropic, when a heylook request answers 404/422/400/503, when parsing its SSE stream, when cancelling an in-flight request, when sending images or audio to a local model, or when porting an OpenAI-SDK client off the removed route. Carries what an Anthropic SDK habit gets wrong here - runtime model discovery against install-local ids, capability gating, client-side image resize, and the deliberate differences from Anthropic's spec. Not for calling Gemini as a tool (that is gemini-bridge), and not for working inside the heylook server codebase itself.
metadata:
  verified_against: "heylookitsanllm 2.0.28"
---

# heylook as an inference provider

Local inference server: FastAPI, Apple Silicon, MLX (text and vision) plus gguf through a `llama-server` subprocess. Default base `http://localhost:8000`.

`POST /v1/messages` conforms to Anthropic's Messages API (typed content blocks, top-level `system`, the Messages SSE grammar with no `[DONE]`), so an Anthropic SDK habit mostly transfers and Anthropic's spec answers most questions this skill does not. What does not transfer follows from the server being **local and single-user**: model ids belong to the install, capabilities vary per model, images are resized by you, and a busy server queues rather than scales.

This file states behaviour as of the version in `metadata.verified_against`. For an older server, read `server_version` from `/v1/capabilities` and then `references/older_servers.md`, which holds every version boundary.

<done>
Each line points at the section that states the rule; a line added here is a pointer, never a second, looser copy.

- Model ids resolved at runtime, never literal in source. → `<discovery>`
- Capability-gated features read `capabilities` before offering, **and** the client handles the three outcomes gating does not prevent: the 400, the in-band `invalid_request_error` on a stream, and the gguf case with no status code. → `<discovery>`
- Images downscaled client-side before the request is built. → `<image_resize>`
- 503 retried with backoff; in-band `error` events end the stream and never reach a rendered transcript as model output. → `<status_codes>`
- Every call carries a **fresh** `X-Request-ID`, and non-streaming calls have a path that DELETEs it. → `<operations>`
- Telemetry read defensively, with `generation_duration_ms` as the throughput denominator. → `<operations>`
- A real request has run against a live server, not just typechecked.
</done>

<discovery>
Model ids are **install-local**. The registry is override-only: any model under a scanned folder is served with derived defaults, so the roster changes when the owner downloads something, with no config edit or restart. An id that worked on one machine is a 400 on another.

Query the user's live server before writing client code; if it is down, ask them to start it rather than guess ids:

```bash
curl -s localhost:8000/v1/models        # served right now
curl -s localhost:8000/v1/capabilities  # server version, sampler roster
python3 ${CLAUDE_SKILL_DIR}/scripts/probe.py --base http://localhost:8000 --need vision
```

The probe prints both as a capability matrix. Exit 2: no served model has every required capability (an empty roster counts), so this machine cannot do the thing about to be built. Exit 1: it could not read the server; the message says unreachable, refused, or not heylook's shape. Discovery is open even with `HEYLOOK_API_KEY` set, so a 401 from the probe points at a proxy in front (pass `--api-key` for it).

**Gate features on `capabilities`, not `modalities`.** `capabilities` is what the server will serve; `modalities` is what the checkpoint author declared, and they diverge on purpose (MLX strips audio towers at load). On MLX, the advertised `vision` capability and the refusal come from one resolver. Keep handling the refusal anyway, because three arms stay open:

- **A vision-capable MLX model refuses an image on a non-user turn** with a 400. Deliberate: mlx-vlm attributes media by counting markers and would silently move an assistant-turn image to the last user turn. For assistant prefill or replayed multi-turn media, put the image on a user turn. gguf accepts the shape.
- **gguf has no capability guard.** heylook forwards the block to `llama-server`. Its 400 is normalized into the same refusal; accepting the block and ignoring it is the silent case, a 200 describing an image the model never used, decided by the model's GGUF/mmproj packaging.
- **An explicit `capabilities` list in `models.toml` is honoured verbatim** on either provider, so an operator can assert what the server will not deliver.

The refusal has two shapes: non-streaming a 400; on a stream the guard fires at the first token, after headers flushed, so it arrives as an in-band `error` event typed `invalid_request_error`. A client that treats gating as sufficient renders that as a hang or as assistant text.

Audio: the MLX branch never emits an `audio` capability, so gating alone keeps you off it (sending it anyway is a 400). gguf serves audio.

`GET /openapi.json` is generated from the Pydantic models at boot, so its fields, bounds and enums are current by construction: it is the field reference and wins over this file (its hand-written header prose lags).
</discovery>

<wire>
`/v1/messages` is the only inference route. `/v1/chat/completions` and `/v1/batch/chat/completions` are a plain 404: an OpenAI-SDK client has to be ported, and the batch endpoint has no replacement (loop requests; generation is serialised anyway). Porting notes: `references/openai_wire.md`.

Differences from Anthropic's Messages API:

- **`max_tokens` is optional.** Absent means heylook's sampler cascade decides (per-model config, named sampler bundle, server floor). A client-side default carried over from Anthropic code silently overrides the model's configured floor on every request; send only the fields you have an opinion about.
- **`thinking` is a bool**, the local-model `enable_thinking` template switch, not Anthropic's config object. Depth is `reasoning_effort`, with a per-model vocabulary.
- **No tools**: no `tools`, `tool_use`, `tool_result`, or `tool_use` stop reason.
- **Thinking blocks carry no `signature`**, and there is no `signature_delta`.
- **No `stop_sequence` field**: `message_delta.delta` carries `stop_reason` alone; `message_start.message` omits both.
- **`stop_sequences` on the request is ignored**, with no error, so generation runs past it. Stop client-side.
- **`message_start.usage.input_tokens` is 0** (emitted before the first chunk); read input tokens from `message_delta.usage`.
- **`logprobs` and `top_logprobs` are removed**, as is the `heylook_logprobs` event; sending either is a 422 naming the removal.
- **Extensions**: `min_p`, `repetition_penalty`, `repetition_context_size`, `presence_penalty`, `seed`, `show_special_tokens`, `sampler`, `vision_tokens`, `reasoning_effort`, `stream_options`; on the stream, `heylook_progress` and `message_stop.performance`. `/openapi.json` enumerates them.

A thinking model returns a `thinking` block alongside `text`: join only the `text` blocks, or the model's reasoning lands in your product's output.
</wire>

<image_resize>
`/v1/messages` has no resize params; clients resize before sending. Match heylook's own frontend: longest edge around 2048px, photos re-encoded to JPEG around 0.85 quality, PNG kept as PNG, EXIF orientation honoured. Node and Python recipes: `references/client_recipes.md`. To cap model cost rather than pixels, send `vision_tokens`, a per-image visual token budget snapped to what the processor supports.
</image_resize>

<status_codes>
| Code | Meaning | Response |
|---|---|---|
| 400 | Pick a different model | Unknown or disabled id, or none given with no server default (reason and available ids in `detail`); or the loaded model refusing input it advertised |
| 500 | That model is broken | It exists but failed to load |
| 503 | Backpressure, retry | `{"error":{"code":"model_overloaded"}}` plus `Retry-After`; no `X-Request-ID` echo |
| 422 | Malformed body | A media block with no `source`/`source_type` or no payload, or an out-of-range sampler value |

503 is normal operation: the server is single-user and serialises generation, so queueing behind a long request is expected. Retry with backoff on `Retry-After`.

After a stream's headers flush the status is already 200, so a late refusal arrives as `event: error`. Map `error.type` `invalid_request_error` to your 400 path and `api_error` to your 500 path. An error event ends the generation, and its message is diagnostic text, not model output.
</status_codes>

<operations>
- **A cold load is invisible on the wire.** Startup loads nothing, and a load runs before the response begins: no headers, no `message_start`, no keepalive. Streaming does not cover it, and a non-streaming client cannot tell a loading model from a hung server.
- **`POST /v1/models/{id}/load` moves that wait into a request you can label**, at no extra cost. Unknown or disabled id is a 400; busy (every loaded model generating) is a 503 with `Retry-After`; 500 is a genuine load failure only. `?warm=true` also runs a 1-token generation to pay the Metal kernel JIT, behind the global FIFO generation gate, so use it for startup or model-switch readiness, not per request. A failed warm is still a 200 (`warmed: false`, `warm_error`); the model is loaded either way.
- **One model is resident by default (LRU eviction)**, so alternating models can reload each time. Batch work by model.
- **Auth is opt-in and gates inference only.** `HEYLOOK_API_KEY` is loopback-exempt by default, so it appears when the app runs on another machine; headers and the admin token, which an integration does not need, are in `references/wire_reference.md` (Auth).
- **Send a fresh `X-Request-ID` on every request**: a new UUID each time, not one per session or client. The server maps an id to a set of in-flight generations, so a reused id cancels every request sharing it; log correlation invites exactly that reuse. The id is echoed (except on a busy 503) and is the cancel handle: `DELETE /v1/requests/{request_id}`. Without the header the server generates an id you never learn on the non-streaming path, so sending it is the precondition for cancelling.
- **Cancel non-streaming calls explicitly.** A stream is cancellable by hanging up; a non-streaming request writes nothing until done, has no disconnect polling, and keeps holding the GPU after the client leaves. Call DELETE. A cancelled run returns normally with what it produced and `stop_reason: "max_tokens"`, indistinguishable from budget exhaustion, so track your own cancels. Against `/v1/conversations` it persists a truncated assistant message. Detail: `references/wire_reference.md`.
- **Telemetry is always on and never guaranteed.** There is no `include_performance`; do not send it. `performance` is `null` for a run with no tokens, and every field is optional: present is a real measurement, absent means this mode could not measure it. The throughput denominator is `generation_duration_ms` (excludes queue wait and load; `request_duration_ms` includes both). Time to first token is never returned: time the first delta on a stream rather than deriving it from a duration field. Per-field account: `references/wire_reference.md`.
- **`reasoning_effort` values are model-specific**, and the schema accepts the union of every model's set, so a wrong value reaches the chat template and returns a 500. Gate on the `reasoning_effort` capability and read each model's accepted set.
</operations>

<references>
| File | Holds | Load when |
|---|---|---|
| `references/wire_reference.md` | Every `/v1/messages` field, block, stream event and error payload | Writing or debugging a request |
| `references/older_servers.md` | Every version boundary, by topic | The server predates `metadata.verified_against`, or the client must support a range |
| `references/openai_wire.md` | Porting off the removed `/v1/chat/completions` | An OpenAI-SDK client points at heylook, or that route answers 404 |
| `references/gemini_migration.md` | Field-by-field Gemini mapping and structural mismatches | Adding heylook beside a Gemini integration |
| `references/client_recipes.md` | Streaming clients in Python and TypeScript; image-resize recipes | Writing the client |
| `${CLAUDE_SKILL_DIR}/scripts/probe.py` | Capability matrix from a live server | Discovery |

Authoritative beyond all of these: the running server's `/openapi.json`, and [docs/api_integration.md](https://github.com/fblissjr/heylookitsanllm/blob/main/docs/api_integration.md) in the heylook repo.
</references>
