# Porting off `/v1/chat/completions` (removed in heylook 1.79.66)

heylook no longer serves an OpenAI-compatible route. `POST /v1/chat/completions`
and `POST /v1/batch/chat/completions` were removed in 1.79.66, together with
their SSE grammar (`choices[].delta` chunks, the `data: [DONE]` sentinel, the
`: keepalive` comment) and the batch processing modes. Nothing the project
cares about spoke them (heylook's own frontend had not since 1.74.0), so the
route was a second wire to keep conformant for nobody. `/v1/messages` is the
inference API, and `GET /v1/models` keeps its OpenAI-shaped list envelope
because that is what discovery clients read.

## How you notice

A request to either removed path is a plain **404** (FastAPI's
`{"detail":"Not Found"}`), which an OpenAI SDK surfaces as a not-found error
on the very first call. Nothing else about the server changed for that client:
`/v1/models` still lists what is served, `/v1/capabilities` still names the
version. Read `server_version` there if you must support servers on both sides
of 1.79.66.

## The SDK swap

The Anthropic SDKs reach `/v1/messages` with `base_url` set to the server's
**origin**; the SDK appends `/v1/messages` itself. (The OpenAI SDK wanted
`.../v1` as its base. Carrying that habit over produces `/v1/v1/messages`,
another 404.)

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://localhost:8000", api_key="not-needed")
resp = client.messages.create(
    model=model_id,                     # resolved from /v1/models
    max_tokens=512,                     # optional here; see SKILL.md
    messages=[{"role": "user", "content": "Hello"}],
)
```

`api_key` is required by the SDK and ignored by the server unless
`HEYLOOK_API_KEY` is set; when it is set, pass the real key.

## Field mapping

| You sent (OpenAI route) | Send now (`/v1/messages`) |
|---|---|
| `{"role":"system"}` in `messages` | top-level `system` string |
| `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}` | `{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":"..."}}` |
| `data:` URI | raw base64, no prefix |
| `{"type":"input_audio","input_audio":{"data":...,"format":...}}` (gguf only) | `{"type":"audio","source":{"type":"base64","media_type":...,"data":...}}` (still gguf only) |
| `enable_thinking` | `thinking` (a bool, same meaning) |
| `stream_options.include_usage` | nothing; `usage` rides `message_delta`, telemetry rides `message_stop.performance` unconditionally |
| `include_performance` | nothing; telemetry is unconditional (never a field on this wire since 1.79.49) |
| `X-Request-ID` | unchanged, same cancellation endpoint |

Sampler knobs (`temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`,
`repetition_context_size`, `presence_penalty`, `seed`, `sampler`,
`vision_tokens`, `reasoning_effort`, `logprobs`, `top_logprobs`) keep their
names and bounds, and absent still means the server cascade decides.

| You read (OpenAI route) | Read now (`/v1/messages`) |
|---|---|
| `choices[0].message.content` (string) | `content`: a typed block list; join the `text` blocks only |
| `choices[0].message.thinking` | a `thinking` block (text under `thinking`, also `text`) |
| `finish_reason`: `stop` / `length` | `stop_reason`: `end_turn` / `max_tokens` |
| stream `delta.content` / `delta.thinking` | `content_block_delta` with `delta.type` `text_delta` / `thinking_delta` |
| stream `logprobs.content` entries | `event: heylook_logprobs`, same entry shape |
| final usage chunk `timing.total_duration_ms` | `performance.request_duration_ms` (whole-request elapsed; the throughput denominator is `generation_duration_ms`) |
| `data: [DONE]` | `message_stop` ends the stream; there is no sentinel |
| `data: {"error":{...}}` then `[DONE]` | `event: error` with `error.type` `invalid_request_error` (your 400 path) or `api_error` (your 500 path); it ends the stream |

`finish_reason: "length"` was overloaded on the old route (budget reached OR
cancelled), and `stop_reason: "max_tokens"` carries the same two meanings
here. Track your own cancel; never infer it from the response.

## What has no replacement

- **Server-side image downscaling.** `resize_max`, `resize_width`,
  `resize_height`, `image_quality` and `preserve_alpha` existed only on the
  removed route. Resize before sending: longest edge around 2048px, photos as
  JPEG at about 0.85 quality, PNG kept as PNG, EXIF orientation honoured.
  Recipes for Node and Python are in `client_recipes.md`. `vision_tokens`
  still caps the model-side cost directly and is the more direct lever.
- **The batch endpoint and `processing_mode`.** Loop your requests. The
  server serialises generation through one FIFO gate, so a batch bought no
  parallelism; it only saved HTTP round trips on a local socket.
- **`continue_final_message`.** The explicit flag was a field of the removed
  route's request. On `/v1/messages` the convention still holds: a trailing
  assistant message is continued rather than answered, and a trailing
  assistant message carrying a `thinking` block and no text resumes inside
  that thought (1.79.63). What is gone is forcing the flag against the
  convention (user-role continuation, or `false` to open a fresh turn on a
  trailing assistant message).

## Cancelling

Unchanged. `DELETE /v1/requests/{request_id}` stops a running generation,
addressed by the `X-Request-ID` you sent; send a fresh one per request. The
old route read the header for log correlation long before cancellation
existed, so a ported client is probably already sending a usable id. Detail in
`wire_reference.md`.
