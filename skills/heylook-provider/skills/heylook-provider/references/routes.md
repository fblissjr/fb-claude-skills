# Every heylook route

All `/v1` operations, grouped by who calls them. An inference integration
needs only the first group; the rest is here so a client knows what exists.
Request and response shapes are in the running server's `/openapi.json`;
heylook's own behaviour spec for each group is `docs/frontend_v3_spec.md` §4
in the heylook repo. "Admin" means the `X-Heylook-Admin-Token` gate, a no-op
when the server sets no `HEYLOOK_ADMIN_TOKEN`; every other route is open.
Every route is behind the Host check (`wire_reference.md`, Access).

Read from heylook's `docs/api_integration.md` §9 and checked against the
generated OpenAPI document at the version in SKILL.md's frontmatter: the
tables below cover every operation it lists.

## Inference

| Route | Purpose |
|---|---|
| `POST /v1/messages` | The inference wire (`wire_reference.md`) |
| `GET /v1/models` | Served models, capabilities, the `engine` object |
| `GET /v1/capabilities` | Server version, optimizations, Metal info |
| `POST /v1/models/{id}/load[?warm=true]` | Pay a model load up front |
| `POST /v1/models/{id}/image-plan` | Tokens and resize target per image size; resident models only (409 otherwise) |
| `DELETE /v1/requests/{request_id}` | Cancel by `X-Request-ID` |

## Conversation store

A server-side alternative to keeping history in the client: the server stores
messages and media (DuckDB) and builds each request from them. heylook's own
chat page uses it.

| Route | Purpose |
|---|---|
| `GET/POST /v1/conversations` | List; create (201) from `{title, model_id?, system_prompt?, params?, applied_preset_id?}` |
| `GET/PUT/DELETE /v1/conversations/{id}` | Read with messages; patch metadata; delete (media included) |
| `POST /v1/conversations/{id}/clone` | Copy a conversation, media included |
| `POST /v1/conversations/{id}/messages` | Append a message `{role, content, thinking?}` |
| `DELETE /v1/conversations/{id}/messages?after={pos}` | Truncate: delete every message after a position |
| `PUT/DELETE /v1/conversations/{id}/messages/{msg_id}` | Edit or delete one message |
| `POST /v1/conversations/{id}/generate` | Generate into the conversation |
| `DELETE /v1/conversations/{id}/generate` | Stop the active generation; the partial persists. 404 when none is active |
| `POST /v1/conversations/{id}/prompt` | The exact prompt string generate would feed the model; persists nothing |
| `GET /v1/conversations/{id}/media/{media_id}` | A stored image or audio blob |

**What differs from `/v1/messages`:**

- **The server builds the request.** `generate` takes
  `{mode: "append"|"regenerate"|"continue", message_id?, user_content?,
  overrides?, stop_sequences?}` and reads the conversation's `system_prompt`,
  `params`, `model_id` and rows. `append` stores `user_content` as a new user
  turn first; `regenerate` replaces everything from the `message_id` anchor;
  `continue` extends the anchor row. `overrides` layers one-shot sampler
  values (and `model`) over the stored `params`.
- **`params` and `overrides` use the store's key names, not the wire's.**
  The thinking switch is `enable_thinking` and the budget is
  `thinking_budget_tokens`; `reasoning_effort` and the sampler fields keep
  their `/v1/messages` names. Any other key is **dropped silently**, so
  `{"thinking": false}` in `overrides` leaves thinking at the model's
  default.
- **One extra event, always last.** The stream is the `/v1/messages` grammar
  plus `event: heylook_saved`, carrying `end_reason`
  (`complete`, `aborted` or `error`), the full stored rows in `messages`,
  `dropped_media` and `timing` (the same object as `message_stop.performance`).
  Set client state from `messages`, not by counting positions.
- **An `error` event does not end the saga.** It may precede `heylook_saved`,
  and a partial reply still persists. On `/v1/messages` an error event ends
  the stream.
- **Persistence is server-owned.** Completion, abort and client disconnect
  all persist; an error before any output persists nothing. A regenerate or
  continue that fails leaves the thread untouched.
- **One generation per conversation.** A second `generate` is a 409
  `{"error":{"code":"generation_in_progress"}}`. A message write or a
  conversation delete while one runs is also a 409, with a plain `detail`
  body and no code, so key on the status. Metadata `PUT`s stay open.
- **Unknown fields are ignored, not refused.** Unlike `/v1/messages`, this
  route has no 422 for retired fields.
- **Stored media comes back by reference.** Send base64 as usual; the stored
  block becomes `{"type": "image", "source": {"type": "url", "url":
  "/v1/conversations/{id}/media/{media_id}", "media_type", "media_id"}}`, and
  the bytes are served from that URL with `Cache-Control: immutable`. Media
  the target model cannot take is dropped from the request and counted in
  `dropped_media`.
- **Messages carry both `content` and `content_blocks`**: the flattened text,
  and the full stored block list. `PUT /v1/conversations/{id}` returns the
  conversation **without** its messages.
- **A stored thinking depth the model does not offer is dropped**, and the
  model runs at its default; `/v1/messages` answers 400 instead.
- **`prompt`** takes the same body as `generate` plus `edits`, and returns
  `{prompt, model_id, provider, mode, continuation, dropped_media,
  unrendered_media, char_count, markers}`, rendered by the model's own
  template. 409 when the model is not resident: a preview never loads one.
  On MLX images in history are not rendered into it.

## Notebooks and presets

| Route | Purpose |
|---|---|
| `GET/POST /v1/notebooks` | List (content omitted); create |
| `GET/PUT/DELETE /v1/notebooks/{id}` | Read, patch, delete a plain-text notebook |
| `GET/POST /v1/presets` | List `{presets, total}`; create (201; duplicate name 409, blank 400) |
| `PUT/DELETE /v1/presets/{id}` | Patch, delete |

A preset is a named bundle of `system_prompt` and sampler `params`. The
**client** expands it: copy `system_prompt` into the request and `params` into
the sampler fields. `params` uses the store's key names, so rename on the way
to `/v1/messages`: `enable_thinking` becomes `thinking`, and
`thinking_budget_tokens` becomes `thinking: {"budget_tokens": N}`. Sent
unrenamed, `enable_thinking` is a 422 there. The server never applies a preset to a request, and
`preset` on `/v1/messages` is a 422. A preset stores only the fields it pins,
so absent fields still fall to the server cascade.

## Model administration (admin)

| Route | Purpose |
|---|---|
| `GET/POST /v1/admin/models`, `GET/PATCH/DELETE /v1/admin/models/{id}` | Per-model config in `heylook.toml`; PATCH reports which fields need a reload |
| `POST /v1/admin/models/validate` | Validate a config without saving |
| `GET /v1/admin/model-options` | Every settable field per provider, and when a change takes effect |
| `GET/PUT /v1/admin/models/scan-config` | The folders models are discovered from |
| `POST /v1/admin/models/{id}/fit` | Whether it fits memory, with optional candidate edits |
| `GET /v1/admin/models/{id}/status` | Loaded state, memory, context use, requests active and queued |
| `POST /v1/admin/models/{id}/unload` | Unload (409 while it is generating) |
| `POST /v1/admin/models/{id}/reload` | Unload, then load and warm, as one operation |
| `GET/PUT/DELETE /v1/admin/models/{id}/chat-template` | Read, override or reset the chat template in force |
| `GET/PUT /v1/admin/config`, `DELETE /v1/admin/config/{key}` | Server operational settings |
| `POST /v1/admin/reload` | Re-read config and clear loaded models without a restart |

## Maintenance and observability

| Route | Purpose |
|---|---|
| `POST /v1/cache/clear` (admin) | Clear prompt and vision caches for one model or all |
| `POST /v1/data/clear` (admin) | Delete every conversation, message and notebook. Presets survive |
| `GET /v1/system/metrics` | RAM, loaded models, per-model memory; unknown readings are null |
| `GET /v1/performance/profile/{1h\|6h\|24h\|7d}` | Aggregated timing by phase |
| `POST /v1/telemetry/events` | heylook's own frontend events; not for integrations |
