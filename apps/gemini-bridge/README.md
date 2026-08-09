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
- **Identical bytes upload once.** Reuse is matched on a content hash over the
  48h window and confirmed with the server first, so a series of questions
  about one recording costs one upload. Change the file and the hash changes
  with it, so a stale handle can never answer for new bytes.
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

## The spend gate

Claude Code's Bash permission prompt is the usual protection, but it is one you
can allowlist away or click through, and it cannot tell "look at this
screenshot" from "upload forty minutes of video". So expensive and
irreversible calls need a second thing: an authorization only a **user-typed**
slash command can create.

```
/gemini-bridge:gemini-authorize              # single use, 10 min, 200k token ceiling
/gemini-bridge:gemini-authorize --max-tokens 500000
```

A call is gated when it is over ~20,000 estimated input tokens, uses `--store`
(which cannot be undone — `interactions.delete` returns 501), raises
`--thinking-level` to `medium` or `high`, or sets `--max-output-tokens` above
the same limit (output bills at several times the input rate, which is the same
reason raised thinking is gated). Everything else — screenshots, PDFs, short
clips, text questions — runs under the ordinary prompt exactly as before.

The estimate covers the **whole** input: attachments plus every text channel
the request carries — question, system instruction, schema, and label values.
That is the same list the secret scanner walks, and it is now literally the
same list in the code, because the two were built separately and disagreed: a
3MB `--schema-file` was scanned and then costed at one token, printing `gate
none` on a call of roughly a million.

**Minting and enforcing are deliberately split.** A `UserPromptExpansion` hook
mints, because only a user-typed command can reach that event; the main loop
cannot. The command also carries `disable-model-invocation: true`, so its
description never enters context and the SlashCommand tool cannot reach it —
without that, the whole design rests on an untested assumption about which
paths fire that event, which is the shape of the 0.11.0 no-op. `doctor` cannot
detect a regression in either half of that, which is why it is written down
here. The CLI enforces, because it is the narrower chokepoint — it also
covers manual, scripted, and subagent callers on machines where the hook is not
installed, and it can see the resolved attachments, which a bash command line
cannot reliably be parsed for.

Enforcement is two steps. The tier is decided and a read-only check runs
**before** credentials are resolved, so a call that is going to be refused is
refused without doing any work first. The single-use token is then spent at the
last moment before the first irreversible step — after the credential command,
the client, and the run directory, all of which can fail for free. That
ordering exists because the first version spent the token before credentials,
so a key command that timed out on a biometric prompt burned the user's
approval on a call that sent nothing. Either step can refuse, both record
`expensive-refused`, and neither can be reached after an upload.

**What this does and does not do.** The authorization is a local file. Anything
holding Bash or Write can fabricate one, and clearing the Claude Code session
and agent-marker environment variables makes a caller look like a human at a
terminal. This is not a defence against a
determined agent and does not claim to be.

It is, however, hardened against the *other* local account it shares `/tmp`
with, which is a different threat and a reachable one. The token is written
under `$TMPDIR` — a shared `/tmp` on Linux when that is unset — and `mkdir -p`
succeeds against a directory someone else created first, at which point the
`chmod 700` fails and, before 0.12.0, was ignored. Both halves now refuse a
state root they do not own: the hook will not mint into one, the CLI will not
read a token from one, symlinks are rejected without following them, and
`doctor` reports the condition rather than leaving it as another silent
refusal. A session id that is not a plain identifier is refused for the same
reason — it is interpolated into that path by both halves. What it guarantees is that nothing
on the *normal, helpful* path spends at scale: an eager agent that would gladly
upload the whole recording now has to be told to, by a human, in a way it
cannot arrange for itself. An eager agent is the realistic failure mode, not a
hostile one.

Turn it off, or retune it, per project:

```toml
[authorization]
# required = false             # back to the permission prompt alone
max_unauthorized_tokens = 5000 # gate more aggressively
ttl_seconds = 600
```

`gemini-bridge doctor` reports whether the gate is on, what it costs to cross,
the session it resolved, and whether an authorization is currently held. It
also flags the two ways the gate breaks invisibly: `jq` missing (the hook mints
nothing, so every expensive call is refused with no way to approve it) and an
agent session whose id cannot be read (the gate refuses rather than standing
down — the direction that matters).

`ledger.jsonl` records an `authorization_tier` per call:

| Value | Meaning |
|---|---|
| `cheap` | under every threshold; never gated |
| `expensive-authorized` | gated, and a user-typed command approved it |
| `expensive-refused` | gated and refused; nothing was sent |
| `expensive-gate-disabled` | would have been gated, but the project turned the gate off |
| `expensive-ungated` | not an agent session, so treated as a direct human invocation |
| `unknown` | a row written by a caller that did not say |

Refusals are recorded too, under `run_id: "(refused)"` with no run directory —
a gate whose audit trail shows only the spends it allowed cannot show an agent
repeatedly trying to spend more than it may.

## What gets checked before anything is sent

Two guards, both on by default, because a call cannot be recalled — the API's
delete endpoint returns 501, so the only cleanups are the project retention
window and a project-wide bulk delete in the console.

**Every file named on the command line** is matched against a built-in pattern
set covering shapes that are secrets or nothing (`*.pem`, `id_rsa`, `.env`,
`.ssh`, and similar), plus anything you add. Matching is case-insensitive,
expands home-relative and environment-variable prefixes in your patterns, and
runs on the raw arguments before any file is opened. It is designed to
over-block rather than under-block.

That means `-f` and `-c` **and** `--prompt-file`, `--system-file` and
`--schema-file`. The last three also read a local file and put its contents
straight into the request, and until 0.12.0 they were not checked: `-f .env`
was refused while `--prompt-file .env` sent the same bytes as the question. A
guard that depends on which flag was typed protects the flag, not the file.

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
sits beside it holding Files API handles; it is what makes a re-asked question
skip the upload, and what lets `uploads --delete` name a file after the run
directory that created it is gone. Handles are *matched* on a content hash and
*keyed* by handle name — one set of bytes can have more than one live handle,
and keying by hash meant a second upload silently erased the first one's name
while its bytes were still at Google.

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
