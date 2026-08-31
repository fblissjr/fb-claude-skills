# `/v1/chat/completions` — the OpenAI wire

heylook's OpenAI-compatible endpoint. Kept for external consumers and
existing SDK clients; heylook's own frontend does not call it. Fully
supported, not deprecated.

## When this wire is the better choice

- **You want server-side image downscaling.** `/v1/messages` has no resize
  params at all, so the client does that work; here it is a request field.
- **You need `continue_final_message`.** A `ChatRequest` field with no
  Messages-wire equivalent, so prefill and "keep going" only work here. Read
  the traps below first — it is narrower than it looks.
- **You have a working OpenAI SDK client.** Changing `base_url` is cheaper
  than rewriting a request builder.
- **You are fronting heylook with something that speaks OpenAI** — a proxy, a
  gateway, an agent framework with an OpenAI adapter.

Otherwise prefer `/v1/messages`; see the parent SKILL.md.

## Using an OpenAI SDK unmodified

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
resp = client.chat.completions.create(
    model=model_id,                     # resolved from /v1/models
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=512,
)
```

`api_key` is required by the SDK and ignored by the server unless
`HEYLOOK_API_KEY` is set. When it is set, pass the real key there.

## Differences from `/v1/messages`

| | `/v1/chat/completions` | `/v1/messages` |
|---|---|---|
| System prompt | `{"role":"system"}` in `messages` | top-level `system` |
| Image part | `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}` | `{"type":"image","source":{"type":"base64",...}}` |
| Image data | `data:` URI | raw base64, no prefix |
| Thinking flag | `enable_thinking` | `thinking` |
| Server-side resize | yes | no |
| Performance block | opt in with `include_performance` | unconditional; no such field since 1.79.49 |
| Response | `choices[0].message.content` (string) | `content` (typed block list) |
| Reasoning | `choices[0].message.thinking` | a `thinking` block |
| Stop field | `finish_reason`: `stop` / `length` | `stop_reason`: `end_turn` / `max_tokens` |
| Cancel handle | `X-Request-ID`, read here before 1.79.44 | `X-Request-ID`, read as of 1.79.44 |
| Stream terminator | `data: [DONE]` | `message_stop`, no sentinel |
| Usage in stream | final chunk, needs `stream_options.include_usage` | `message_delta` |

Sampler knobs are the same names with the same bounds on both wires, and
absent still means the server cascade decides.

## Server-side image resize

Only on this wire:

| Param | Effect |
|---|---|
| `resize_max` | cap the longest edge, in pixels |
| `resize_width` / `resize_height` | explicit target dimensions |
| `image_quality` | JPEG quality for the re-encode |
| `preserve_alpha` | keep transparency rather than flattening |

```json
{
  "model": "a model whose capabilities include vision",
  "messages": [{ "role": "user", "content": [
    { "type": "text", "text": "What is in this image?" },
    { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,..." } }
  ]}],
  "resize_max": 1024,
  "max_tokens": 512
}
```

These downscale before the model sees the image, which cuts prefill cost as
well as upload size. `vision_tokens` works here too and caps the visual token
budget directly — the two are complementary, not alternatives.

## Streaming

```
data: {"choices":[{"delta":{"content":"..."}}]}
data: {"choices":[{"delta":{"thinking":"..."}}]}
data: {"choices":[{"logprobs":{"content":[...]}}]}
data: {"usage":{...},"timing":{...},"stop_reason":"stop"}
data: [DONE]
```

The usage chunk appears only with `stream_options: {"include_usage": true}`.
Its `timing` object carries the same telemetry vocabulary as the Messages
wire's `message_stop.performance`.

`delta.thinking` is a separate field from `delta.content` — an OpenAI client
that reads only `content` will silently drop reasoning, which is usually what
you want.

## Cancelling

`DELETE /v1/requests/{request_id}` works identically on this wire — the id is
the `X-Request-ID` you sent. **The endpoint is 1.79.44 on both wires**; what
predates it here is only the header read, which this route already did for log
correlation while `/v1/messages` ignored it and generated its own. So an
existing OpenAI-wire client is likely already sending a usable id, and 1.79.44
is what made it cancellable. Everything else is the same: non-streaming is
where it matters, cancellation is cooperative, and a `404` means the run
already finished. Detail in `wire_reference.md`.

One consequence lands here: **`finish_reason: "length"` is overloaded.** A
cancelled run reports it, so on this wire it means either the token budget was
reached or someone cancelled — there is no third value that separates them.
Track your own cancel rather than reading it off the response. Full account in
`wire_reference.md`.

## Errors

Identical taxonomy to `/v1/messages`: 400 for model routing, 500 for a failed
load, 503 with `Retry-After` for backpressure, and a mid-stream failure
arriving in-band after the 200 has flushed. On this wire the in-band form is:

```
data: {"error":{"message":"...","type":"server_error","code":"generation_failed"}}
data: [DONE]
```

Never render `error.message` as assistant content.

## Two traps specific to this wire

**`processing_mode` switches the response schema.** Setting it to anything
other than `"conversation"` returns a `chat.completion.batch` object rather
than a `chat.completion`. Leave it unset.

**`continue_final_message` continues rather than opens a turn.** Absent means
auto: a trailing assistant message is continued. `true` continues whatever
the final message is, and user-role continuation is MLX-only — gguf answers
400. `false` never continues. Not supported alongside image history. Only
relevant if you are building a prefill or "keep going" feature.

## Batch

`POST /v1/batch/chat/completions` takes `{"requests": [ChatRequest, ...]}`
with at least two entries. Every `requests[].model` must be identical and
none may set `stream`; either violation is a 400. Returns
`{"data": [ChatCompletionResponse], "batch_stats": {...}}`.

Useful when generating many independent outputs against one model, since it
avoids per-request queue round-trips against a server that serialises
generation anyway.
