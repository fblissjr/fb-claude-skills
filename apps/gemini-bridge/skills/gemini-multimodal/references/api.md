# How the bridge and the API work

Read this when you need to set a parameter and want to know what it does, or
when something returned a shape you did not expect. For attaching files, see
`media.md`; for video specifically, `video.md`.

Everything here is stated with its source. That distinction is load-bearing in
this plugin: the docs, the OpenAPI spec, and the generated SDK have each been
caught being wrong about something material, so a claim's provenance tells you
how much to trust it.

- **probed** — confirmed by a live call (`scripts/probe.py`). Authoritative.
- **SDK** — read from the generated types in `google/genai/_gaos/`. Reliable
  about shape, and has been wrong about behaviour.
- **docs** — from Google's documentation. Treat as a hypothesis.

## The call

One `gemini-bridge ask` is one `client.interactions.create(...)`. There is no
conversation and no retry loop unless you ask for one.

```
your flags + recipe
   -> media resolved (inline bytes, or uploaded and referenced by uri)
   -> one create() call
   -> .gemini-runs/<timestamp>-<recipe>/   <- the answer lives here
```

stdout stays deliberately small — run path, status, token counts — because
tool output stays in context for the rest of the session. Read `response.md`
or `response.json` from the run directory instead.

## Where each parameter lives

The commonest 400 is a valid parameter in the wrong place. Only these ten go
inside `generation_config` (SDK):

```
image_config · max_output_tokens · seed · speech_config · stop_sequences
thinking_level · thinking_summaries · tool_choice · transcription_config
video_config
```

Everything else is **top level** on the request: `system_instruction`,
`response_format`, `service_tier`, `labels`, `store`,
`previous_interaction_id`, `tools`, `stream`, `background`,
`response_modalities`, `environment`, `webhook_config`, `safety_settings`.

The CLI and recipes place these for you. It matters when you are writing a
recipe or reading `request.json`.

## Models

`--model`, or `model:` in a recipe. Recipes default to `gemini-3.6-flash`.

**A wrong model id is not caught locally.** The SDK types it as a `Literal`
union of known ids *plus* an `UnrecognizedStr` escape hatch, so any string
passes validation and the failure arrives from the server. Check the id rather
than trusting a typo to be rejected.

Two ways to name a model, with a real tradeoff:

- **Pinned** (`gemini-3.6-flash`) — reproducible. A recipe with a `seed` is
  only reproducible if the model is pinned too.
- **Alias** (`gemini-flash-latest`, `gemini-pro-latest`) — follows Google's
  current release. Good for ad-hoc calls, wrong for a recipe you want to
  compare against last month's run.

Choosing a tier: Flash is the default for a reason and handles almost
everything here, including video. Reach for Pro when the task needs reasoning
*about* what it sees rather than accurate reporting *of* it — inferring intent
from a UI recording, judging whether a design works. Perception is not the
part Pro improves most.

The authoritative current list is the `Model` union in
`google/genai/_gaos/types/interactions/model.py` in the installed SDK, and
`https://ai.google.dev/gemini-api/docs/models`. Do not trust a model id
remembered from elsewhere — this API's lineup moves.

## Thinking, and why it is the expensive knob

**Thinking is ON by default, and thought tokens bill at the output rate**
(probed). An unset `thinking_level` is the expensive path, not the cheap one,
which is why every recipe here sets `minimal` explicitly.

Probed on "what is 17 * 23":

| thinking_level | input | output | thought | total |
|---|---|---|---|---|
| `high` | 17 | 3 | **195** | 215 |
| `minimal` | 17 | 3 | **0** | 20 |

Levels are `minimal`, `low`, `medium`, `high`. Raising it is a per-call
decision worth stating a reason for. For perception — "what is in this frame",
"what changed" — `minimal` is usually right, because the work is looking, not
reasoning. Raise it when the answer requires a chain of inference from what was
seen.

`thinking_summaries` is a literal `'auto' | 'none'`, **not a boolean** (SDK);
passing `True` fails validation.

## Determinism

- `seed` **is** honored (probed): same seed and prompt gave identical output
  twice. Pin it in any recipe whose runs you intend to compare.
- `temperature` is **accepted and silently ignored** (probed). At 0.0 the same
  prompt still varied; 0.0 and 2.0 produced identical answer sets. Recipes
  reject it outright rather than let it imply control that does not exist, and
  there is no `--temperature` flag on purpose. A parameter that is accepted,
  does nothing, and reports no error is worse than one that 400s.

## Structured output

`--schema-file`, or `schema:` in a recipe, sends a `response_format` and the
reply comes back as JSON in `response.json`.

Worth knowing: if the model hits `max_output_tokens` mid-object the status is
`incomplete` and the JSON will not parse. The CLI reports that as a
truncation, not as a parser complaint, because blaming the parser buries the
real cause. Raise `--max-output-tokens` or simplify the schema.

A schema is not free — its field descriptions are input tokens, and they are
scanned for secret-shaped content like any other outgoing text.

## Storage, follow-ups, and the thing that cannot be undone

`store` defaults to **false** on every recipe, and that is the only privacy
lever that exists.

- **`interactions.delete` returns HTTP 501** (probed, repeatedly). Anything
  stored is stored for the project's full retention window. There is also no
  `list` endpoint, so the run directories and `ledger.jsonl` are the only
  record of what exists.
- `--store` opts in, which is what `--continue-from` requires. Use it only
  when follow-up turns are genuinely needed.
- `gemini-bridge stored` lists what is out there. It is a disclosure list, not
  a purge list — the only bulk cleanup is the **Delete project logs** button in
  AI Studio's log settings, which is project-wide and immediate.
- Free tier is marked "used to improve our products: yes"; paid tier, no. That
  is the argument for linking billing, independent of rate limits.

`system_instruction` and `generation_config` are **interaction-scoped**: a
follow-up that omits them runs with neither. The run directory therefore
records the whole parameter set, not just the interaction id.

Uploaded files are the one exception to all of this — `files.delete` works.
See `media.md`.

## Service tiers

`--service-tier` takes `standard` (default), `flex`, or `priority` (SDK,
`flex` probed accepted).

`flex` is roughly half price for latency-tolerant work, which fits nearly
everything this bridge does. `priority` has a catch worth knowing before
reaching for it: its default rate limit is about **0.3x** the standard limit
for the model, and on overflow it degrades to standard billing rather than
failing.

## Counting tokens: measure, never compute

**Three Google doc pages give three different video token rates, differing by
about 4x, and none cross-references the others.** The tempting resolution —
that the newest page supersedes the others — does not hold, because the oldest
page's own worked example targets a current model.

So: do not compute an estimate from a formula. `usage` on the response is
exact and costs nothing extra, and it is written verbatim to `usage.json`:

```json
{"input_tokens_by_modality": [{"modality": "text", "tokens": 17}],
 "total_input_tokens": 17, "total_output_tokens": 3,
 "total_thought_tokens": 195, "total_cached_tokens": 0,
 "total_tool_use_tokens": 0, "total_tokens": 215}
```

The per-modality breakdown is what makes a video call attributable: it says how
much the video cost versus the prompt. `gemini-bridge stats` aggregates the
ledger by recipe.

**There is deliberately no pre-flight token estimate.** `count_tokens` requires
uploading the media to count it, so a `--dry-run` that called it would send
exactly the files the flag exists to avoid sending. `--dry-run` is local-only
and opens no connection.

No prices are written anywhere in this plugin, deliberately: a stale constant
in a file looks authoritative in a way that "go and look" does not. Current
rates are at `https://ai.google.dev/gemini-api/docs/pricing`.

## Not available on this API

From the overview's limitations, and relevant here:

- **`video_metadata`** — no clipping intervals, no custom frame rate. This is
  the constraint that shapes all video work; see `video.md`.
- **Explicit caching** — only implicit caching, via `previous_interaction_id`.
  There is no cache object to create.
- **Batch** — so the Batch price tier is unreachable. Flex is not.
- **Custom safety settings** — the SDK has the field; the docs say it is
  unsupported. Do not rely on it.
- **Automatic function calling** (Python) and remote MCP on Gemini 3.

## What this CLI does not expose

Not oversights — each is either unverified or a deliberate omission:

- **`transcription_config`** (word timestamps, speaker diarization, custom
  vocabulary) is a valid `generation_config` key and **is settable from a
  recipe**, since recipes pass generation config through. It has no flag
  because it has never been probed live. If you use it, extend
  `scripts/probe.py` first.
- **`tools` / function calling** — inverts control: Gemini would drive a loop
  executing code outside Claude Code's permission system.
- **`stream`, `background`** — background needs `store=true` plus polling,
  which this tool does not do.
- **`speech_config`, `image_config`, `video_config`** — generation, not
  understanding. `video_config` in particular is text-to-video and has nothing
  to do with analysing a video.

## Extending this safely

The rule that produced every probed finding above: **form the hypothesis from
the SDK or the docs, then confirm it with a live call before exposing it.**
`scripts/probe.py` is that instrument — each arm is isolated, so one 400 does
not hide the rest, and a full run costs a few cents.

Source pages, all served as plain markdown by appending `.md.txt`:

| Page | URL under `https://ai.google.dev/gemini-api/docs/` |
|---|---|
| Overview | `interactions-overview` |
| Video | `interactions/video-understanding` |
| Audio | `interactions/audio` |
| Documents | `interactions/document-processing` |
| Media resolution | `interactions/media-resolution` |
| Files | `interactions/files` |
| Thinking | `interactions/thinking` |
| Structured output | `interactions/structured-output` |
| Models / tokens / pricing | `models`, `tokens`, `pricing` |

**URL trap, learned the hard way:** the overview is `interactions-overview`,
with no `interactions/` prefix. The prefixed path also returns HTTP 200 and
serves *different, incomplete* content — a verification pass using it produced
two false "the docs don't say this" findings.

Design history, including the findings that were later disproved and why that
matters: `docs/internals/gemini_bridge_design.md` in the repo.
