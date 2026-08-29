# Adding heylook beside a Gemini integration

For an app whose provider layer already speaks the Gemini
`generateContent` / `streamGenerateContent` API and is gaining heylook as a
second backend.

## Field mapping

| Gemini | heylook `/v1/messages` |
|---|---|
| `systemInstruction.parts[].text` | `system` (top-level string) |
| `contents[]` | `messages[]` |
| `contents[].role: "user"` | `role: "user"` |
| `contents[].role: "model"` | `role: "assistant"` |
| `parts[].text` | `{ "type": "text", "text": ... }` |
| `parts[].inlineData { mimeType, data }` | `{ "type": "image", "source": { "type": "base64", "media_type": ..., "data": ... } }` |
| `parts[].fileData { fileUri }` | `{ "type": "image", "source": { "type": "url", "url": ... } }` |
| `generationConfig.maxOutputTokens` | `max_tokens` |
| `generationConfig.temperature` | `temperature` |
| `generationConfig.topP` / `topK` | `top_p` / `top_k` |
| `generationConfig.seed` | `seed` |
| `generationConfig.stopSequences` | no equivalent; stop tokens are resolved from the model |
| `generationConfig.responseSchema` | no equivalent; prompt for the shape |
| `generationConfig.thinkingConfig` | `thinking` plus `reasoning_effort` |
| `candidates[].content.parts[].text` | a `text` output block |
| `candidates[].finishReason` | `stop_reason` (`end_turn` / `max_tokens` / `stop_sequence`) |
| `usageMetadata.promptTokenCount` | `usage.input_tokens` |
| `usageMetadata.candidatesTokenCount` | `usage.output_tokens` |
| streaming chunk `candidates[].content.parts[].text` | `content_block_delta` → `delta.text` |

Both `inlineData.data` and heylook's `data` are **raw base64 without a
`data:` prefix**, so that field ports across unchanged. The surrounding block
shape does not.

## Structural mismatches worth planning around

**Model ids are install-local.** Gemini ids are global constants you can
ship in a config file. heylook's registry is override-only — a model under a
scanned folder is served with derived defaults — so its roster reflects
whatever the operator has downloaded. Resolve from `/v1/models` at runtime
and select by capability. A provider abstraction that treats "model name" as
a static enum needs a discovery seam before heylook fits it.

**Capabilities are per-model, not per-provider.** With Gemini you can assume
vision. With heylook, one served model does vision, another is text-only,
and only gguf models take audio. Read `capabilities` on each `/v1/models`
row and gate the features you expose — then handle the refusal anyway, because
`capabilities` can over-report (`references/wire_reference.md`, discovery
endpoints). Gemini has no equivalent of a model that advertises a modality and
then declines it.

**Message roles are validated by the model's own chat template, not by the
server.** Gemini enforces strict `user`/`model` alternation itself. heylook
passes messages through to whichever template the checkpoint ships, and
templates disagree: some reject a system message appearing mid-conversation,
some reject two leading system messages, and a raised jinja exception on the
gguf path surfaces as a 500. Keep to one leading system prompt via the
top-level `system` field, then strict alternation. Do not assume a shape
works because it worked on another model.

**Reasoning is a separate block, not concatenated parts.** Gemini returns
one candidate whose parts you join. heylook returns typed blocks where
`thinking` and `text` are distinct. Joining everything puts the model's
reasoning into your product's output.

**There is no `responseSchema`.** Gemini's structured-output constraint has
no heylook equivalent. Ask for the format in the prompt and parse
defensively, or use `logprobs` if you need confidence signals.

**Latency has a different first-request shape.** Gemini is a warm hosted
endpoint. heylook loads nothing at startup and keeps one model resident by
default, so the first request to a model pays its load, and alternating
between two models can reload on every call. Pre-warm with `POST
/v1/admin/models/{id}/load?warm=true`, and batch work by model.

**Backpressure is real and normal.** Gemini answers 429 under quota.
heylook answers 503 with `Retry-After` because it serialises generation for
a single user. Treat it as a queue, not a quota — retry rather than degrade.

## Provider-abstraction seams this implies

If the app's provider interface was shaped around Gemini, four seams usually
need to exist before heylook fits cleanly:

1. **Model discovery** — a call that lists models and their capabilities,
   rather than a static enum.
2. **Capability gating** — feature flags derived per model, not per provider.
3. **Reasoning channel** — somewhere for `thinking` content to go that is not
   the answer.
4. **Retry on backpressure** — a 503-with-`Retry-After` path distinct from a
   hard failure.

All four are things heylook makes visible rather than things it invents;
they exist against hosted providers too, just less often.

## Keeping images working across both

Gemini accepts large `inlineData` and does its own downscaling.
`/v1/messages` does not resize at all, so a payload that was fine for Gemini
arrives at a local vision tower at full resolution and is paid for in vision
tokens and prefill. Resize in the shared path before the provider split, and
send `vision_tokens` to heylook to cap the budget directly. Recipes are in
`client_recipes.md`.
