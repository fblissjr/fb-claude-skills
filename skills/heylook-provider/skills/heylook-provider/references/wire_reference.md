# `/v1/messages` wire reference

Complete field, block, event and error reference for heylook's Messages
endpoint, read out of `src/heylook_llm/schema/messages.py`,
`content_blocks.py`, `responses.py`, `converters.py` and `messages_api.py`.
The heylookitsanllm version this was verified against is in SKILL.md's
frontmatter — one home, so there is no second copy here to drift.

Servers before 1.79.39 differ on three payloads: the image block accepted
only the flat spelling, the thinking block and delta carried only `text`,
and `stop_reason` was `"stop"` / `"length"`. Separately, **every version
through 1.79.39** declared an `"error"` stop reason that nothing could emit;
1.79.40 removed it rather than making it reachable, so no client ever needed
a branch for it. That scope includes 1.79.39 itself, which is otherwise the
first conforming release.

In practice only `end_turn` and `max_tokens` occur, and `max_tokens` carries
two meanings — a cancelled run reports it too, indistinguishably from budget
exhaustion (see [Cancelling a request](#cancelling-a-request)).
`stop_sequence` is declared and mapped but unreachable, since both engines
report OpenAI's `stop`/`length`; it is kept because Anthropic's own spec
defines it, so a client written against that spec already handles it and
declaring it costs nothing. That is the distinction `"error"` failed: unreachable-and-standard
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
  "stream_options":          { "include_usage": true },
  "metadata":                {"k": "v"}   // string->string, passed through to the response
}
```

**`stop_sequences` is NOT accepted.** Anthropic takes it on the request;
heylook's request model has no such field, so it is ignored rather than
honoured — a port that relies on it generates straight past the sequence it
was meant to stop at, with no error to notice. There is no server-side
equivalent; stop on the client, or rely on the model's own end-of-turn.

**Absent means the server cascade decides** — per-request, then the named
sampler bundle, then the model's `default_sampler`, then the server floor.
`max_tokens` is deliberately optional here unlike Anthropic's required field:
a hard client-side default silently overrides the model's configured floor
for every request that did not actually have an opinion.

**That cascade covers the sampling knobs, and the generated schema tells you
which those are** — no roster to keep here, because a roster is what went
stale when `include_performance` was removed. A cascade field is **nullable
with no default** (`anyOf` with `null`); a field carrying `"default": false`
and no null member is a plain flag whose absence means `false` permanently,
with no server-side config behind it. Check the field in `/openapi.json` and
the shape answers it. `show_special_tokens` and `stream` are the flags on this
request today.

**`include_performance` is not a field on this wire, as of 1.79.49.** It was
declared through 1.79.48 and never read: the Messages route returns telemetry
**unconditionally in both modes** — `message_stop.performance` on every stream,
a `performance` object on every non-streaming run that produced tokens — and
the bundled frontend's status lines read the streaming half. So gating the
non-streaming half alone would have split the two modes against each other,
and gating both would have broken that frontend. Unconditional telemetry is
the design here; the flag was what did not fit it, and it was removed rather
than wired up. **Do not send it to `/v1/messages`** — there is nothing to
ask for. It is not a wire break either way: the request model sets no
`extra="forbid"`, so an unknown field is ignored rather than rejected, and an
existing client needs no change. On `/v1/chat/completions` the flag is real
and absent genuinely means no performance block; keep sending it there.

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

**Explicit `null` flat fields beside a nested `source` are fine as of
1.79.41 — and were a 422 before it.** Because `source_type` is optional in
the schema, a client generated from `/openapi.json`, or any pydantic client
calling `model_dump()` without `exclude_none`, emits every unset optional
rather than omitting it:

```json
{ "type": "image", "source_type": null, "media_type": null, "data": null,
  "source": { "type": "base64", "media_type": "image/jpeg", "data": "..." } }
```

Through 1.79.40 the normalizer tested key PRESENCE in two places — the gate
and the `setdefault` under it — so those nulls suppressed the flattening and
the block was rejected as "requires `source_type`", on the exact spelling
this reference recommends. 1.79.41 treats null as absent in both. **If you
target servers at or below 1.79.40, serialize with `exclude_none` (or send
the flat form);** it is the single most likely way a correctly-written
Anthropic-style client fails against an older heylook. A flat field that is
actually set still wins over the nested object on every version.

**A payload-less block is a 422 as of 1.79.42, and was a SILENT DROP before
it.** A block carrying neither `source` nor `source_type` has always failed
validation. A block whose source type IS set — nested `source.type`, or the
flat `source_type` — but which carries no `data` and no `url` used to
validate and then get **silently dropped** during conversion: the request
returned **200**, the text parts survived, and the model never saw the image,
so the caller got a confident answer about a picture that was never sent.
1.79.42 rejects it with a message naming the missing field. Both spellings
behave identically, and a nested `source` missing its `type` was always the
422 case.

**Against servers at or below 1.79.41 this is the failure to defend
against**, because no status code reveals it: if a vision answer describes
nothing, inspect the block's payload rather than trusting the 200.

**Filling from `source` is per FIELD as of 1.79.42.** 1.79.41 suppressed the
whole nested object as soon as any flat field was set, so
`{"source_type":"base64","source":{...,"data":"..."}}` resolved the type and
dropped the image. The nested object is ignored wholesale only when the two
spellings DISAGREE about the kind of source (flat `source_type:"url"` against
nested `type:"base64"`), where merging would build a block you never
described.

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
  "performance": { "prompt_tps": 0.0, "generation_tps": 0.0,
                   "request_duration_ms": 0, "generation_duration_ms": 0,
                   "queue_wait_ms": 0.0044, "peak_memory_gb": 0.0,
                   "thinking_duration_ms": null, "content_duration_ms": null }
}
```

Output block union: `text`, `thinking`, `logprobs`, `hidden_states`.
`thinking_tokens` and `content_tokens` appear only when the model produced a
thinking block.

`performance` is present on any run that produced tokens (it is `null` only
when the generation yielded none — test for presence, not for truthiness).
The object is built by one shared function for both modes from **1.79.58**, so
the field set is the same on both paths and the reading rule is one line:

> Every field, when present, is a real measurement of exactly the thing its
> name says. Absent means this mode or engine could not measure it.

Absent has two spellings and one meaning: streaming omits the key,
non-streaming returns an explicit `null` (its response is materialised through
`PerformanceInfo`, so every declared field appears). Test for `None`, not for
key presence, if you want one branch that works on both.

The rates are the engine's own measurements, taken tightly around prefill and
decode. **Nothing is synthesized from 1.79.58** — `generation_tps` is the
engine's figure or absent, never a wall-clock stand-in. What that beats is
dividing tokens by an elapsed time spanning the whole request; the hazard is
the span, not whose clock measured it, and the server ships spans of both kinds
(see the duration fields under Streaming).

**`prompt_tps` is `0.0` when the engine never measured it, on this path, on
every version.** It is assigned raw from the telemetry accumulator, whose field
defaults to `0.0` and latches only on a truthy value, so a run with no prefill
rate emits a real zero rather than omitting the key. **Never read
`prompt_tps == 0` here as "the server measured zero"** — on the streaming path
that same run omits the field entirely. 1.79.54 fixed this shape one layer
down, in the converter's `.get(key, 0)` default, but the builder above it still
hands the converter a genuine `0.0`, so the fix does not reach this field.

What is absent here, and whether you may rely on it, differs by field — the
three cases are set out once under
[Streaming](#heylook-extensions-on-the-same-stream) rather than twice.

**`peak_memory_gb` is MLX-only, on every path and in both modes.** It is
`mx.get_peak_memory()`, reported per chunk by the MLX engine; the gguf provider
never sets it, because generation happens inside a `llama-server` subprocess
that does not report it. **So absent there means "this model runs on the other
backend", not "this server is old"** — and reading it off a stream instead, the
obvious workaround, fails for the same reason. Only if you see it absent on an
*MLX* model is it a version question, and then the answer is 1.79.50: before
that release the non-streaming builder dropped it while the streaming half and
both OpenAI-wire halves carried it.

**Time to first token is not returned, on either mode.** The server computes
it (net of FIFO queue wait) and keeps it for its own collector; no response
field carries it. On a stream you can time the first `content_block_delta`
yourself, but non-streaming TTFT is genuinely unobservable to a client —
anything you compute from a non-streaming response is a different quantity.
Aggregates are at `GET /v1/performance/profile/{1h|6h|24h|7d}`.

Join `text` blocks for the answer. A `thinking` block is the model's
reasoning, not its response.

A thinking block carries its content under **both** `thinking` (Anthropic's
field name) and `text` (heylook's original, kept so existing readers keep
working). Read `thinking`.

`stop_reason` is Anthropic's vocabulary, with no additions. A non-streaming
failure produces no response at all — it is an HTTP 4xx/5xx — so there is no
error member and no branch to write for one. (Declared through 1.79.39 on a
mechanism that did not exist; 1.79.40 removed it — see the version note at
the top of this file.)

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
data: {"type":"message_stop","performance":{"request_duration_ms":1234, ...}}
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

**One builder, one rule, from 1.79.58.** Both modes and both Messages routes
emit through a single function, so the per-field divergences below are closed
rather than documented. The declared set is `request_duration_ms`,
`generation_duration_ms`, `prompt_tps`, `generation_tps`, `peak_memory_gb`,
`kv_cache_bytes`, `queue_wait_ms`, `draft_acceptance`, `thinking_duration_ms`
and `content_duration_ms` — none required.

**`total_duration_ms` is retired on this wire, not aliased.** It named two
different spans depending on mode, so it was replaced by two fields that each
name one:

| Field | Span | Use it for |
|---|---|---|
| `request_duration_ms` | arrival to done — **includes** queue wait and model load | user-perceived latency |
| `generation_duration_ms` | generation only — **excludes** both | the throughput denominator |

On a server older than 1.79.58 you get `total_duration_ms` instead, and **which
new field it corresponds to depends on the mode**: treat it as
`request_duration_ms` non-streaming and `generation_duration_ms` streaming.
That per-mode split is exactly the ambiguity the rename removed.

Both modes report both. If you divide tokens by a duration, it is
`generation_duration_ms`; `request_duration_ms` is the number that makes a cold
load look like a hang, because it is measuring the load.

**On 1.79.58 exactly, `generation_duration_ms` is not yet that denominator.**
It contained the queue wait its own name excludes: the route's body is a
generator function, so the FIFO gate is acquired on the first `next()` inside
the consume loop — after the span clock has started. A request that queued 30s
and generated 5s reported `35000`, and a client following the rule above
computed a seventh of the true rate. **1.79.59 subtracts the wait
server-side**, clamped at zero. Against a .58 server, net it out yourself
using `queue_wait_ms` — with the caveat immediately below about what that field
means there.

**`/v1/chat/completions` is unchanged and still sends `total_duration_ms`.**
That wire has its own timing model, untouched by 1.79.58, so the retirement is
Messages-only — a client speaking both wires needs both names.

Absent-versus-zero is decided per field, on whether zero is a meaningful
measurement of that quantity:

- **Durations: zero is real.** The builder is handed an explicit integer or
  nothing, so absence is a statement that the span was not measurable.
- **Everything read off the telemetry accumulator — both rates,
  `peak_memory_gb`, `kv_cache_bytes` and `queue_wait_ms`: zero is never
  real**, so it is spelled as absence. A rate of zero would mean no tokens in
  unbounded time, and a wait of exactly `0.0` is not something the gate can
  produce.

**`queue_wait_ms` is in that second group, and 1.79.58 briefly put it in the
first on a premise that measurement refuted.** That release emitted the zero,
reasoning that it rescued a real measurement on an idle server. There is no
such measurement: the wait is an elapsed-counter difference, so an idle gate
yields a tiny nonzero float — live runs reported `0.0044`, `0.0037` and
`0.0024` ms, never `0.0`. What produces exactly `0.0` is the unmeasured set and
only it. **1.79.59 restores the correct rule: absent means not measured, and
`0` never appears.**

`thinking_duration_ms` and `content_duration_ms` remain streaming-only, and
under this rule that stops being an exception: they are spans the non-streaming
path genuinely cannot measure.

**On 1.79.58 exactly, `queue_wait_ms: 0.0` is a non-answer.** That release
emits the field unconditionally, and the gguf provider never assigns it — gguf
bypasses this server's FIFO gate and queues inside `llama-server` at `-np 1`,
so a gguf request that genuinely waited seconds still publishes `0.0`. An MLX
run that yields no chunk loses the tag the same way, since it rides the first
one. So on a .58 server: **on gguf, `queue_wait_ms` is always meaningless**,
and on MLX a `0.0` means the run produced nothing. Treat `0.0` as absent there
and you have the .59 rule early.

### Below 1.79.58 the two modes disagreed, per field

Real, shipped, and live for anyone on an older build — all four are closed
above, and none of them was visible in `/openapi.json`.

- **`total_duration_ms` measured a different span in each mode.**
  Non-streaming started its clock at request arrival, before the provider was
  resolved, so it **included** queue wait and model load; streaming started at
  event-translator construction and **excluded** both. Warm, they nearly
  agreed; on a cold load the same work reported the whole load in one mode and
  none of it in the other, with nothing marking which clock produced a value.
- **`prompt_tps` was `0.0` when unmeasured, non-streaming** — assigned raw
  from a field defaulting to zero and latching only on truthy. **On 1.79.54
  through .57, never read `prompt_tps == 0` as "measured zero" on that path.**
  1.79.54 removed the same trap from the converter beneath it, which is why
  that release looks like it closed this and did not.
- **`generation_tps` was synthesized non-streaming** — run through a helper
  substituting tokens-over-elapsed when the engine reported no rate, while the
  stream dropped it instead. Same name, two guarantees.
- **`queue_wait_ms` was spelled `or None`, which turned out to be correct.**
  It was read here and upstream as hiding a measured zero on an idle server —
  the mirror of the `prompt_tps` trap. Measurement refuted that: an idle gate
  reports a tiny nonzero float, so the dropped zero was never a measurement.
  1.79.58 "fixed" it and 1.79.59 restored it. This entry is kept rather than
  deleted because the reasoning was wrong on both this side and the server's,
  and only a measurement settled it.

Before **1.79.54** the object was also asymmetric in its declared shape: the
two rates were declared **required** while the stream never sent them, so a
strict client generated from `/openapi.json` failed on every `message_stop`;
and `kv_cache_bytes`, `queue_wait_ms` and `draft_acceptance` were sent on the
stream while the model declared none of them, so a generated client dropped
three values per event with no error. Both were possible because the streaming
payload was assembled as a raw dict that nothing checked against the model.
**1.79.55** closed that by filtering the emitted keys to the declared fields;
1.79.58 moved that filter into the shared builder, which is also what makes the
opposite direction — a field declared and emitted by nothing — visible for the
first time.

`thinking_duration_ms` and `content_duration_ms` remain **streaming-only by
design** — the translator times them as it emits, so there is nothing
non-streaming to measure. Their absence there is a contract you may rely on.

**Below 1.79.54 the object is asymmetric in both directions**, and if you
target those builds, both bite. The rates were declared **required** while the
stream never sent them, so a strict deserializer generated from
`/openapi.json` failed on every `message_stop`. And `kv_cache_bytes`,
`queue_wait_ms` and `draft_acceptance` were sent on the stream while the model
declared none of them, so a generated client dropped three telemetry values
per event with **no error anywhere** — the worse direction, because a
declared-but-unsent field at least leaves a dead branch a reader can see.

Both were possible because `MessageStopEvent.performance` is typed
`Optional[PerformanceInfo]` while the streaming payload is assembled as a raw
dict and written straight to the wire, so nothing checked one against the
other. **1.79.55 closes that structurally**: the emitter now filters to the
model's declared fields and logs what it drops, so the payload cannot carry a
key the schema does not declare. For a client that means a new telemetry field
appears in the schema *before* it appears on the wire, never after — so from
.55 the generated document is trustworthy on this path, where before .54 it
was the one place on this wire it was not.

`message_stop.performance` carries the same declared set as the non-streaming
object from 1.79.58 — see the reading rule above. On the stream **absent
telemetry is omitted rather than sent as null**, so test for key presence here
where the non-streaming path wants a `None` check.

Through 1.79.57 this object was keyed on `total_duration_ms` with the
telemetry merged beside it, and `draft_tokens` / `draft_accepted` appeared
alongside `draft_acceptance`; the shared builder emits only the model's
declared fields, so the two raw draft counters are no longer on the wire.

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
| 400 | The loaded model refuses the input: on the MLX path, images to a text-only model or audio to any MLX model (non-streaming only — see in-band errors) | message in `detail` |
| 422 | Body failed validation — an out-of-range sampler value, or a media block carrying neither `source` nor `source_type` | FastAPI validation detail |
| 500 | Model exists but failed to load: corrupt weights, unsupported architecture | message in `detail` |
| 503 | Backpressure — the queue is full, or every loaded model is generating so none can be evicted | `{"error":{"code":"model_overloaded"}}` with `Retry-After` and `X-RateLimit-*`. **No `X-Request-ID` echo** — this is the one response class you cannot correlate by id. `error.message` names the blocking models and what to do (`"cannot make room -- ['<id>'] is generating"`), so show it rather than a generic retry notice |

400 means pick a different model; 500 means that model is broken. The split
is deliberate and worth honouring in client logic — a 400 is recoverable by
falling back to another id, a 500 is not.

## Auth

Both gates are opt-in and off by default; a default localhost deployment is
open.

| Env var | Header | Gates |
|---|---|---|
| `HEYLOOK_API_KEY` | `Authorization: Bearer <key>` | inference: chat completions, messages, embeddings, RLM, hidden states — plus `POST /v1/models/{id}/load` and `DELETE /v1/requests/{id}`, which are gated like inference rather than as admin |
| `HEYLOOK_ADMIN_TOKEN` | `X-Heylook-Admin-Token` | admin routes and `/v1/data/clear` |

Loopback traffic is **exempt from the API-key gate by default**, so it
appears only when the client is on another machine — or when the operator has
set `HEYLOOK_API_KEY_ENFORCE_LOOPBACK=true`. Comparison is constant-time.

The gate is a per-route dependency on the inference routes, not middleware,
so **discovery is never gated**: `/v1/models` and `/v1/capabilities` answer
without a key on a server that has one set. A 401 from either is something
in front of heylook, not heylook.

Send `X-Request-ID` on every request, and make it **unique per request** —
not per session or per client. It is how a request is correlated in the
server's logs, and it is the handle you cancel by, so a reused id is a cancel
that stops every in-flight request sharing it. It is echoed back as a response
header: on the streaming path since 1.79.44, on the non-streaming path only
since 1.79.46 (see below). **Not on a busy 503** — that envelope is built in
one shared place carrying `Retry-After` and the `X-RateLimit-*` pair, and no
echo, on every route that returns it. So the one response class you most want
to correlate in the logs is the one you cannot correlate by id.

## Cancelling a request

```http
DELETE /v1/requests/{request_id}
```

Stops a generation that is still running. **The route is 1.79.44 on both
wires** — nothing could be cancelled by id before it. What 1.79.44 also
changed is that `/v1/messages` began reading a client-supplied
`X-Request-ID`, having always generated its own and ignored the header;
`/v1/chat/completions` already read it for log correlation, so a client on
that wire was probably already sending a usable id.

**The id is the one you sent.** A usable header value is tracked verbatim;
anything missing or malformed gets a server-generated id, which is still fine
for logs and correlation but cannot be cancelled by a client that never chose
it. Usable means `[A-Za-z0-9._:-]`, 1 to 128 characters, matched whole — a
UUID string qualifies. On the non-streaming path you never learn a generated
id in time, so **sending the header is the precondition for being able to
cancel at all**; the response echoes the id actually tracked, so compare it if
a cancel unexpectedly 404s. **That echo reached the non-streaming Messages
response only in 1.79.46** — .44 and .45 returned the body with no
`X-Request-ID` header on that path, so a client there could not tell that its
own id had been rejected and a later DELETE 404'd with nothing to explain why.
The streaming path carried the header from .44.

| Response | Meaning |
|---|---|
| `200 {"cancelled": N, "request_id": "..."}` | N in-flight generations were signalled. A **count, not a boolean**: ids are client-supplied, so two in-flight requests may share one and cancelling it cancels both |
| `404` | Nothing is running under that id, and the id was well-formed. Ids are tracked only while in flight, so the usual cause is that it already finished; the other is that the original request carried no `X-Request-ID` and is tracked under a generated one. Treat it as "too late", not as an error |
| `422` | **The id is malformed and could never have been tracked** (1.79.52). Not the usual "your request was invalid" — the POST end rewrites an unusable `X-Request-ID` to a generated id, so an id failing this check was never registered and never could be. It means *fix your id generator*; retrying cannot help, and no run was stopped. Through 1.79.51 this case answered 404, so a client emitting bad ids saw permanent "too late" and could reasonably conclude cancellation was broken |

**This matters most for non-streaming calls.** A streaming request is already
cancellable by hanging up: the server is writing chunks, so it notices the
peer is gone. A non-streaming one writes nothing until the generation
finishes, so an abandoned client is invisible and the run continues, holding
the GPU and blocking whatever queued behind it. There is deliberately no
disconnect polling — hanging up on a non-streaming request does **not** stop
it. Call DELETE.

**Cancellation is cooperative.** It sets an abort flag the decode loop checks
between tokens, then the run unwinds normally: the generation gate is
released, and a partial run against a conversation persists what it produced.
It is not a kill — a generation blocked inside one long operation, such as
prefill on a large context, stops at the next token boundary rather than
instantly.

**There is no distinct cancellation stop value.** A cancelled run returns a
normal response carrying whatever was generated and reports `stop_reason:
"max_tokens"` (`finish_reason: "length"` on `/v1/chat/completions`) —
Anthropic's vocabulary has no cancellation member, since cancellation there is
a dropped connection rather than an end state. The override applies only when
the provider itself said nothing; a real `length` or `stop_sequence` from the
engine keeps priority. So a cancelled run is indistinguishable on the wire
from budget exhaustion: **track your own cancel, never infer it from the
response.**

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

**`capabilities` could over-report, and 1.79.43 closed the arm that did.**
Until then MLX's `vision` capability was derived from the checkpoint's own
`config.json` while the refusal was decided by the model as loaded, so the two
could disagree: a variant whose entry still declared vision advertised
`vision` and was refused at generation time. Since 1.79.43 the loader router
answers both (`capabilities.py` → `_mlx_serves_vision`, the same answer the
provider's image guard reads), so they cannot diverge on MLX.

Two arms are still open, so handle the refusal regardless. An explicit
`capabilities` list on the model's entry is an **override** that
short-circuits inference entirely (`effective_capabilities`), on either
provider — an operator can assert what the server will not deliver. And gguf
has no guard of its own; see below.

Audio is not one of the open arms. The MLX branch never appends an `audio`
capability — the towers are stripped at load — so gating alone keeps a client
off it, and audio sent to an MLX model anyway is a plain 400 rather than a
broken promise. gguf is where audio is served.

The refusal reaches you as a **400 non-streaming**, or, because the guard
fires at the first token when streaming, as an in-band `error` event typed
`invalid_request_error` (both branches live in the Messages route, not only
the OpenAI one). Gate to decide what to offer; handle both shapes to decide
what actually happened.

**Only MLX has a capability guard.** A gguf entry gets `vision` from an
`mmproj_path` or a declared modality, and the gguf provider forwards
`request.messages` to `llama-server` rather than checking them. The outcome
splits on what that subprocess does. A 400 from it is normalized into the
same refusal the MLX guard raises and arrives in the two shapes above, so
that branch needs no extra client handling. If it accepts the block and
ignores it, nothing refuses: a 200 describing an image the model never used.
Which branch you land on is decided by the model's GGUF/mmproj packaging
rather than by heylook, so test it against the build you are targeting.

`GET /v1/capabilities` returns `server_version`, `optimizations`, Metal
device info, `samplers.available` (the named-bundle roster), an `endpoints`
map and `features`. Query once at integration time for the sampler names.
