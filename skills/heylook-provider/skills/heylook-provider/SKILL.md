---
name: heylook-provider
description: Wire an application to heylook (heylookitsanllm), a local multimodal LLM server on Apple Silicon serving MLX and gguf models over one Anthropic Messages-conformant /v1/messages endpoint (its OpenAI-compatible route was removed in 1.79.66). Use when adding heylook as a provider alongside Gemini, OpenAI or Anthropic, when a heylook request answers 400/403/404/422/503, when parsing its SSE stream, when cancelling an in-flight request, when using its conversation store or presets, when sending images or audio to a local model, or when porting an OpenAI-SDK client off the removed route. Carries what an Anthropic SDK habit gets wrong here - runtime discovery of install-local model ids, capability gating, client-side image resize, and its differences from Anthropic's spec. Not for calling Gemini as a tool (that is gemini-bridge), and not for working inside the heylook server codebase itself.
metadata:
  verified_against: "heylookitsanllm 2.0.181"
---

# heylook as an inference provider

Local inference server on Apple Silicon: MLX plus gguf through a `llama-server` subprocess. Default base `http://localhost:8000`.

`POST /v1/messages` conforms to Anthropic's Messages API (typed content blocks, top-level `system`, `stop_sequences`, the Messages SSE grammar with `ping` keepalives and no `[DONE]`), so an Anthropic SDK habit mostly transfers and Anthropic's spec answers most questions this skill does not. What does not transfer follows from the server being **local and single-user**: model ids belong to the install, capabilities vary per model, images are resized by you, and a busy server queues rather than scales.

This file states behaviour as of `metadata.verified_against`. For an older server, read `server_version` from `/v1/capabilities`, then `references/older_servers.md`, which holds every version boundary.

<done>
Each line points at the section that states the rule; a line added here is a pointer, never a second, looser copy.

- Model ids resolved at runtime, never literal in source, and always sent. → `<discovery>`
- Capability-gated features read `capabilities` and `engine` before offering, **and** the client handles the three outcomes gating does not prevent: the 400, the in-band `invalid_request_error` on a stream, and the gguf case with no status code. → `<discovery>`
- Images downscaled client-side before the request is built. → `<image_resize>`
- 503 retried with backoff; in-band `error` events end the stream and never reach a rendered transcript as model output. → `<status_codes>`
- Every call carries a **fresh** `X-Request-ID`, and non-streaming calls have a path that DELETEs it. → `<operations>`
- Telemetry read defensively, with `generation_duration_ms` as the throughput denominator. → `<operations>`
- A real request has run against a live server, not just typechecked.
</done>

<discovery>
Model ids are **install-local**. The registry is override-only: any model under a scanned folder is served with derived defaults, so the roster changes when the owner downloads something. An id that worked on one machine is a 400 on another. There is no default model: a request without `model` is a 400 listing the ids.

Query the user's live server before writing client code; if it is down, ask them to start it rather than guess ids:

```bash
curl -s localhost:8000/v1/models        # served right now, with each model's engine facts
curl -s localhost:8000/v1/capabilities  # server version
python3 ${CLAUDE_SKILL_DIR}/scripts/probe.py --base http://localhost:8000 --need vision
```

Exit 2: no served model has every required capability (an empty roster counts). Exit 1: it could not read the server; the message says unreachable, refused, or not heylook's shape. Discovery is never gated, so a 401 is something in front of heylook, and a 403 is heylook's Host check (see `<operations>`).

**Gate features on `capabilities`, not `modalities`.** `capabilities` is what the server will serve; `modalities` is what the checkpoint author declared (MLX strips audio towers at load). Finer controls come from each row's `engine` object: context length, the thinking switch and depth vocabulary, which request fields the engine reads (hide a control whose field is not in `engine.decoding.request_fields`). Most of it is facts, `{value, provenance, source}`, read at `.value`; `engine.thinking` is a plain object. Shape: `references/wire_reference.md` (Discovery endpoints).

On MLX, the advertised `vision` capability and the refusal come from one resolver. Keep handling the refusal anyway, because three arms stay open:

- **A vision-capable MLX model refuses an image on a non-user turn** with a 400 (mlx-vlm would silently move it to the last user turn). Put images on user turns. gguf accepts the shape.
- **gguf has no capability guard.** It advertises `vision` only with an mmproj projector, then forwards the block to `llama-server`, whose refusal becomes the same 400 (in llama-server's own words, so never string-match refusals); accepting the block and ignoring it is the silent case, a 200 describing an image the model never used.
- **An explicit `capabilities` list in the model's `heylook.toml` config is honoured verbatim**, so an operator can assert what the server will not deliver.

The refusal has two shapes: non-streaming a 400; on a stream the guard fires after headers flushed, so it arrives as an in-band `error` event typed `invalid_request_error`. The same two shapes carry an unreadable image and a prompt longer than the model's context. A client that treats gating as sufficient renders that as a hang or as assistant text.

Audio: MLX never advertises `audio` (sending it is a 400). gguf serves it with a projector.

`GET /openapi.json` is generated from the code at boot, so it is current by construction: it is the field reference and wins over this file.
</discovery>

<wire>
`/v1/messages` is the only inference route. `/v1/chat/completions` and its batch route are a plain 404; porting notes: `references/openai_wire.md`.

Differences from Anthropic's Messages API:

- **`max_tokens` is optional.** Absent means heylook's cascade decides (server floor, the publisher's generation config, model config). A client-side default carried over from Anthropic code overrides the model's own on every request; send only the fields you have an opinion about.
- **`thinking` takes a bool** (the template's thinking switch) as well as Anthropic's `{"type","budget_tokens"}`. Gate `budget_tokens` on the `thinking_budget` capability: elsewhere it is accepted but may cap nothing.
- **Depth is `reasoning_effort`**, in each model's own template vocabulary: read `engine.thinking.depth.values` and show those words (`depth.off` lists the ones that mean thinking off). Never map a low/medium/high scale across models. An unoffered value is a 400, unless `depth.unknown` is `verbatim`.
- **No tools**: `tools` and `tool_choice` are a 422.
- **`response_format`** is OpenAI's structured-output shape (`json_schema`, `json_object`, `text`), not an Anthropic field. 400 on harmony and diffusion models, and with a continuation.
- **Thinking blocks carry no `signature`**, and there is no `signature_delta`.
- **`message_start.usage.input_tokens` is 0**; read usage from `message_delta`. `input_tokens` counts tokens processed this request; the reused prefix is `cache_read_input_tokens`.
- **A trailing assistant message is continued**, not answered; a thinking-only final turn resumes the thought.
- **Removed fields are refused**: `logprobs`, `sampler`, `preset`, `vision_tokens`, `show_special_tokens: true`, and the misspellings `enable_thinking`, `max_new_tokens`, `system_prompt`, `chat_template_kwargs` are a 422 naming the fix. Any other unknown field is **silently ignored**, so a typo in an optional field is a silent no-op.
- **Extensions**: `min_p`, `repetition_penalty`, `repetition_context_size`, `presence_penalty`, `seed`, `reasoning_effort`, `response_format`; on the stream, `heylook_progress` and `message_stop.performance`. Detail: `references/wire_reference.md`.

A thinking model returns a `thinking` block alongside `text`: join only the `text` blocks, or the model's reasoning lands in your product's output.
</wire>

<image_resize>
`/v1/messages` has no resize params; clients resize before sending. Match heylook's own frontend: longest edge around 2048px, photos re-encoded to JPEG around 0.85 quality, PNG kept as PNG, EXIF orientation honoured. Only base64 and http(s) sources: MLX refuses a local file path. To show what an image costs a loaded model, `POST /v1/models/{id}/image-plan` returns its prompt tokens and the size the engine resizes it to; show the cost as disclosure, not a gate. Recipes: `references/client_recipes.md`.
</image_resize>

<status_codes>
| Code | Meaning | Response |
|---|---|---|
| 400 | Pick a different model or input | No `model`, an unknown or disabled id (available ids in `detail`); or the model refusing input: an unoffered capability, an unoffered depth, an over-long prompt |
| 403 | Host check | The `Host` header names a host heylook does not know; `detail` names the fix |
| 500 | That model is broken | It exists but failed to load |
| 503 | Backpressure, retry | `{"error":{"code":"model_overloaded"}}` plus `Retry-After` |
| 422 | Malformed body | A removed or misspelt field, a media block with no payload, an out-of-range value |

503 is normal operation: the server is single-user and serialises generation, so queueing behind a long request is expected. Retry with backoff on `Retry-After`.

After a stream's headers flush the status is already 200, so a late refusal arrives as `event: error`. Map `error.type` `invalid_request_error` to your 400 path and `api_error` to your 500 path. An error event ends the generation, and its message is diagnostic text, not model output. Ignore `ping` and any event type you do not know.
</status_codes>

<operations>
- **A cold load is invisible on the wire.** Startup loads nothing, and a load runs before headers are sent: no `message_start`, no `ping`. A non-streaming client cannot tell a loading model from a hung server.
- **`POST /v1/models/{id}/load` moves that wait into a request you can label.** Unknown id is a 400; busy is a 503 with `Retry-After`; 500 is a genuine load failure. `?warm=true` also runs a 1-token generation to pay the Metal kernel JIT, behind the generation gate: use it on startup or model switch, not per request. A failed warm is still a 200 (`warmed: false`).
- **One model is resident by default (LRU), and one engine family at a time**: switching between MLX and gguf evicts the other. Batch work by model.
- **Inference has no API key.** An admin token gates admin routes only; an integration needs neither. **The Host check** answers 403 to a `Host` that is not an IP, `localhost`, the machine's own name or an `allowed_hosts` entry in `heylook.toml`: a LAN client using a DNS name hits it. **There is no CORS**: a browser app is same-origin or proxies.
- **Send a fresh `X-Request-ID` on every request**: a new UUID each time. A reused id cancels every request sharing it. It is echoed on every response and is the cancel handle: `DELETE /v1/requests/{request_id}`. Without it, the server's id is one you never learn on the non-streaming path.
- **Cancel non-streaming calls explicitly.** A stream is cancelled by hanging up; a non-streaming request keeps holding the GPU after the client leaves. A cancelled run returns what it produced with `stop_reason: "max_tokens"`, indistinguishable from budget exhaustion, so track your own cancels. Detail: `references/wire_reference.md`.
- **Telemetry is always on and never guaranteed.** `performance` is `null` for a run with no tokens, and every field is optional: present is a real measurement, absent means this mode could not measure it. The throughput denominator is `generation_duration_ms` (excludes queue wait and load). Time to first token is never returned: time the first delta yourself.
</operations>

<references>
| File | Holds | Load when |
|---|---|---|
| `references/wire_reference.md` | Every `/v1/messages` field, block, stream event, error, and the `/v1/models` row | Writing or debugging a request |
| `references/older_servers.md` | Every version boundary, by topic | The server predates `metadata.verified_against`, or the client must support a range |
| `references/openai_wire.md` | Porting off the removed `/v1/chat/completions` | An OpenAI-SDK client points at heylook, or that route answers 404 |
| `references/routes.md` | Every route by audience; the conversation store | A route beyond inference, or server-side history |
| `references/gemini_migration.md` | Field-by-field Gemini mapping and structural mismatches | Adding heylook beside a Gemini integration |
| `references/client_recipes.md` | Streaming clients in Python and TypeScript; image resize and image-plan | Writing the client |
| `${CLAUDE_SKILL_DIR}/scripts/probe.py` | Capability matrix from a live server | Discovery |

Authoritative beyond all of these: the running server's `/openapi.json`, then `docs/api_integration.md` in the heylook repo (the GitHub copy lags an unpushed local server).
</references>
