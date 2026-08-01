last updated: 2026-08-01

# gemini-bridge

Hand a multimodal task to a Gemini model when Claude cannot do it directly, and
get a structured answer back — without copy-pasting between two chat windows.

Built for one problem first: comparing two renders of the same scene and
reporting what a person would actually notice. Claude can measure images with
code but cannot reliably see the difference between them; Gemini can.

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
gemini-bridge doctor               # check config, credentials, recipes
```

## Skills

| Skill | Description |
|-------|-------------|
| [gemini-multimodal](skills/gemini-multimodal/SKILL.md) | Route a perceptual task to Gemini, pick a resolution from measured guidance, and read the structured verdict from the run directory. |

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
```

The runs root writes its own `.gitignore` containing `*` on first use, so run
output cannot be committed into your repo by accident. A `ledger.jsonl` beside
it records one line per call — model, recipe, tokens, duration, status — using
only facts the API reported, never a self-assessment.

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
