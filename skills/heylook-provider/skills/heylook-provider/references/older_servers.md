# Older heylook servers

SKILL.md and `wire_reference.md` state current behaviour, as of the version in
SKILL.md's frontmatter. This file holds every version boundary they no longer
carry. Read `server_version` from `/v1/capabilities`, then read only the
entries above that version: each one names what a server below it does
differently. A client that must support a range of servers handles every arm
the range spans.

## Payload conformance

- **Before 1.79.39** the image block was flat (`source_type` on the block,
  nested `source` a 422), the thinking field was `text` only, and
  `stop_reason` was `"stop"` / `"length"`. The flat image spelling is still
  accepted, and thinking blocks still carry `text` alongside `thinking`.
- **Through 1.79.40** the unreachable `error` stop reason was still declared.
  Nothing could emit it, so no client needs a branch for it.
- **Through 1.79.40** the nested `source` was validator-only, so that
  version's `/openapi.json` rejects the spelling SKILL.md recommends even
  though the server accepts it.
- **Through 1.79.40** a nested `source` sent alongside explicit `null` flat
  fields (what a generated or `model_dump()`-based client emits) was a 422
  saying `source_type` is required. Serialize with `exclude_none` against
  those builds.
- **At or below 1.79.41** a media block with `source_type` but no `data` and
  no `url` passed validation and was dropped during conversion: the request
  succeeded, the text survived, and the model never saw the image. 1.79.42
  makes it a 422 naming the missing field. On 1.79.41 a set flat field also
  suppressed the whole nested object. Against older servers no status code
  reveals a dropped image, so if a vision answer describes nothing, check the
  block's payload.
- **Before 2.0.40** the output block union also declared `hidden_states`, and
  hidden-states and embeddings routes existed.
- **Before 2.0.121** an image that could not be decoded was silently replaced
  rather than refused. **Before 2.0.128** MLX accepted a local file path as an
  image source.

## Request fields

- **1.79.49** removed `include_performance`; it never controlled anything.
- **1.79.74** removed `logprobs`, `top_logprobs` and the `heylook_logprobs`
  SSE event. The 422 naming the removal is reachable only **from 1.79.79**;
  on 1.79.74-1.79.78 the key is dropped in silence and the request answers
  200.
- **Before 2.0.23** gguf had no vendor rung in the sampler cascade: a request
  omitting `top_k` resolved to the server floor, not to the GGUF header's
  `general.sampling.*` value. Same client code, different output.
- **Before 2.0.30** a `sampler` field named a bundle from
  `/v1/capabilities` → `samplers.available`, and models had a
  `default_sampler`. From 2.0.30 `sampler` and `preset` are a 422 and the
  `samplers` key is gone.
- **Before 2.0.38** `show_special_tokens: true` returned declared special
  tokens instead of stripping them. From 2.0.38 it is a 422.
- **Before 2.0.45** the server floor for `max_tokens` was 4096; it is now
  16384.
- **Before 2.0.50** `enable_thinking`, `max_new_tokens` and `system_prompt`
  were dropped silently (a 200 with the cascade default). **Before 2.0.86**
  the same held for `chat_template_kwargs`. Now each is a 422 naming the
  field to send.
- **Before 2.0.64** `vision_tokens` capped the visual token budget per image.
  On 2.0.64 through 2.0.177 it is accepted and ignored, so a client still
  sending it gets no cap and no error. From 2.0.178 it is a 422.
- **Before 2.0.91** `thinking` was a bool only; the object form and
  `budget_tokens` arrived in 2.0.91.
- **Before 2.0.95** `reasoning_effort` was validated against the union of
  every served model's values, so a value wrong for the chosen model reached
  the chat template and could come back as a 500. From 2.0.95 it is the
  template's own vocabulary, and an unoffered value is a 400 before any
  stream opens. `engine.thinking.depth.off` arrived in 2.0.159.
- **Before 2.0.148** `stream_options` was declared; it has always been read by
  nothing and is now ignored.
- **Before 2.0.150** a request with no `model` fell back to a loaded or
  default model. It is now a 400 listing the ids.
- **Before 2.0.151** `stop_sequences` was ignored with no error, so generation
  ran past it and `stop_reason: "stop_sequence"` could not occur. `tools` and
  `tool_choice` were dropped silently rather than refused.
- **Before 2.0.155** there was no `response_format`: prompt for the shape and
  parse defensively. **Before 2.0.181** gguf passed the schema to
  llama-server as its top-level `json_schema`, which clashed with some
  templates' reasoning grammar and answered 400 "Failed to initialize
  samplers" where the same schema now works.
- **Before 2.0.181** the documented rule was that `budget_tokens` without the
  `thinking_budget` capability is a 400; the server never did that outside MLX
  harmony models.

## Usage and telemetry

- **Before 1.79.54** the two rates inside `performance` were declared required
  while the stream never sent them, and `kv_cache_bytes`, `queue_wait_ms` and
  `draft_acceptance` were sent on the stream while the schema declared none of
  them, so a generated client dropped them silently. 1.79.55 filtered emitted
  keys to the declared set.
- **Through 1.79.57** the two modes disagreed per field:
  - `total_duration_ms` included queue wait and load non-streaming and
    excluded both streaming. From 1.79.58 it is replaced by
    `request_duration_ms` (includes) and `generation_duration_ms` (excludes).
    Against an older server, read it as `request_duration_ms` non-streaming
    and `generation_duration_ms` streaming.
  - Non-streaming `prompt_tps` was `0.0` when unmeasured; never read it as a
    measured zero.
  - Non-streaming `generation_tps` was synthesized from tokens over elapsed
    time when the engine reported none.
  - The stream also carried `draft_tokens` and `draft_accepted`.
- **Before 1.79.50** non-streaming `performance` on MLX lacked
  `peak_memory_gb`.
- **On 1.79.58** `generation_duration_ms` still contained the queue wait; net
  it out with `queue_wait_ms`. That release also emitted `queue_wait_ms: 0.0`
  unconditionally, which meant nothing on gguf and meant "produced nothing" on
  MLX. From 1.79.59 absent means not measured.
- **Before 2.0.78** `usage.input_tokens` was the whole prompt, and there was
  no `cache_read_input_tokens`, `performance.cache` or `performance.speculative`
  (`draft_acceptance` stood in for the latter until then). From 2.0.78 the
  whole prompt is `input_tokens + cache_read_input_tokens`. **Before 2.0.81**
  `performance` also carried `kv_cache_bytes`.
- **Before 2.0.64** `thinking_duration_ms` and `content_duration_ms` were
  streaming-only.
- **Before 2.0.183** a non-streaming run with no tokens answered
  `performance: null`, while the stream carried its two durations.
- **Before 2.0.91** non-streaming `usage.thinking_tokens` and
  `content_tokens` were not filled.

## Streaming

- **Before 2.0.13** a gguf decode failure was an empty success: the run ended
  `end_turn` with empty `content` and no error. Treat a zero-token `end_turn`
  on gguf as a possible failure on those builds. From 2.0.13 it is a 500
  non-streaming and an in-band `api_error` streaming.
- **Before 2.0.55** image requests reported no prefill progress, and before
  2.0.59 they could not be cancelled mid-prefill.

## Capability gating and discovery

- **Before 1.79.43** MLX's `vision` capability came from the checkpoint's own
  `config.json` while the refusal came from the model as loaded, so a
  hand-made variant could advertise `vision` and then refuse it. Since 1.79.43
  one resolver answers both.
- `thinking_default` arrived in **1.79.63**, a top-level `context_length` in
  **1.79.65**, and `sampler_defaults` in **2.0.21** (gguf values corrected in
  2.0.25).
- **Before 2.0.18** a vision-capable MLX model accepted an image on a
  non-user turn and mlx-vlm silently moved it to the last user turn.
- **Before 2.0.73** a row carried top-level `context_length`,
  `context_running` and `effective_loader`, and `provider` could be
  `mlx_embedding`. From 2.0.73 they are `engine.context.length`,
  `engine.context.running` and `engine.runtime`, each a fact read at `.value`.
- **Before 2.0.91** there was no `thinking_budget` capability. **Before
  2.0.95** gguf's `thinking` capability did not come from the template in
  force.
- **Before 2.0.101** there was no `image-plan` route.
- **Before 2.0.147** a gguf model advertised `vision` from a declared modality
  without a projector, which llama-server cannot serve.
- **Before 2.0.163** rows had no `sampler_sources`.
- `engine.thinking.depth.off` arrived in 2.0.159; the schema's own
  description of `engine.thinking` omitted it until 2.0.179.

## Access

- **Before 2.0.123** the server sent CORS headers, so a browser page on
  another origin could call it.
- **Before 2.0.127** `HEYLOOK_API_KEY` (`Authorization: Bearer`) gated some
  inference routes, plus `/v1/models/{id}/load` and `DELETE /v1/requests/{id}`;
  loopback was exempt unless `HEYLOOK_API_KEY_ENFORCE_LOOPBACK=true`.
  Discovery was never gated.
- **Before 2.0.137** there was no Host check, so no 403 for a DNS name.

## Removed routes

- **1.79.66** removed `/v1/chat/completions` and
  `/v1/batch/chat/completions` (see `openai_wire.md`).

## Cancellation and request ids

- **Before 1.79.44** there is no `DELETE /v1/requests/{request_id}`, and
  `/v1/messages` ignored `X-Request-ID` and generated its own.
- **On 1.79.44 and 1.79.45** the non-streaming response did not echo
  `X-Request-ID`, so a client could not tell its id had been rejected.
- **Through 1.79.51** a malformed id on DELETE answered 404, not 422.
- **Before 2.0.182** a request was registered for cancelling only after its
  model loaded, so a DELETE during a cold load answered 404 as if the run had
  already finished, and the run went ahead. Against those servers, load the
  model first (`/load`) or repeat the DELETE until the call returns.
- **Before 2.0.181** a conversation message write or delete during a
  generation answered 409 with a bare `detail`; only a second `generate` had
  the `generation_in_progress` envelope.
- **Before 2.0.138** the busy 503 and 4xx responses carried no
  `X-Request-ID` echo (2.0.141 completed the rest).

## Model load and residency

- **Before 1.79.48** the load route was `/v1/admin/models/{id}/load` behind
  the admin token. It moved to `/v1/models/{id}/load`; the admin URL answers
  405 on newer servers.
- **Through 1.79.52** busy on the load route came back as a **500** carrying
  the `MODEL_BUSY` token in `detail`; key on that token against those builds.
  From 1.79.53 busy is a 503 with `Retry-After`.
- **Before 2.0.178** a load that failed with a bare `ValueError` answered 400
  on the load route (500 on `/v1/messages`), so a 400 there did not always
  mean an unknown id.
- **Before 2.0.49** MLX and gguf models could be resident together; from
  2.0.49 loading one engine family evicts the other.
