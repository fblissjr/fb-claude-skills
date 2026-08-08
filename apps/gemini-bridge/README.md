last updated: 2026-08-08

# gemini-bridge

Hand a task to a Gemini model and get a structured answer back — without
copy-pasting between two chat windows.

Built for one problem first: comparing two renders of the same scene and
reporting what a person would actually notice. Claude can measure images with
code but cannot reliably see the difference between them; Gemini can. Since
0.7.0 the bridge is not vision-only: any call that does not need a saved
recipe can be made ad-hoc, with every parameter set from the command line.
Since 0.8.0 it takes **video and audio** too, which is the harder capability
gap — those are files Claude cannot open at all.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install gemini-bridge@fb-claude-skills
```

The CLI is a Python package:

```bash
uv tool install --from apps/gemini-bridge gemini-bridge
gemini-bridge doctor
```

## Credentials

No secret manager is required, and none is privileged. Either export an API key:

```bash
export GEMINI_API_KEY=...
```

or point the tool at any command that prints your key, in
`<HOME>/.config/gemini-bridge/config.toml` (`gemini-bridge doctor` prints the
exact path it reads):

```toml
[auth]
key_command = "pass show gemini/api-key"
# key_command = "security find-generic-password -w -s gemini"
# key_command = "doppler secrets get GEMINI_API_KEY --plain"
```

The config file holds a *command*, never a key. The key is fetched per call and
never written to disk, never logged, and redacted from tracebacks. The run
record stores only coarse provenance (`key-command` or `env:VARNAME`), because
a key command usually names a vault and an item.

**Use a project with a billing account linked.** On the free tier, Gemini API
inputs are used to improve Google's products; on the paid tier they are not.
Linking billing is a form, not a purchase — the tier threshold is a spend *cap*,
not a spend requirement.

## Usage

```bash
gemini-bridge ask -r perceptual-diff -f before.png -f after.png \
  "The first is BEFORE a change, the second is AFTER."

gemini-bridge ask ... --dry-run    # print the manifest, call nothing
gemini-bridge recipes              # list available recipes
gemini-bridge stats                # token totals per recipe from the ledger
gemini-bridge stored               # interactions held server-side
gemini-bridge uploads              # files held by the Files API (deletable)
gemini-bridge formats              # what can be attached, and how each travels
gemini-bridge doctor               # config, credentials, recipes, guards
```

### Video and audio

```bash
gemini-bridge ask -f recording.mp4 \
  --system "You are reverse-engineering a UI interaction so it can be rebuilt." \
  "Trace the drawer animation: timestamp, what moves, how far, how long."
```

Attaching a video or an audio file uploads it to the Files API and sends a
reference; images and PDFs still attach inline, and anything past the inline
cap is uploaded regardless of kind. Four consequences:

- **The upload is a disclosure with a 48-hour life.** Unlike a stored
  interaction, it can be taken back — `gemini-bridge uploads` lists what this
  project is holding at Google, `--delete` removes it now.
- **Identical bytes upload once.** Handles are cached by content hash for the
  48h window and confirmed with the server before reuse, so a series of
  questions about one recording costs one upload. Change the file and the hash
  changes with it, so a stale handle can never answer for new bytes.
- **It is slow.** Give the command more than the default 120s if the file is
  large, and raise `--upload-timeout` (default 300s) if processing runs long.
- **Frames are sampled at 1 FPS and cannot be clipped or retimed** — the API
  offers no fps, start, or end controls. Trim with ffmpeg before sending, and
  do not expect sub-second events to be seen at all.

The prompt is where the quality comes from, and it is yours to write: a video
sent with no context returns a plot summary. Say what the file is, what
decision the answer feeds, and what to ignore; use `--system` for the stance.
A call that attaches media and asks nothing runs a generic default and warns
about it. Detail and ffmpeg recipes:
[skills/gemini-multimodal/references/video.md](skills/gemini-multimodal/references/video.md).

`-r` is optional. Without it the call runs as `adhoc` — no system instruction
unless you pass one — and every parameter a recipe could set is a flag:

```bash
# text-only question, no recipe, deeper thinking
gemini-bridge ask --model gemini-pro-latest --thinking-level high \
  "Poke holes in this migration plan: ..."

# ad-hoc stance plus structured output
gemini-bridge ask --system-file stance.md --schema-file verdict.schema.json \
  -f screenshot.png "Does this page match the spec?"

# multi-turn: --store opts in to server-side storage (NOT deletable),
# then --continue-from picks the interaction up
gemini-bridge ask --store "First question..."
gemini-bridge ask --store --continue-from v1_abc123 "Follow-up..."
```

Also settable: `--seed`, `--max-output-tokens`, `--service-tier`,
`--label key=value`. Precedence is CLI flag > recipe value > built-in default.
Thinking defaults to `minimal` either way — an unset level is the expensive
path, so raising it is always an explicit act. `--system`/`--system-file`
cannot be combined with `-r`: the run is labeled with the recipe's name, and
swapping the stance under that name would mislabel the record.

## What gets checked before anything is sent

Two guards, both on by default, because a call cannot be recalled — the API's
delete endpoint returns 501, so the only cleanups are the project retention
window and a project-wide bulk delete in the console.

**Attached files** are matched against a built-in pattern set covering shapes
that are secrets or nothing (`*.pem`, `id_rsa`, `.env`, `.ssh`, and similar),
plus anything you add. Matching is case-insensitive, expands home-relative and
environment-variable prefixes in your patterns, and runs on the raw arguments
before any file is opened. It is designed to over-block rather than
under-block.

**The prompt itself** is scanned for secret-shaped content — API keys, tokens,
private key blocks, JWTs. High-confidence shapes refuse the call; weaker signals
(an email address, an absolute home path) warn and continue. Findings are
redacted in the message, so a warning never reproduces the thing it found.
`--allow-prompt-secrets` overrides when they are false positives.

This matters because the prompt is usually composed by Claude, which has been
reading your files. Checking only which files are attached would leave the
larger opening unguarded.

**What neither guard covers**, stated plainly because each was confirmed by a
red-team pass rather than assumed:

- **The contents of any attachment.** A screenshot showing a password, or a CSV
  with a key in a cell, passes both checks -- the path guard sees a filename,
  the prompt scanner reads only the prompt. Look at what is in a file before
  attaching it.
- **A hardlink to a blocked file.** Matching is on the path string, not the
  inode, so a hardlink under an innocuous name defeats every pattern. This is
  a guard against mistakes, not against someone determined to route around it.
- **Secrets with no distinguishing shape.** AWS secret access keys, bare bearer
  tokens, and most passwords look like ordinary text. No pattern scanner
  catches those, and this one does not pretend to.

Configure in `.gemini-bridge.toml` at the project root:

```toml
[privacy]
sensitive_paths = ["design-docs", "*.sketch"]
# use_defaults = false   # drop the built-in patterns
# scan_prompt  = false   # disable prompt scanning
```

`gemini-bridge doctor` reports how many patterns are active and whether prompt
scanning is on.

## Skills

| Skill | Description |
|-------|-------------|
| [gemini-multimodal](skills/gemini-multimodal/SKILL.md) | Route a task to Gemini in any modality — image, video, audio, PDF, or text — pick a resolution from measured guidance, and read the answer from the run directory. |

The skill is a routing layer; the detail lives in three references beside it:
[api.md](skills/gemini-multimodal/references/api.md) (models, parameters,
storage, token accounting, what is deliberately not exposed),
[media.md](skills/gemini-multimodal/references/media.md) (per-modality routing,
formats, resolution and cost, size limits), and
[video.md](skills/gemini-multimodal/references/video.md) (video and audio end
to end).

## Invocation

```
/gemini-bridge:gemini                     # slash command
"have Gemini compare these two renders"   # natural language
"ask Gemini what changed between these"
```

## Run directories

Every call writes `.gemini-runs/<timestamp>-<recipe>/` into the current project:

```
prompt.md        the system instruction and the question
request.json     the media manifest and parameters -- never the base64 payloads
response.md      the answer as prose
response.json    the structured verdict, when the recipe defines a schema
usage.json       token counts, broken down by modality
uploads.json     Files API handles this run created or reused, when any
```

The runs root writes its own `.gitignore` containing `*` on first use, so run
output cannot be committed into your repo by accident. A `ledger.jsonl` beside
it records one line per call — model, recipe, tokens, duration, status — using
only facts the API reported, never a self-assessment. An `upload-cache.json`
sits beside it holding Files API handles keyed by content hash; it is what
makes a re-asked question skip the upload, and what lets `uploads --delete`
name a file after the run directory that created it is gone.

**Add `.gemini-runs/` to your project's own `.gitignore` as well.** The
self-ignore is a single file: delete it and the tree is stageable until the next
call rewrites it, and nothing announces that window. `gemini-bridge doctor`
reports whether the marker is currently in place. The tool does not edit your
`.gitignore` for you.

Two ledger fields are worth knowing about. `prompt_scanned` is false when the
scan **did not gate the send**, whatever the route — the
`--allow-prompt-secrets` flag on that call, or a project config with
`scan_prompt = false`. That is the field to filter on when auditing for
ungated runs: it does not mean a secret was confirmed present. (Since 0.7.1
the flag route still scans and prints its findings — only the block is
waived; the config route skips the scan entirely.) Either way the run
directory holds that text in plaintext locally, and since the interaction
cannot be deleted through the API, the copy at Google is permanent. Filtering the ledger is the only way to find those runs without
grepping every `prompt.md`, which means reading the very content the bypass
was used to send. `allow_prompt_secrets` records the route: true when the flag
was passed on that call, so a deliberate one-off bypass is distinguishable
from a standing config opt-out. (Before `prompt_scanned` existed, the config
route produced rows saying `allow_prompt_secrets: false` for runs that were
never scanned — rows older than that field carry no `prompt_scanned` key and
should be read with that in mind.)

## Recipes

A recipe is data, not code: YAML frontmatter for parameters, markdown body for
the system instruction. Adding one is adding a file.

Keeping the analytical stance in a versioned file is what makes results
reproducible. Composing the prompt fresh each session makes the answer depend on
how the question happened to be phrased that day.

Before trusting a new comparison recipe, run it against a **null pair** — the
same file twice. A differ that reports differences between an image and itself
is worse than none, and that failure is invisible if you only test on inputs
that genuinely differ.

## Design notes

The API surface here was verified by live probing, not from documentation — the
docs, the OpenAPI spec, and the generated SDK each turned out to be wrong about
something material. Findings, decisions, and what is deliberately not built:
[docs/internals/gemini_bridge_design.md](../../docs/internals/gemini_bridge_design.md).
