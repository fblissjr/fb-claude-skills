# `/v1/messages` wire reference

Field, block, event and error reference for heylook's Messages endpoint, read
out of `src/heylook_llm/schema/messages.py`, `schema/responses.py`,
`content_blocks.py`, `messages_api.py`, `stop_sequences.py`,
`perf_collector.py` and `providers/contract.py`. The heylookitsanllm version it
states is in SKILL.md's frontmatter, one home for that number. Every older
behaviour is in `older_servers.md`, not here.

The live `/openapi.json` outranks this file: it is generated from the same
Pydantic models at boot. Use this for the shape and the reasoning; use the
schema to confirm a bound.

## Request body

```jsonc
{
  "model": "id from /v1/models",   // required in practice: absent is a 400 listing the ids
  "system": "top-level string",     // NOT a system role inside messages
  "messages": [ { "role": "user" | "assistant", "content": string | Block[] } ],

  // sampling: every one optional, absent = server cascade decides
  "max_tokens":              1024,  // > 0
  "temperature":             0.7,   // 0.0 .. 2.0
  "top_p":                   0.95,  // 0.0 .. 1.0
  "top_k":                   40,    // >= 0
  "min_p":                   0.05,  // 0.0 .. 1.0
  "repetition_penalty":      1.05,  // 0.1 .. 2.0
  "repetition_context_size": 64,    // >= 1
  "presence_penalty":        0.0,   // 0.0 .. 2.0
  "seed":                    12345,

  // ending
  "stop_sequences":          ["\n\nUser:"],  // up to 16 strings, 1..256 chars each

  // thinking
  "thinking":                true,  // or {"type": "enabled"|"disabled", "budget_tokens": N}
  "reasoning_effort":        "<a word from engine.thinking.depth.values>",

  // structured output (OpenAI's shape)
  "response_format":         { "type": "json_schema", "json_schema": { "schema": { } } },

  "stream":                  true,
  "metadata":                {"k": "v"}   // string->string, passed through to the response
}
```

**Absent means the server cascade decides**: the server floor, then the
publisher's own recommended settings (the model directory's
`generation_config.json` on MLX, the GGUF header's `general.sampling.*` block
on gguf), then the model's config, then the request. "Send what you have an
opinion about, omit the rest" therefore means *use the publisher's value*, not
*use a generic default*. `max_tokens` is optional here, unlike Anthropic's
required field: a hard client-side default overrides the model's configured
floor on every request that had no opinion. Each `/v1/models` row reports what
a silent request resolves to (`sampler_defaults`) and which layer each value
came from (`sampler_sources`).

A cascade field is **nullable with no default** in the generated schema
(`anyOf` with `null`); a field with `"default": false` and no null member is a
plain flag whose absence means `false`. `stream` is such a flag.

### Stop sequences

Honoured on both engines, the same way. The reply is matched on its **text
only**, never on thinking; when a sequence appears, the reply is cut before
it, generation aborts, `stop_reason` is `"stop_sequence"`, and `stop_sequence`
names the match on the non-streaming body and on `message_delta.delta`.

### Thinking

`thinking` is the template's thinking switch. A bool and Anthropic's object
mean the same switch; the object may also carry `budget_tokens`, a hard cap
the engine enforces on models with the `thinking_budget` capability and a 400
elsewhere. Both object fields are optional: an absent `type` keeps the model's
default, so a budget can be set without deciding the switch. Absent
`thinking` is the model's default, which the row reports as
`thinking_default`.

`reasoning_effort` is separate from `thinking` on purpose: harmony (gpt-oss)
models read reasoning depth and have no thinking switch at all. The schema
accepts any word matching `^[A-Za-z0-9_-]+$` up to 32 characters. What a model
accepts is its template's own vocabulary, published per model at
`engine.thinking.depth` on `/v1/models`. A value the model does not offer is a
**400 naming the valid values**, returned before any stream opens or model
loads, and so is any value sent to a model whose template has no depth
control. The exception is `depth.unknown: "verbatim"` (gpt-oss, for one): the
template pastes any word in, so every value is accepted. The value reaches the
template under the template's own variable name (`depth.variable`), whether or
not thinking is on. Show the template's own words and never translate between models:
there is no shared low/medium/high scale. Omitting it applies the template's
default.

| `depth` key | Meaning |
|---|---|
| `variable` | The template variable the value is sent as |
| `values`, `aliases`, `default` | The words to offer, other spellings the template accepts, and what applies when you send none |
| `off` | Values that render identically to thinking switched off. Present them as "thinking off", not as a level |
| `changes_prefix` | Switching depth changes the rendered prompt prefix, so it costs prompt-cache reuse |
| `unknown` | What the template does with a value it does not recognise: `raises`, `ignored`, `verbatim` or `fallback`. Under `verbatim` any word is accepted, so offer a text box with `values` as suggestions |

### Structured output

`response_format` is OpenAI's shape, which llama-server also takes:
`{"type": "json_schema", "json_schema": {"schema": {...}}}` makes the reply a
JSON document matching the schema; `{"type": "json_object"}` any JSON object;
`{"type": "text"}` free text. Thinking is not constrained. It is a 400 on
harmony models, on masked-diffusion models, and combined with a continuation.

### Continuation

A trailing assistant message is **continued**, not answered, and a trailing
assistant message holding only a `thinking` block resumes inside that thought.
There is no flag to force the other reading.

### Fields refused, and fields ignored

The request model does not forbid unknown fields, by design (a blanket forbid
would 422 an Anthropic SDK sending fields heylook does not implement). So an
unknown field is **dropped silently**, and a typo in an optional field is a
no-op that answers 200. The exceptions are the fields a client plausibly
sends, which are refused with a 422 that names the fix:

| Sent | Answer |
|---|---|
| `tools`, `tool_choice` | 422: tool use is not built |
| `logprobs`, `top_logprobs` | 422: removed |
| `vision_tokens` | 422: removed; cap pixels client-side and ask `image-plan` for the cost |
| `sampler`, `preset` | 422: named sampler bundles were removed; send the sampler fields. `/v1/presets` is a separate system and the client expands a preset into those fields |
| `show_special_tokens: true` | 422; `false` is what the server does anyway |
| `enable_thinking` | 422: send `thinking` |
| `max_new_tokens` | 422: send `max_tokens` |
| `system_prompt` | 422: send `system` |
| `chat_template_kwargs` | 422: send `thinking` and `reasoning_effort` |
| `stream_options`, `include_performance` | ignored: removed, and nothing reads them |

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

heylook's original flat spelling is also accepted and normalizes to the same
block:

```json
{ "type": "image", "source_type": "base64",
  "media_type": "image/jpeg", "data": "<raw base64>" }
```

| Field (flat form) | Notes |
|---|---|
| `source_type` | `"base64"` or `"url"`; from `source.type` in the nested form |
| `media_type` | required for base64, e.g. `image/jpeg` |
| `data` | base64 with **no** `data:` URI prefix |
| `url` | `http(s)` only; MLX refuses a local file path with a 400 |

Prefer the nested form: heylook's `/v1/conversations` store accepts only that
shape. Explicit `null` flat fields beside a nested `source` (what a generated
or `model_dump()`-based client emits) are treated as absent. A flat field that
is set wins over the nested object; the nested object is ignored wholesale only
when the two spellings disagree about the kind of source.

A block with a source type but no `data` and no `url` is a 422 naming the
missing field. An image that cannot be decoded is a 400, or an in-band
`invalid_request_error` on a stream.

### Audio: gguf only

```json
{ "type": "audio", "source": { "type": "base64",
  "media_type": "audio/wav", "data": "<raw base64>" } }
```

Both spellings, exactly as for images. `media_type` is advisory; codecs are
sniffed. MLX models answer 400 for any audio part, because audio towers are
stripped at load.

## Non-streaming response

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "...",
  "content": [
    { "type": "thinking", "thinking": "...", "text": "..." },
    { "type": "text", "text": "..." }
  ],
  "stop_reason": "end_turn" | "max_tokens" | "stop_sequence",
  "stop_sequence": null,
  "usage": { "input_tokens": 0, "output_tokens": 0,
             "cache_read_input_tokens": null,
             "thinking_tokens": null, "content_tokens": null },
  "performance": { "...": "see Telemetry" }
}
```

Output blocks are `text` and `thinking` only. Join `text` blocks for the
answer; a `thinking` block is the model's reasoning, not its response. A
thinking block carries its content under both `thinking` (Anthropic's field)
and `text` (heylook's original); read `thinking`.

`usage.input_tokens` is what this request **processed**; the part of the
prompt reused from a previous request is `cache_read_input_tokens`, so the
whole prompt is their sum. A null `cache_read_input_tokens` means the engine
reported nothing about reuse, not a claimed zero. `output_tokens` is the
engine's own count. `thinking_tokens` and `content_tokens` count emitted text
segments, not engine tokens: an approximate split that **need not sum to
`output_tokens`** (template markers, the end-of-sequence token and
multi-token characters emit no segment of their own). They are null when the
reply had no thinking.

`stop_reason` is Anthropic's vocabulary with no additions. A non-streaming
failure is an HTTP 4xx/5xx with no response body of this shape.

## Streaming

Set `stream: true`. Events in order:

```
event: message_start
data: {"type":"message_start","message":{"id","type","role","model","content":[],"usage":{"input_tokens":0,"output_tokens":0}}}

event: heylook_progress        (zero or more, during prefill)
data: {"type":"heylook_progress","prefill":{"processed":512,"total":2048}}

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
data: {"type":"message_stop","performance":{...}}
```

**`message_stop` terminates the stream. There is no `data: [DONE]`.**

**`event: ping`** (`{"type":"ping"}`, Anthropic's own keepalive) is sent after
every 5 seconds of silence, during prefill and decode. Ignore it, and ignore
any event type you do not recognise. A cold model load still happens before
headers are sent, so no ping covers it.

`message_start.usage.input_tokens` is 0, because it is emitted before the
first chunk; read usage from `message_delta`. When a stop sequence ended the
reply, `message_delta.delta` also carries `stop_sequence`.

Blocks open and close as the content type switches, so a thinking model emits
a `thinking` block, closes it, then opens a `text` block. Key on `delta.type`
rather than on the block index: index is a running counter across the whole
message, not a stable slot. Image requests report prefill progress too, and
are cancellable mid-prefill.

### In-band errors

```
event: error
data: {"type":"error","error":{"type":"invalid_request_error","message":"..."}}
```

`error.type` is `invalid_request_error` (treat as 400) or `api_error` (treat
as 500). An error event **ends** the generation; nothing follows it. The
message is diagnostic text, never model output. Refusals that fire after
headers flush arrive this way: an image the model will not take, an image that
cannot be decoded, a prompt longer than the model's context, and a gguf decode
failure (`api_error`).

## Telemetry

`performance` rides `message_stop` on every stream and the non-streaming body
on every run that produced tokens; it is `null` only when the run yielded none
(test for presence, not truthiness). There is no request flag for it. One
builder serves both modes, so the rule is one line:

> Every field, when present, is a real measurement of exactly the thing its
> name says. Absent means this mode or engine could not measure it.

Absent has two spellings: streaming omits the key, non-streaming returns
`null`. Test for `None` if you want one branch for both.

| Field | Meaning |
|---|---|
| `prompt_tps`, `generation_tps` | The engine's own rates. Never synthesized, never `0.0` |
| `request_duration_ms` | Arrival to done, **including** queue wait and model load: user-perceived latency |
| `generation_duration_ms` | Generation only, **excluding** both: the throughput denominator |
| `queue_wait_ms` | Time in the FIFO generation gate. An idle gate reports a tiny nonzero float, so absent means not measured |
| `thinking_duration_ms`, `content_duration_ms` | Time from the first emitted segment of each kind to its end, in both modes. `0` is a real value: under one millisecond, as when a short answer is released in one piece |
| `peak_memory_gb` | MLX only: generation on gguf runs in a subprocess that does not report it |
| `cache` | `{prompt_tokens, cached_tokens, processed_tokens, outcome, cause, reason}`; `outcome` is `reused`, `miss` or `ineligible` |
| `speculative` | When a drafter ran: `{drafted, accepted, emitted, acceptance_rate, draft_share}`; the two rates are different quantities |

Time to first token is not returned in either mode. On a stream, time the
first `content_block_delta` yourself; non-streaming it is unobservable.
Aggregates are at `GET /v1/performance/profile/{1h|6h|24h|7d}`.

## HTTP errors

| Code | Condition | Body |
|---|---|---|
| 400 | No `model`, or an unknown or disabled one | reason plus available ids in `detail` |
| 400 | The model refuses the input: images to a text-only model, audio to any MLX model, an image on a non-user turn on MLX, an undecodable image, a local file path on MLX, a prompt over the context window, an unoffered `reasoning_effort`, `budget_tokens` without `thinking_budget`, `response_format` where it is refused (non-streaming; on a stream, see In-band errors) | message in `detail` |
| 403 | Host check: the `Host` header is not an IP, `localhost`, one of the machine's own names, or an `allowed_hosts` entry in `heylook.toml` | names the fix |
| 409 | A conversation-store write while that conversation is generating | A second `generate` answers `{"error":{"code":"generation_in_progress"}}`; a message write answers a plain `detail`. Key on the status, restore the user's text, and retry after the run ends |
| 422 | Body failed validation: a refused field (table above), an out-of-range value, a media block with no payload | FastAPI validation detail |
| 500 | Model exists but failed to load, or a gguf decode failed | message in `detail` |
| 503 | Backpressure: the queue is full, or every loaded model is generating so none can be evicted | `{"error":{"code":"model_overloaded"}}` with `Retry-After` and `X-RateLimit-*`. `error.message` names the blocking models; show it rather than a generic retry notice |

400 means pick a different model or input; 500 means that model is broken. A
400 is recoverable by falling back to another id, a 500 is not.

## Access

**There is no inference API key.** `HEYLOOK_ADMIN_TOKEN` (header
`X-Heylook-Admin-Token`) gates the admin routes, `/v1/data/clear` and
`/v1/cache/clear`, and is off when unset. An integration needs neither.
Discovery is never gated, so a 401 from `/v1/models` is something in front of
heylook.

**The Host check** guards against DNS rebinding. A LAN client that reaches the
server by a DNS or VPN name gets a 403 until the operator adds that name to
`allowed_hosts` in `heylook.toml`. Addressing the server by IP always passes.

**There is no CORS.** A browser page on another origin fails at preflight, so
a browser client is served from the same origin or goes through a proxy.

## Request ids and cancelling

Send `X-Request-ID` on every request, **unique per request**: not per session
or per client. It correlates the server's logs and is the handle you cancel
by, so a reused id is a cancel that stops every in-flight request sharing it.
A usable value is `[A-Za-z0-9._:-]`, 1 to 128 characters, matched whole; a
UUID qualifies. A valid id is echoed on every response, including a busy 503
and 4xx errors; only an unhandled 500 lacks it. A missing or malformed id is
replaced by a server-generated one, which you never learn in time on the
non-streaming path, so **sending the header is the precondition for
cancelling at all**.

```http
DELETE /v1/requests/{request_id}
```

| Response | Meaning |
|---|---|
| `200 {"cancelled": N, "request_id": "..."}` | N in-flight generations were signalled. A **count**, since two requests may share an id |
| `404` | Nothing is running under that id. Usually it already finished; otherwise the original request carried no usable id. Treat it as "too late" |
| `422` | The id is malformed and could never have been tracked. Fix the id generator; retrying cannot help |

**This matters most for non-streaming calls.** A stream is cancelled by
hanging up, since the server notices the dead peer on its next write. A
non-streaming request writes nothing until done and does not poll for
disconnects, so an abandoned run keeps the GPU and blocks the queue. Call
DELETE.

**Cancellation is cooperative**: an abort flag checked between tokens, then a
normal unwind. A partial run against a conversation persists what it produced.

**There is no cancellation stop value.** A cancelled run returns what it
generated with `stop_reason: "max_tokens"`, unless the engine had already
reported `stop_sequence`. It is indistinguishable from budget exhaustion:
**track your own cancel, never infer it from the response.**

## Discovery endpoints

`GET /v1/models`:

```jsonc
{ "object": "list", "data": [
  { "id": "...", "object": "model", "owned_by": "user",
    "provider": "mlx" | "gguf",
    "modalities": ["text", "vision"],
    "capabilities": ["chat", "vision", "thinking", "reasoning_effort"],
    "thinking_default": true,
    "sampler_defaults": { "off": {"temperature": 1.0, "top_k": 64}, "on": {"...": 0} },
    "sampler_sources":  { "...": "model | vendor | default" },
    "engine": {
      "runtime":  { "value": "mlx-vlm", "provenance": "...", "source": "..." },
      "context":  { "length": { "value": 262144, "...": "..." }, "running": { "value": 32768 } },
      "template": { "...": "which chat template is in force, incl. prefix_stable" },
      "settings": { "<field>": { "value", "configured", "auto", "reason", "provenance", "effect" } },
      "cache":    { "...": "how this model reuses a prompt" },
      "thinking": { "switch": "...", "depth": { "variable", "values", "aliases", "default",
                                                "unknown", "changes_prefix", "off" },
                    "budget": { "enforced", "reason" }, "template": "..." },
      "image":    { "...": "image geometry" },
      "speculative": { "drafter", "type", "in_force" },
      "decoding": { "mode": { "value": "autoregressive" }, "request_fields": { "value": null } }
    } } ] }
```

`capabilities` is what the server will serve; `modalities` is the checkpoint
author's description. Gate on the former. The capabilities are `chat`,
`vision`, `audio` (gguf only), `thinking` (a switch detected in the template in
force), `reasoning_effort` (a detected depth control) and `thinking_budget`.

The `engine` object has one shape on every engine and answers for unloaded
models too. Its leaves are **facts**, `{value, provenance, source}`: read
`.value` through one helper rather than at each call site. What a client
gates on:

- `engine.context.length.value`: the model's window (null where the files do
  not say). Size a prompt against it rather than learning the ceiling from a
  400.
- `engine.thinking.depth.values`: the `reasoning_effort` vocabulary.
- `engine.decoding.request_fields.value`: the request fields this engine path
  reads; null means every sampler field. Hide a control whose field is not
  listed.

`thinking_default` is what thinking resolves to when the request says nothing;
label a "model default" control with it. `sampler_defaults` is what every
sampler key resolves to for a silent request, keyed by the thinking state
(`off` / `on`) because the anti-loop overlay changes the numbers.

MLX's `vision` capability and its refusal come from one resolver, so they
cannot disagree. Three arms stay open, so handle the refusal regardless:

- A vision-capable MLX model refuses an image on a non-user turn: mlx-vlm
  would relocate it to the last user turn without saying so. gguf accepts it.
- An explicit `capabilities` list in the model's config (`heylook.toml`, or a
  `model.heylook.toml` beside the weights) is an **override** honoured
  verbatim on either provider.
- gguf has no guard of its own. It advertises `vision` only when the model has
  an mmproj projector (a declared modality alone advertises nothing; `audio`
  needs the projector and the modality), then forwards the block to
  `llama-server`. A 400 from llama-server becomes the same refusal (a 400, or
  an in-band `invalid_request_error`); any other llama-server status is a 500
  or `api_error`. The status and error type match MLX, but the message is
  llama-server's own text, so never string-match refusal messages across
  engines. If llama-server accepts the block and ignores it, nothing refuses:
  a 200 describing an image the model never used, decided by the model's
  packaging.

### Image cost

```http
POST /v1/models/{id}/image-plan
{"sizes": [[1920, 1080], [4032, 3024]]}
```

Takes 1 to 16 `[width, height]` pairs, each side 1 to 16384: the size each
image will be sent at. Returns `{model_id, engine, images: [{size, tokens,
target}], source}`: the prompt tokens each image adds and the size the engine
resizes it to (`target` is null on gguf, where llama.cpp does not say). The
numbers come from the engine itself: the loaded MLX model's processor, or
llama-server's token counter. Planning never loads a model, so a model that is
not resident is a **409**; a model served without images is a 400.

### Loading

`POST /v1/models/{id}/load[?warm=true]` loads a model ahead of the first
request. Unknown or disabled id is a 400; busy (every loaded model generating)
is a 503 with `Retry-After`; any real load failure is a 500, the same split
`/v1/messages` makes. `warm=true` also runs a 1-token generation to pay
the Metal kernel JIT, behind the global generation gate; a failed warm is still
a 200 with `warmed: false` and `warm_error`, and the model is loaded either
way.

One model is resident by default (LRU eviction), and one engine family at a
time: loading an MLX model evicts resident gguf models and the reverse.

`GET /v1/capabilities` returns `server_version`, `optimizations`, Metal device
info, an `endpoints` map and `features`.
