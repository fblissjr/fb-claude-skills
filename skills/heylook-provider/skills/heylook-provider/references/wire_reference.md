# `/v1/messages` wire reference

Complete field, block, event and error reference for heylook's Messages
endpoint. Verified against heylookitsanllm 1.79.40
(`src/heylook_llm/schema/messages.py`, `content_blocks.py`, `responses.py`,
`converters.py`, `messages_api.py`).

Servers before 1.79.39 differ on three payloads: the image block accepted
only the flat spelling, the thinking block and delta carried only `text`,
and `stop_reason` was `"stop"` / `"length"`. Those versions also declared an
`"error"` stop reason that nothing could emit — it was removed in 1.79.40
rather than fixed, so no client ever needed a branch for it.

In practice only `end_turn` and `max_tokens` occur. `stop_sequence` is
declared and mapped but unreachable, since both engines report OpenAI's
`stop`/`length`; it is kept because Anthropic's own spec defines it, so a
client written against that spec already handles it and declaring it costs
nothing. That is the distinction `"error"` failed: unreachable-and-standard
is harmless, unreachable-and-bespoke makes clients write a branch for you.

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

### Image

Anthropic's nested `source`, which is what an Anthropic SDK sends:

```json
{ "type": "image", "source": { "type": "base64",
  "media_type": "image/jpeg", "data": "<raw base64>" } }
```

```json
{ "type": "image", "source": { "type": "url", "url": "https://..." } }
```

heylook's original flat spelling is also accepted and normalizes to the
same block, so existing clients keep working:

```json
{ "type": "image", "source_type": "base64",
  "media_type": "image/jpeg", "data": "<raw base64>" }
```

| Field (flat form) | Notes |
|---|---|
| `source_type` | `"base64"` or `"url"`; from `source.type` in the nested form |
| `media_type` | required for base64, e.g. `image/jpeg` |
| `data` | base64 with **no** `data:` URI prefix |
| `url` | used when the source type is `"url"` |

Prefer the nested form: heylook's `/v1/conversations` store accepts **only**
that shape, so it is the one that works on every surface.

Both forms are visible in the generated JSON Schema as of 1.79.40: `source`
is a declared `MediaSource` field and `source_type` is optional there, with a
post-validation check keeping it mandatory in fact. Before that the nested
form existed only in a `mode="before"` validator, which contributes nothing
to the schema — so a client generated from `/openapi.json`, or a
schema-validating proxy, would reject the spelling the docs recommend.

**Two different failures, and only one of them is a 422.** A block carrying
neither `source` nor `source_type` fails validation (422). A block whose
source type IS set — nested `source.type`, or the flat `source_type` —
but which carries no `data` and no `url` validates, then gets **silently
dropped** during conversion: the request succeeds, the text parts survive,
and the model never sees the image. Both spellings behave identically here;
a nested `source` missing its `type` is the 422 case, not the silent one. If a vision answer
describes nothing, inspect the block rather than waiting for a status code.

### Audio — gguf only

```json
{ "type": "audio", "source": { "type": "base64",
  "media_type": "audio/wav", "data": "<raw base64>" } }
```

Both spellings, exactly as for images. `media_type` is advisory; codecs are
sniffed. MLX models answer 400 for any audio part, because audio towers are stripped at load —
that refusal is deliberate and loud rather than a silent drop.

## Non-streaming response

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "...",
  "content": [
    { "type": "thinking", "thinking": "...", "text": "..." },
    { "type": "text", "text": "..." },
    { "type": "logprobs", "tokens": [ ... ] }
  ],
  "stop_reason": "end_turn" | "max_tokens" | "stop_sequence",
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

A thinking block carries its content under **both** `thinking` (Anthropic's
field name) and `text` (heylook's original, kept so existing readers keep
working). Read `thinking`.

`stop_reason` is Anthropic's vocabulary, with no additions. A non-streaming
failure produces no response at all — it is an HTTP 4xx/5xx — so there is no
error member and no branch to write for one. (1.79.39 briefly declared one
on a mechanism that did not exist; 1.79.40 removed it.)

## Streaming

Set `stream: true`. Events in order:

```
event: message_start
data: {"type":"message_start","message":{"id","type","role","model","content":[],"usage":{"input_tokens","output_tokens"}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

  (a thinking block instead opens with
   "content_block":{"type":"thinking","thinking":"","text":""})

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"..."}}

  (inside a thinking block the delta is instead
   {"type":"thinking_delta","thinking":"...","text":"..."})

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{...}}

event: message_stop
data: {"type":"message_stop","performance":{"total_duration_ms":1234, ...}}
```

**`message_stop` terminates the stream. There is no `data: [DONE]`.**

Blocks open and close as the content type switches, so a thinking model emits
a `thinking` block, closes it, then opens a `text` block. Key on
`delta.type` rather than on the block index — index is a running counter
across the whole message, not a stable slot.

`thinking_delta` carries the text under both `thinking` (conformant) and
`text` (heylook's original). Read `thinking`.

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
| 422 | Body failed validation — an out-of-range sampler value, or a media block carrying neither `source` nor `source_type` | FastAPI validation detail |
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
