# Older heylook servers

SKILL.md states current behaviour, as of the version in its frontmatter. This
file holds every version boundary it no longer carries inline. Read
`server_version` from `/v1/capabilities`, then read only the entries at or
above that version. A client that must support a range of servers handles
every arm the range spans.

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
  makes it a 422 naming the missing field. Against older servers no status
  code reveals it, so if a vision answer describes nothing, check the block's
  payload.

## Capability gating

- **Before 1.79.43** MLX's `vision` capability came from the checkpoint's own
  `config.json` while the refusal came from the model as loaded, so a
  hand-made variant whose directory still declared vision advertised `vision`
  and was then refused. Since 1.79.43 one resolver answers both.

## Removed fields that were dropped silently

- **1.79.66** removed `/v1/chat/completions` and
  `/v1/batch/chat/completions` (see `openai_wire.md`). From 1.79.66 the
  `preset` rename guard was unreachable in the same way as the `logprobs`
  refusal below.
- **1.79.74** removed `logprobs`, `top_logprobs` and the `heylook_logprobs`
  SSE event. The 422 naming the removal is only reachable **from 1.79.79**.
  Through 1.79.78 it was declared on an internal model no route binds, and
  pydantic ignores an undeclared field, so on 1.79.74-1.79.78 the key is
  dropped in silence and the request answers 200.
- **`include_performance`** existed through 1.79.48, controlled nothing, and
  was removed in 1.79.49.

## Cancellation and request ids

- **Before 1.79.44** there is no `DELETE /v1/requests/{request_id}`, and
  `/v1/messages` ignored `X-Request-ID` and generated its own.

## Model load route

- **Before 1.79.48** the load route was `/v1/admin/models/{id}/load` behind
  the admin token. It moved to `/v1/models/{id}/load`, gated like inference;
  a move, not an alias, so the admin URL answers 405 on newer servers.
- **Through 1.79.52** the load route had no backpressure branch: busy fell
  through to a generic handler and came back as a **500 carrying the
  identical sentence**, so status alone could not separate transient busy
  from a broken model. Against those builds, key on the `MODEL_BUSY` token in
  `detail`; that is the correct reading for an older server, not a
  workaround. From 1.79.53 busy is a 503 with `Retry-After` and the
  `model_overloaded` envelope.

## Telemetry

- **Before 1.79.54** fields inside `performance` were not all optional.
- **Through 1.79.57** streaming and non-streaming disagreed per field; most
  sharply, non-streaming `prompt_tps` was `0.0` when unmeasured, so never
  read it as a measured zero on those builds. Per-field detail:
  `wire_reference.md`, "Below 1.79.58 the two modes disagreed, per field".
- **On 1.79.58** `generation_duration_ms` still contains the queue wait; net
  it out yourself. From 1.79.59 it excludes queue wait and model load.
