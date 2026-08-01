last updated: 2026-08-01

# gemini-bridge: design notes

> Status: **shipped** as `apps/gemini-bridge` (0.3.0). This began as a design
> note written before any code existed, and the design sections are preserved
> as written — including the parts later disproved, because *how* they were
> wrong is the useful part. Anything a live probe contradicted is marked in
> place rather than quietly corrected.
>
> The operating lesson: **form hypotheses from docs and the SDK, confirm
> anything load-bearing with a real call.** Every static source turned out to be
> wrong about something material. Re-run `internal/scratch/gemini_probe.py`
> before exposing any new API parameter.

## What this is

A plugin that lets Claude Code hand a specific multimodal task to a Gemini
model and get a structured answer back, without the user copy-pasting between
two chat windows.

Not a general Gemini integration. Not an agent. A bridge for the cases where
Claude cannot do the work at all.

## The two motivating cases

**Perceptual comparison.** Comparing renders of the same 3D scene, Claude could
not see the difference between two frames. It fell back to measuring pixels
with numpy and reporting statistics. Handing the same images to Gemini with a
question Claude composed worked immediately. The manual round-trip was the
only friction.

That failure has a recognizable signature worth encoding as a trigger: *pixel
math standing in for looking at the thing.*

**Video to code.** Turning a screen recording into working HTML/JS needs a model
that understands motion, timing, and the audio track together. Claude cannot
watch the video.

Both are capability gaps, not cost decisions. That distinction matters for how
this relates to `model-routing` (see below).

## Verified API facts

Everything here was checked against primary sources during the design session.
Sources disagree with each other, so the provenance matters.

### Source hierarchy: only the live API is authoritative

A probe run on 2026-08-01 (`internal/scratch/gemini_probe.py`) disproved the
hierarchy this document previously asserted. **Every static source is wrong
about something**, including the generated SDK, which had been treated as
highest authority:

| Source | Wrong about |
|---|---|
| OpenAPI spec | omits video input entirely; dangling `SafetySetting` ref |
| Generated SDK | omits `temperature`, which the API *accepts*; ships a `delete` the server does not implement |
| Doc pages | claim `temperature` works (it is ignored); claim `delete` works (501); three mutually contradictory video token rates |

Use static sources to form hypotheses. **Confirm anything load-bearing with a
live call.** The probe script is cheap to extend and should be re-run whenever a
new parameter is about to be exposed.

Ordering among static sources, for hypothesis-forming only:
**Generated SDK types > `.md.txt` doc pages > OpenAPI spec.** Established by two
concrete conflicts:

- The OpenAPI spec (`interactions-v1.openapi.json`) defines `Content` as a
  `oneOf` over Audio, Document, Image, Text. **No video.** The SDK has
  `VideoContent`, and the docs show video input working. The spec is stale.
- The spec has a dangling `$ref`: `safety_settings` points at `SafetySetting`,
  which is never defined. Explained by the overview's Limitations section —
  custom safety settings are not supported on this API at all.

Do **not** build a drift check that validates CLI flags against the OpenAPI
spec. It would fail video input as invalid. That idea was proposed and killed
during the session.

The SDK is vendored at `coderef/python-genai` (v2.16.0). The Interactions
surface is generated code under `google/genai/_gaos/`; `client.interactions`
resolves to `GeminiNextGenInteractions`. `google/genai/interactions.py` is only
param TypedDicts — the real implementation is in `_gaos`.

`coderef/gemini-skills` is Google's own skill library. It is a **source, not a
deliverable** — four dev-time SKILL.md files totalling ~62KB that teach an agent
to write `google-genai` code. It contains no multimodal examples at all. Its
lasting value is the doc-URL index and a handful of gotchas.

### Call shape

```python
from google import genai
client = genai.Client()
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=[{"type": "video", "uri": myfile.uri, "mime_type": myfile.mime_type},
           {"type": "text", "text": "..."}],
    system_instruction="...",
    response_format={"type": "text", "mime_type": "application/json",
                     "schema": SomeModel.model_json_schema()},
)
print(interaction.output_text)
```

Not `client.models.interactions.create()`. Not `user_input=`. `output_text` is a
convenience property; the raw timeline is `interaction.steps`.

### GenerationConfig — complete

From the generated SDK, which is authoritative:

```
image_config · max_output_tokens · seed · speech_config · stop_sequences
thinking_level · thinking_summaries · tool_choice · transcription_config · video_config
```

**`temperature` is accepted and silently ignored — the worst of both.** Probed
directly: a request carrying `temperature` returns 200, so nothing surfaces an
error. But at `temperature: 0.0` four samples of "name one animal" returned
three *different* answers, and `temperature: 2.0` returned the identical answer
set. A honored temperature of 0.0 would return one value. It does nothing.

**Never expose `--temperature`.** A flag that is accepted, does nothing, and
reports no error is worse than one that 400s, because the user believes it
worked.

`seed` **is** honored — probed twice with the same seed and prompt, identical
output both times. That is the determinism knob, and it suits reproducible
render comparison better anyway.

`thinking_level`: `minimal | low | medium | high`.

`image_config` is marked **deprecated** in the generated code even though it is
current. So is `response_mime_type` (which the same file says is "required if
response_format is set" — an inconsistency in Google's generated docstrings, not
something to build against).

### transcription_config — the audio recipe's real surface

Verified against the generated types. This was undocumented in every guide read,
and it is exactly what the audio work needs:

| Field | Notes |
|---|---|
| `custom_vocabulary` | list of phrases to bias recognition toward specific terms |
| `diarization_mode` | speaker diarization; supported value `"speaker"` |
| `language_codes` | BCP-47 hints; omit for auto-detection |
| `timestamp_granularities` | supported value `"word"`; empty means no timestamps |
| `adaptation_phrases` | **deprecated** — use `custom_vocabulary` |

Word-level timestamps plus speaker diarization, both configurable per call.

### video_config is generation-only — not for understanding

Its single field is `task`, a union of `text_to_video | image_to_video |
reference_to_video | edit`. That is the Omni Flash generation path. **It has
nothing to do with video understanding** and is irrelevant to v0.1.

### service_tier is real, and it is where Flex lives

`ServiceTier = "flex" | "standard" | "priority"`, a **top-level field on the
create request**, not inside `GenerationConfig`:

```python
client.interactions.create(..., service_tier="flex")
```

Confirmed present on both `CreateModelInteraction` and `CreateAgentInteraction`,
and echoed on the response. Both `interactions/flex-inference` and
`interactions/priority-inference` open with "This version of the page covers the
new Interactions API," and neither appears in the not-available list. So Flex is
available on the Interactions API even though Batch is not.

Priority has a catch worth knowing before exposing it: its default rate limit is
**0.3x** the standard limit for the model, and on overflow it degrades gracefully
to standard billing rather than failing.

### Field placement gotcha

Only the ten fields listed above live inside `generation_config`. These are all
**top level** on the create request: `service_tier`, `labels`, `stream`, `store`,
`background`, `previous_interaction_id`, `system_instruction`, `tools`,
`response_modalities`, `response_format`, `environment`, `webhook_config`,
`safety_settings`. Treating "the knobs" as one bag will produce 400s.

(Note `safety_settings` is present in the SDK type despite the docs listing
custom safety settings as unsupported. Do not rely on it. `webhook_config` is
undocumented in everything read so far.)

### Content types and media resolution

`VideoContent` is `data | mime_type | resolution | type | uri`. **No fps, no
start_offset, no end_offset.** Confirmed against the generated SDK types, not
just the docs. Accepted mime types: `video/mp4`, `video/mpeg`, `video/mpg`,
`video/mov`, `video/avi`, `video/x-flv`, `video/webm`, `video/wmv`,
`video/3gpp`. The overview's Limitations section confirms:
`video_metadata` (clipping intervals, custom frame rates) is not available on
the Interactions API. Sampling is fixed at 1 FPS.

Consequence: **trimming and retiming are ours, via ffmpeg.** Google's own
`gemini-omni-flash-api` skill ships `scripts/video/prep_video.py` for exactly
this; that is a reasonable shape to copy.

`resolution` is **per content item** (Gemini 3 only), enum
`low | medium | high | ultra_high`. You can mix within one request.

| Media | Setting | Tokens | When |
|---|---|---|---|
| Image | `high` (= default) | 1120 | most image analysis |
| Image | `low` / `medium` | 280 / 560 | context images that aren't the subject |
| Image | `ultra_high` | 2240 | computer use only |
| Video | default / `low` / `medium` | **70/frame, all identical** | motion, action, scene description |
| Video | `high` | 280/frame | only when reading text or fine detail in frames |
| PDF | `medium` | 560 | quality saturates here |

The non-obvious part: for video there is no cheap tier. `low` and `medium` are
treated the same as the default. The only decision is 70 vs 280, a flat 4x, paid
only for in-frame text.

### Token counting — measure, never compute

**Three** doc pages give three different answers, and the conflict is genuinely
unresolved — none of them cross-references the others:

| Page | Claim |
|---|---|
| `tokens` | "Video: 263 tokens per second", with a worked example: "A 60-second video is approximately 263 * 60 = 15,780 tokens" |
| `media-resolution` | 70 tokens/frame at default/low/medium, 280 at high (Gemini 3 scoped) |
| `interactions/video-understanding` | 66 tokens/frame at low, 258 otherwise; "approximately 300 tokens per second at default media resolution, or 100 at low" |

The tempting resolution — that `tokens` and `video-understanding` describe older
models and `media-resolution` supersedes them for Gemini 3 — **does not hold**:
the `tokens` page's own worked example targets `gemini-3.6-flash`. Two pages
describe the same Gemini 3 `media_resolution` parameter and disagree by roughly
4x.

Treat all three as unreliable.

So the CLI must not estimate from a formula:

- **Dry run**: `client.models.count_tokens(model=..., contents=[...])`
- **Actuals**: `interaction.usage` — `total_input_tokens`, `total_output_tokens`,
  `total_thought_tokens`, `total_cached_tokens`, `total_tool_use_tokens`,
  `total_tokens`

Gotcha: `count_tokens` lives on `client.models` and takes `contents=[...]`, while
the real call is `client.interactions.create(input=[...])`. Two different
payload shapes for the same attachments. A test should assert they describe the
same media, or the dry-run estimate will silently drift from what is sent.

**Probed: for text, they agree exactly** (`count_tokens=7`, `usage_input=7`).
The image and video cases are still unverified.

### `usage` carries a per-modality breakdown

Undocumented in everything read, and exactly what cost attribution needs:

```json
{"input_tokens_by_modality": [{"modality": "text", "tokens": 17}],
 "total_input_tokens": 17, "total_output_tokens": 3,
 "total_thought_tokens": 195, "total_cached_tokens": 0,
 "total_tool_use_tokens": 0, "total_tokens": 215}
```

So a video call reports how many tokens the video contributed versus the prompt.
Write the whole object to `usage.json` verbatim.

### Thinking is ON by default, and it dominates cost

Probed on "what is 17 * 23":

| thinking_level | input | output | **thought** | total |
|---|---|---|---|---|
| `high` | 17 | 3 | **195** | 215 |
| `minimal` | 17 | 3 | **0** | 20 |

Thought tokens bill at the **output** rate ($7.50/1M for 3.6 Flash), so a
trivial question cost 65x more output tokens at `high` than at `minimal`.

A bare call with no `generation_config` returns steps `['thought',
'model_output']` — thinking runs by default. **Cheap recipes must set
`thinking_level: minimal` explicitly**; omitting it is not the cheap path.
`--thinking` is the expensive knob, not media resolution.

`thinking_summaries` is a literal `'auto' | 'none'`, **not a boolean** — passing
`True` fails schema validation.

### Storage, state, and lifetimes

Two independent clocks:

- **Files API upload: 48 hours.** 2GB per file, 20GB per project.
- **Interaction storage: 55 days** on paid tier (configurable to 7/14/28 in AI
  Studio), 1 day on free tier. Deletable programmatically.

`store=true` is the default. `store=false` disables **both**
`previous_interaction_id` and `background=true`.

### Delete does not work. Purge is impossible.

`client.interactions.delete(id)` exists in the SDK, the API reference documents
the endpoint, and the overview states "You can delete stored interactions at any
time using the delete method."

**The server returns HTTP 501:**

```
Error code: 501 - {'error': {'message': 'Operation is not implemented,
or supported, or enabled.', 'code': 'not_implemented'}}
```

Reproduced on every attempt. There is also no `list` method (the set is
`create`, `get`, `cancel`, `delete`), so there is no enumerate-then-clean path
either.

Consequences, and they are significant:

- **`purge` cannot be built.** Drop it from the CLI surface.
- **Anything stored is stored for the full retention window**, full stop. The
  7-day project setting in AI Studio is not a backstop — it is the *only*
  control that exists.
- **`stateful: false` becomes the meaningful privacy lever**, because it is the
  only one. A recipe that opts into storage is opting into an irrevocable
  window. Weight the per-recipe default accordingly.
- The probe left two undeletable interactions behind (trivial "Remember: blue"
  content). Any future probing of stateful behavior leaves permanent residue.

### Correction: bulk deletion exists in the UI

`interactions.delete` returns 501 and that stands -- there is no programmatic
purge, and no `list` to enumerate what exists. But AI Studio's log settings
dialog has a **Delete project logs** button that clears them project-wide.

So the accurate statement is "cannot be deleted via the API", not "cannot be
deleted". The mitigation is manual and all-or-nothing rather than per-run, but
it is immediate rather than waiting out the retention window.

That dialog also carries a per-API storage toggle. The **Interactions API**
toggle sets the project default; a per-request `store` value overrides it. Since
every shipped recipe is `stateful: false` and therefore sends `store: false`,
turning the project toggle off costs nothing and makes storage opt-in --
worth doing, because a misconfigured recipe would otherwise be retained
silently.

Re-test `delete` periodically — a 501 reads like "not enabled yet" rather than
"never." If it starts working, `purge` becomes buildable and the storage
calculus changes.

Because the clocks are independent, `store=false` costs you the *conversation*,
not the *upload*. Guessing wrong means re-paying input tokens on the next turn,
not re-uploading bytes.

Free tier is marked "Used to improve our products: **Yes**." Paid tier: **No**.
That is the argument for paid, independent of rate limits.

### Not available on the Interactions API

From the overview's Limitations section:

- `video_metadata` (clipping, custom fps)
- Batch API — so the Batch pricing tier is unreachable here; **Flex is not**
- **Explicit caching** — only implicit caching, obtained by using
  `previous_interaction_id`. There is no cache object to create or pay hourly
  storage on. An earlier design that leaned on explicit caching was wrong.
- Automatic function calling (Python) — the manual loop is the only path
- Custom safety settings
- Remote MCP on Gemini 3 ("coming soon") — Gemini calling our MCP servers is out

### Pricing

Clean markdown tables at a stable `.md.txt` URL, per model, per service tier
(Standard / Batch / Flex / Priority). For `gemini-3.6-flash` standard:
$1.50/1M input, $7.50/1M output. Flex is half. Search grounding is metered
separately: 5,000 requests/month free across Gemini 3.x, then $14/1,000.

At 70 tokens/frame and 1 FPS, video is far cheaper than first assumed — roughly
a third of a cent per minute of input at standard rates. The caching and reuse
complexity is not worth it for short clips.

**No dollar figure is ever written into a SKILL.md.** See the pricing refresh
design below.

## Architecture

Thin transport, fat recipes. The CLI stays small and stable; growth happens in
data.

```
apps/gemini-bridge/
  .claude-plugin/plugin.json
  commands/gemini.md                 # typed entry point, argument-hint
  skills/gemini-multimodal/
    SKILL.md                         # routing table + invariants. Small.
    references/
      api-modes.md                   # the axes and the constraint graph
      video.md  audio.md  images.md  documents.md
      files.md                       # 4 input methods, 48h lifetime
      structured-output.md
      params.md
      recipes/                       # the expansion point
        perceptual-diff.md
        scene-to-data.md
        video-to-code.md
      models.json                    # generated cache
      pricing.json                   # generated cache
  src/gemini_bridge/                 # auth, upload, ffmpeg prep, params,
                                     # run dirs, budget cap, purge
  pyproject.toml
  README.md
  # no hooks/, no MCP server
```

### Recipes are the core idea

A recipe is data, not code — a system instruction plus a response schema plus
parameter defaults:

```
perceptual-diff.md
  system_instruction:  "You are comparing renders of the same 3D scene..."
  response_format:     {differences: [{region, kind, severity, evidence}], identical: bool}
  resolution:          high on subjects, low on context
  model:               gemini-3.6-flash
  thinking_level:      medium
  stateful:            false
```

`system_instruction` is what makes this work, and it was the missing piece for
most of the design session. Without it, the quality of a Gemini answer depends
on how Claude happened to phrase things that session. With it, the analytical
stance is fixed, versioned, and diffable, and Claude supplies only the specific
question. Combined with `seed`, results become actually reproducible.

Same shape as `model-routing` shipping a rules file instead of a hook: behavior
as data in the repo, editable without touching Python.

Note: `system_instruction` and `generation_config` are **interaction-scoped**.
A follow-up must re-send them. The run directory therefore persists the whole
parameter set, not just the interaction ID — otherwise turn 2 silently runs with
no system instruction and different settings.

`client.agents.create()` also accepts `system_instruction`, which would register
a named agent server-side. Avoid it: that is state on Google that drifts from
the repo and cannot be diffed.

### Run directory — the handoff contract

Every invocation writes:

```
.gemini-runs/<timestamp>-<slug>/
  request.json      exactly what was sent (media manifest, params, recipe ref)
  prompt.md         the composed question — editable, re-runnable
  response.md       Gemini's answer
  response.json     structured output when a schema was used
  interaction.id    for previous_interaction_id follow-ups
  usage.json        token breakdown and cost
```

**stdout must stay small.** Tool output lands in Claude's context and stays
there for the session. The CLI prints run-dir path, model, tokens, cost, status,
and at most a few lines of head. The full answer goes to `response.md`, which
Claude reads deliberately. Same progressive-disclosure discipline as SKILL.md,
applied to tool output.

### The usage axes and their constraint graph

Not 11 modes — a handful of mostly-orthogonal axes:

| Axis | Values |
|---|---|
| History | stateful (`previous_interaction_id`) / stateless |
| Storage | `store=true` / `store=false` |
| Delivery | blocking / `stream=true` |
| Execution | foreground / `background=true` |
| Target | `model=` / `agent=` |
| Output | free text / `response_format` schema |
| Tools | none / built-ins / own functions |
| Service tier | standard / flex / priority |

The valuable part is what is illegal, which the CLI should validate up front
rather than letting Google return a 400:

- `store=false` ⇒ no `previous_interaction_id`, no `background`
- `background=true` ⇒ requires `store=true`
- agents ⇒ require `background=true`
- managed agents ⇒ require `environment="remote"`
- mixing models mid-conversation ⇒ the next model must accept the previous
  model's output modalities

Best practice from the overview worth using: **agents and models can be mixed in
one conversation** via `previous_interaction_id`. Deep Research collects, a cheap
Flash reformats, no re-upload.

## Decisions made

| Decision | Rationale |
|---|---|
| **Gemini Developer API key, billing account linked, via 1Password `op://`** | A Google AI Ultra subscription does not change your API *tier* — the rate-limit tiers qualify on billing alone, and subscriptions are absent from the billing docs entirely. It does supply **$100/month in Google Cloud credits** (via Google Developer Program premium), which reach programmatic usage through Vertex. Two facts make the Developer API the right v0.1 default anyway: `client.files.upload` raises on Vertex clients (Gemini Developer API only), and Tier 1 needs a *linked* billing account, not $250 of spend — the $250 is the cap. Linking billing also flips "used to improve our products" from Yes to No at zero cost. Build auth and file attachment as a **seam** so Vertex stays reachable; revisit at phase 4 when video needs uploads and GCS URI registration (2GB/file, no 48h expiry) becomes the substitute. Antigravity is not a path: its **SDK** is API-key/ADC only (OAuth is an open feature request), and only its **CLI** gets subscription limits — a full agent harness, wrong shape for one multimodal call. |
| **CLI, not MCP server** | Works outside Claude Code, testable as a plain package, exact invocation visible in the transcript. Note the earlier claim that "MCP means the model can call it whenever" was **overstated** — MCP tools go through the same permission system. The honest cost of the CLI is schema drift (flags documented in SKILL.md are a copy that can rot); mitigate by generating the flag reference from `--help` and failing a test on mismatch. |
| **MCP as a possible later wrapper, not now** | `agent-state` / `agent-state-mcp` is the precedent: CLI first, thin opt-in MCP adapter over it later if the two-calls-and-a-temp-file rhythm becomes annoying. Do not build both. |
| **No hooks** | Runs against invariant 1c's tier test. SessionStart is the pattern already disabled for three plugins here. UserPromptSubmit fires on every prompt to catch a rare case and duplicates skill triggering. PostToolUse duplicates stdout. PreToolUse budget guards are the only defensible one, and they belong in the CLI — the narrower chokepoint that also covers manual, scripted, and subagent callers. |
| **Skip Google's recommended docs MCP server** | It is a docs-search server, not a call server. `skill-maintain upstream` already does snapshot + diff, at zero ambient context cost. |
| **`apps/gemini-bridge`, one plugin** | User's call. Cascade is the four-file variant: `plugin.json` + root `marketplace.json` + `CHANGELOG.md` + `apps/gemini-bridge/pyproject.toml`, plus `uv lock`. Editing anything under `src/` triggers it. |
| **v0.1 scope: images + video + audio + documents. No generation.** | Video moved from "big scope increase" to "another content type plus an upload plus an ffmpeg prep step" once it was clear the prep is local, free, and testable. Image/video generation is v2. |
| **Model-invocable skill, `disable-model-invocation` NOT set** | Subagents cannot type slash commands, so the flag would permanently bar delegated agents from vision work. Skill loading has never been what gates the external call — the Bash permission prompt is, identically in both cases. **But see the advisor precedent below — this decision deserves one more look.** |
| **`google_search` grounding exposed** | Confirmed by user. Built-in tool, returns URL citations in response annotations. Citations get written to the run dir. |
| **Storage tied to statefulness, declared per recipe** | Most recipes are one-shot and store nothing. Iterative ones (video-to-code) opt in. `--stateful` / `--no-stateful` overrides. Backstop is a **7-day project retention window set once in AI Studio** — a guarantee that does not depend on our cleanup code running, unlike delete-on-close, which fails exactly when it is most needed (a crash mid-run). |

## Open questions

1. **Does `temperature` really not exist?** Three sources say no (OpenAPI,
   generated SDK, absence from every example); one says yes (overview prose).
   Settle with a live call. Low stakes — `seed` is better for this use case —
   but worth knowing.
2. ~~`transcription_config` and `video_config`~~ — **RESOLVED**, see above.
   `transcription_config` is the audio surface (diarization, word timestamps,
   custom vocabulary); `video_config` is generation-only and irrelevant to v0.1.
3. ~~Model-list endpoint~~ — **RESOLVED.** `client.models.list()` does exist and
   returns a `Pager[types.Model]`, but it is **entirely the legacy surface** —
   there is no model-listing call anywhere under `_gaos`. The Interactions
   `Model` type is a hardcoded `Literal` union plus an `UnrecognizedStr` escape
   hatch, so arbitrary model strings still pass at runtime. Usable for the
   refresh cache; do not describe it as part of the Interactions API.
4. **Local function calling** (`--tools`) — worth building eventually, but it
   inverts control: Gemini drives a `while True` loop executing code on the
   machine, outside Claude Code's permission system. Constraints if built:
   allowlisted pure read-only functions declared in a tracked config, hard
   iteration cap, no writes and no shell, every call logged, opt-in per
   invocation, never allowlisted in settings. The high-value functions are ones
   that let Gemini ask for *more data about what it is already looking at*
   (`list_frames`, `read_frame(n)`, `measure_region`), not ones that act.
5. **Bash timeout.** Default 120s, max 600s. Large video plus `thinking: high`
   can exceed it. Options: `background=true` plus a `poll` subcommand (requires
   `store=true`), or `run_in_background` on the Bash call. Decide alongside the
   storage design.
6. **`status: incomplete`** is a distinct terminal state — "completed, but
   contains incomplete results (e.g. hitting max_tokens)". A truncated scene
   JSON otherwise looks like success. Must be handled loudly.

## Staying current

Three layers, because three things drift at different speeds.

1. **Doc pages** — every page is served as plain markdown at `<url>.md.txt`.

   **URL trap, verified the hard way:** the overview lives at
   `gemini-api/docs/interactions-overview.md.txt` — *no* `interactions/`
   subdirectory. A path of `gemini-api/docs/interactions/interactions-overview.md.txt`
   also returns HTTP 200 but serves different, incomplete content: four
   limitation bullets instead of five, and no data-retention section. A
   verification pass using the wrong path produced two false "the docs don't say
   this" findings. Pin the exact URLs in the tracking config and diff the byte
   count, not just the text.

   Point `skill-maintain upstream` at: `interactions-overview`,
   `interactions/video-understanding`, `interactions/audio`,
   `interactions/document-processing`, `interactions/media-resolution`,
   `interactions/files`, `file-input-methods`, `interactions/thinking`,
   `interactions/structured-output`, `tokens`, `pricing`. Clean line/char diffs,
   no HTML scraping.
2. **SDK** — `coderef/python-genai` is a real clone. Add it and
   `coderef/gemini-skills` to `update-coderef.sh`. The generated `_gaos` types
   are the highest-authority source; when they change, our param surface changes.
3. **Model IDs and pricing** — never baked into a skill.
   `gemini-bridge pricing --refresh` parses the pricing tables into
   `pricing.json` with a timestamp; the cost estimator and `--dry-run` read that.
   Warn when stale. Same pattern for models.

Note there is a "May 2026 Breaking Changes Migration Guide" in the doc index.
This API breaks. Pin the SDK exactly.

## Relationship to model-routing and advisor

Three plugins, three different routing decisions. Worth naming, because they
look adjacent and are not:

| Plugin | Direction | Binding constraint |
|---|---|---|
| `model-routing` | down-tier, within Claude | **cost** — several options work, pick the cheapest |
| `advisor` | up-tier, within Claude | **capability**, bounded by spend |
| `gemini-bridge` | cross-vendor | **capability** — the default option does not work at all |

**`model-routing` should not be modified for this.** Reasons:

- Its criteria are crisp because they answer one question ("is this mechanical
  enough for a cheaper model?"). Cross-vendor capability routing is a different
  question — it exists because the default *fails*, not because a cheaper option
  suffices. Folding them together makes both fuzzier.
- Its base rule is deliberately standalone — "no external tool, no CLI". A
  Gemini clause would reference a CLI absent from most repos where that rule
  lands. There is a clean opt-in slot (same pattern as the agent-state feedback
  layer) but it is not earned yet.
- "When to reach for Gemini" is what the gemini skill's own description is for.
  Duplicating it into `model-routing` creates a copy whose only reader is the
  belief that the two should agree — invariant 1b.
- One incident is not evidence for a routing rule. Wait for the log.

**What to do instead:** put the failure signature in the gemini skill's
description, so it triggers on the symptom rather than only on file type —
"…when a visual question is being answered with pixel math, histograms, or diff
statistics because direct comparison isn't working…"

**The additive integration:** `model-routing`'s optional feedback layer logs
delegation outcomes to `agent-state`. Gemini calls can write to the same DB —
model, recipe, tokens, cost, accepted or not. Touches nothing in
`model-routing`, and after a month it says empirically which recipes are worth
the money and what tier each needs. That is how a routing rule should get
written: from the log, not from the incident that prompted it.

### The advisor precedent — revisit decision on invocation

`skills/advisor` is the closest sibling in this repo and it made the **opposite**
call. It sets `disable-model-invocation: true` and enforces user-only invocation
in three layers: the flag keeps the skill out of context entirely, a
`UserPromptExpansion` hook mints an authorization only on a user-typed command,
and a `PreToolUse` hook denies any spawn whose authorization is missing, expired,
or names a different model.

Its reasoning: the advisor's whole value is a *bounded* second opinion, so a
model that can self-authorize consults defeats the point.

That argues against the decision recorded above, and the machinery already
exists in this repo. A synthesis worth considering before writing code:

> Model-invocable skill, with a **tiered** authorization. Cheap read-only calls
> (a couple of images, no thinking budget, under a threshold) run under the
> ordinary Bash permission prompt. Expensive ones — video, `thinking: high`, the
> function-calling loop — require an advisor-style authorization minted only by
> a user-typed command.

That would preserve subagent access to the cheap path, keep NL ergonomics, and
put a hard gate exactly where the money and the control risk actually are. It
also reuses a pattern this repo has already built and debugged rather than
inventing a second one.

## What to verify first

Before designing further, make one real call and check:

1. Does `temperature` get accepted or rejected?
2. What do `transcription_config` and `video_config` actually accept?
3. Does `count_tokens` on `client.models` agree with `usage` on the interaction
   for the same media?
4. Is there a model-list endpoint on the SDK?

All four are cheap, and all four are currently assumptions.
