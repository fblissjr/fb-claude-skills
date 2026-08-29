# `/v1/messages` wire reference

Complete field, block, event and error reference for heylook's Messages
endpoint. Verified against heylookitsanllm 1.79.37
(`src/heylook_llm/schema/messages.py`, `content_blocks.py`, `responses.py`,
`messages_api.py`).

The live `/openapi.json` outranks this file — it is generated from the same
Pydantic models at boot. Use this when you want the shape and the reasoning;
use the schema when you want to confirm a bound.

## Request body

```jsonc
{
  "model": "id from /v1/models",   // optional: falls back to loaded/default model
  "system": "top-level string",     // NOT a system role inside messages
  "messages": [ { "role": "user" | "assistant", "content": string | Block[] } ],

  // sampling — every one optional, absent = server cascade decides
  "max_tokens":              1024,  // > 0
  "temperature":             0.7,   // 0.0 .. 2.0
  "top_p":                   0.95,  // 0.0 .. 1.0
  "top_k":                   40,    // >= 0
  "min_p":                   0.05,  // 0.0 .. 1.0
  "repetition_penalty":      1.05,  // 0.1 .. 2.0
  "repetition_context_size": 64,    // >= 1
  "presence_penalty":        0.0,   // 0.0 .. 2.0
  "seed":                    12345,

  // thinking
  "thinking":                true,          // Messages spelling of enable_thinking
  "reasoning_effort":        "medium",      // MODEL-SPECIFIC vocabulary, see below

  // logprobs
  "logprobs":                true,
  "top_logprobs":            5,     // 0 .. 20

  // heylook extensions
  "sampler":                 "balanced",    // named bundle from /v1/capabilities
  "vision_tokens":           1024,          // 16 .. 16384, per-image visual budget
  "show_special_tokens":     false,         // return declared specials instead of stripping

  "stream":                  true,
  "stream_options":          { "include_usage": true }
}
```

**Absent means the server cascade decides** — per-request, then the named
sampler bundle, then the model's `default_sampler`, then the server floor.
`max_tokens` is deliberately optional here unlike Anthropic's required field:
a hard client-side default silently overrides the model's configured floor
for every request that did not actually have an opinion.

`sampler` names a bundle from the server's `SamplerRegistry`
(`/v1/capabilities` → `samplers.available`). It is not a `/v1/presets` id —
different system, same English word. Presets are saved user prompt+sampler
bundles in the server's own database and are not part of this wire.

`reasoning_effort` accepts the **union** of every served model's vocabulary,
so validation passes values a given model rejects. Qwen3.8 takes
`xhigh|medium|low` and raises otherwise; harmony models take `low|medium|high`.
A wrong-for-this-model value reaches the chat template, and on gguf a raised
jinja exception is a 500. Gate on the `reasoning_effort` capability from
`/v1/models`, and prefer omitting it (the template's own default applies).

`reasoning_effort` is separate from `thinking` on purpose: gpt-oss/harmony
models read reasoning depth and have no `enable_thinking` at all, so gating
depth behind the thinking flag makes it unreachable for the family it was
built for.

## Input content blocks

`content` is either a plain string or a list of blocks.

### Text

```json
{ "type": "text", "text": "..." }
```

### Image — flat, not Anthropic's nested `source`

```json
{ "type": "image", "source_type": "base64",
  "media_type": "image/jpeg", "data": "<raw base64>" }
```

```json
{ "type": "image", "source_type": "url", "url": "https://..." }
```

| Field | Notes |
|---|---|
| `source_type` | required, `"base64"` or `"url"` |
| `media_type` | required for base64, e.g. `image/jpeg` |
| `data` | base64 with **no** `data:` URI prefix |
| `url` | used when `source_type` is `"url"` |

Anthropic's `{"type":"image","source":{"type":"base64",...}}` fails
validation with a 422. The block union is
`TextBlock | ImageBlock | AudioBlock`, and a nested `source` matches none of
them.

A block missing both `data` and `url` is **silently dropped** during
conversion rather than rejected, so a malformed image can present as the
model simply not seeing the picture.

### Audio — gguf only

```json
{ "type": "audio", "source_type": "base64",
  "media_type": "audio/wav", "data": "<raw base64>" }
```

Same flat shape. `media_type` is advisory; codecs are sniffed. MLX models
answer 400 for any audio part, because audio towers are stripped at load —
that refusal is deliberate and loud rather than a silent drop.

## Non-streaming response

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "...",
  "content": [
    { "type": "thinking", "text": "..." },
    { "type": "text", "text": "..." },
    { "type": "logprobs", "tokens": [ ... ] }
  ],
  "stop_reason": "stop" | "length" | "error",
  "usage": { "input_tokens": 0, "output_tokens": 0,
             "thinking_tokens": null, "content_tokens": null },
  "performance": null
}
```

Output block union: `text`, `thinking`, `logprobs`, `hidden_states`.
`thinking_tokens` and `content_tokens` appear only when the model produced a
thinking block.

Join `text` blocks for the answer. A `thinking` block is the model's
reasoning, not its response.

## Streaming

Set `stream: true`. Events in order:

```
event: message_start
data: {"type":"message_start","message":{"id","type","role","model","content":[],"usage":{"input_tokens","output_tokens"}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text"|"thinking"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta"|"thinking_delta","text":"..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"stop"},"usage":{...}}

event: message_stop
data: {"type":"message_stop","performance":{"total_duration_ms":1234, ...}}
```

**`message_stop` terminates the stream. There is no `data: [DONE]`.**

Blocks open and close as the content type switches, so a thinking model emits
a `thinking` block, closes it, then opens a `text` block. Key on
`delta.type` rather than on the block index — index is a running counter
across the whole message, not a stable slot.

### heylook extensions on the same stream

`event: heylook_logprobs`, one per token when `logprobs: true`:

```json
{ "type": "heylook_logprobs",
  "tokens": [ { "token": "...", "token_id": 1, "logprob": -0.1,
                "top_logprobs": [ { "token": "...", "logprob": -2.3 } ] } ] }
```

The entry shape matches the OpenAI wire's `logprobs.content`, so a parser
ported from `/v1/chat/completions` keeps working.

`message_stop.performance` merges optional telemetry beside
`total_duration_ms`: `thinking_duration_ms`, `content_duration_ms`,
`peak_memory_gb`, `kv_cache_bytes`, `queue_wait_ms`, `draft_tokens`,
`draft_accepted`, `draft_acceptance`. **Absent telemetry is omitted, never
null** — test for key presence, not for a null value.

### In-band errors

```
event: error
data: {"type":"error","error":{"type":"invalid_request_error","message":"..."}}
```

`error.type` is `invalid_request_error` (treat as 400) or `api_error` (treat
as 500). On `/v1/messages` an error event **ends** the generation — nothing
follows it. The message is diagnostic text and never model output.

## HTTP errors

| Code | Condition | Body |
|---|---|---|
| 400 | Unknown or disabled `model`; or no `model` given and no server `default_model` | reason plus available ids in `detail` |
| 422 | Body failed validation — most often the image block shape | FastAPI validation detail |
| 500 | Model exists but failed to load: corrupt weights, unsupported architecture | message in `detail` |
| 503 | Generation queue full | `{"error":{"code":"model_overloaded"}}`, `Retry-After` and `X-RateLimit-*` headers |

400 means pick a different model; 500 means that model is broken. The split
is deliberate and worth honouring in client logic — a 400 is recoverable by
falling back to another id, a 500 is not.

## Auth

Both gates are opt-in and off by default; a default localhost deployment is
open.

| Env var | Header | Gates |
|---|---|---|
| `HEYLOOK_API_KEY` | `Authorization: Bearer <key>` | inference: chat completions, messages, embeddings, RLM, hidden states |
| `HEYLOOK_ADMIN_TOKEN` | `X-Heylook-Admin-Token` | admin routes and `/v1/data/clear` |

Loopback traffic is **exempt from the API-key gate by default**, so it
appears only when the client is on another machine — or when the operator has
set `HEYLOOK_API_KEY_ENFORCE_LOOPBACK=true`. Comparison is constant-time.

Send `X-Request-ID` on every request; it is echoed back and is how a request
is correlated in the server's logs.

## Discovery endpoints

`GET /v1/models`:

```json
{ "object": "list", "data": [
  { "id": "...", "object": "model", "owned_by": "user",
    "provider": "mlx" | "mlx_embedding" | "gguf",
    "modalities": ["text", "vision"],
    "capabilities": ["chat", "vision", "thinking", "reasoning_effort"] } ] }
```

`capabilities` is what the server will serve. `modalities` is the
checkpoint author's description. Gate on the former.

`GET /v1/capabilities` returns `server_version`, `optimizations`, Metal
device info, `samplers.available` (the named-bundle roster), an `endpoints`
map and `features`. Query once at integration time for the sampler names.
