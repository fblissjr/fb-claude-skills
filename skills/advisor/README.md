last updated: 2026-08-01

# advisor

Consult a higher-tier model about what the current session is doing.

This emulates the Claude API's [advisor tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
inside Claude Code, with one deliberate inversion: **the user decides when to
spend, not the model.**

## The problem it solves

The API advisor pairs a fast executor with a stronger advisor that reads the
full transcript mid-generation and returns a plan. Claude Code cannot do that
directly. Its `Agent` tool forces a choice:

- `subagent_type: "fork"` inherits your full context — but ignores the model
  override, so the consultant is the same model you already are.
- Any other subagent takes a model override — but starts with an empty context
  and knows nothing about your session.

Neither gives a stronger model that has seen your work. This plugin bridges
that by reconstructing the session from its transcript on disk into a bounded
digest, then handing that to a model tier you name.

## Nothing spawns without you

The advisor runs on frontier-tier models, so the design question that matters is
not "does it ask nicely" but **where the authorization to spend is created.**

It is created in a `UserPromptExpansion` hook, which fires only when a
user-typed command expands into a prompt. Claude cannot reach that event: when
Claude invokes a skill it goes through the `Skill` tool, and typing `/advisor`
does not. That asymmetry is what the guarantee rests on — not on the model
choosing to comply.

| Job | Mechanism | Spends |
|---|---|---|
| Mint the authorization | `UserPromptExpansion`, only on a typed `/advisor` | Nothing |
| Spawn the advisor | The skill, once, with your parameters | Yes, only here |
| Refuse model-invoked skill loads | `disable-model-invocation` + `PreToolUse` on `Skill` | Nothing |
| Deny unauthorized spawns | `PreToolUse` on `Agent` | Nothing |
| Pre-write checkpoint (opt-in, off) | `PreToolUse` on `Write`/`Edit` | Nothing |

Every hook job is detection and refusal. None can spawn a model. Authorizations
are one-shot, expire in five minutes, carry `origin: user_typed_command`, and
record the tier you typed — the spawn gate rejects a mismatch, so "approve
sonnet, spawn fable" is not reachable. The bounds you type are captured at mint
time, so nothing downstream can substitute a different value.

**The honest limit.** The authorization is a file. Anything holding `Write` or
`Bash` can fabricate one. This is defense against an *eager* agent — the actual
risk here — not against a hostile one, and no file-based scheme can promise the
latter. What it does guarantee is that nothing on the normal, helpful path
creates one.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install advisor@fb-claude-skills
```

Requires `jq` (hooks fail open without it) and `uv` (runs the digest script).

## Skills

| Skill | Invocation | What it does |
|---|---|---|
| `advisor` | `/advisor` | Runs one authorized consult, or installs and configures the project rule and checkpoint |

## Invocation examples

```
/advisor
/advisor --model fable --words 150
/advisor --max-chars 20000
/advisor is the digest budget the right place to spend context here?
/advisor install
```

Plain-language triggers deliberately do **not** work. The skill sets
`disable-model-invocation: true`, so its description is never in Claude's
context and "ask the advisor" will not load it. Asking Claude for a second
opinion gets you a suggestion that you run `/advisor`, not a consult. That is
the point: if natural language could trigger it, the spend would be one
ambiguous phrasing away.

## Components

| Path | Role |
|---|---|
| `skills/advisor/SKILL.md` | The `/advisor` command. The only path that spawns anything |
| `skills/advisor/scripts/digest.py` | Transcript JSONL to advisor view, within a character budget |
| `skills/advisor/scripts/prepare-consult.sh` | Validates the authorization and builds the digest. Deliberately cannot create one |
| `skills/advisor/references/advisor-rule.md` | Installable `.claude/rules/advisor.md` |
| `skills/advisor/references/api-advisor-tool.md` | The upstream API feature, and where this departs from it |
| `agents/advisor.md` | The advisor's system prompt and its bounds |
| `hooks/advisor-session-start.sh` | Silently pins the session transcript path |
| `hooks/advisor-user-prompt-expansion.sh` | The only place a spend authorization is minted |
| `hooks/advisor-pre-tool-use.sh` | The spend gate and the optional checkpoint |

## Cost controls

Every lever is explicit; none is inferred.

| Lever | Where | Effect |
|---|---|---|
| `model` | `--model`, verified by the hook | Which tier answers |
| `effort` | `agents/advisor.md` frontmatter | How hard it thinks |
| `maxTurns` | `agents/advisor.md` frontmatter (6) | Hard ceiling on advisor turns |
| `tools` | `agents/advisor.md` frontmatter | Read-only: it can verify, not act |
| `--max-chars` | digest budget, default 40000 | Input size |
| `--words` | soft cap in the prompt, default 250 | Output size |

The digest reports its size in characters and approximate tokens before the
spawn, so the input cost is visible in advance rather than after the fact.

## The checkpoint

Off by default. `.claude/advisor.json`:

```json
{ "checkpoint": "block" }
```

`block` denies the session's first `Write` or `Edit` until a consult is on
record — the "hard rule" from the upstream docs. `warn` notes it without
blocking. Any consult satisfies it permanently.

Leave it off unless you have watched the model skip planning on work that
needed it. Anthropic measured the rule raising Haiku coding pass rates ~7.5pp
while costing ~4pp on retrieval-heavy workloads and pushing Opus to over-call.
It is a real tradeoff.

## Related

[`model-routing`](../model-routing/README.md) is this plugin's mirror image: it
routes *down*, sending well-specified mechanical work to cheaper models in
subagents. The advisor routes *up*, buying a stronger opinion at the moments
where judgment is the expensive part.

They are deliberately separate plugins rather than one, though the original
reason has expired. This section used to argue that `model-routing` must stay
discoverable while this plugin must not, so one plugin could not hold both
settings. On 2026-08-01 `model-routing` paused installation and took
`disable-model-invocation` too, so both are now user-invoked only.

What still separates them is shape and lifecycle. `model-routing` is an
installer: it writes a file and gets out of the way, no runtime footprint. This
plugin is all runtime — hooks on three events, a spend gate, per-session state.
`model-routing` is paused pending measurement; this one tracks a beta upstream
feature and will keep moving.

They also encode opposite policies about who decides: the delegation rule tells
Claude to route downward on its own judgment, while this one forbids acting
without a keystroke. Kept apart, each says one thing clearly.

## What the digest contains, and what it does not filter

The digest is a condensation of your session transcript, and **it is not
filtered for secrets.** Your own messages are deliberately preserved verbatim —
losing a constraint you stated is the failure mode that makes advice actively
harmful — so anything you pasted into the chat is in there at full fidelity. An
API key, a `.env` value a command printed, a customer record, an internal
hostname: if it was in the conversation, it is in the digest.

Two things this does *not* change, worth being precise about:

- **It sends nothing new to the model.** That content already went to Claude when
  you typed it. The advisor is a different model tier, but the same backend, and
  no code here reaches the network on its own.
- **It does create a second copy on disk.** `$TMPDIR/claude-advisor/<session>/digest.md`,
  written `0600` in a `0700` directory, replaced on the next consult, and swept
  after seven days. Before 0.2.1 it inherited the default umask, which meant
  `0644` — a real exposure on Linux, where the `${TMPDIR:-/tmp}` fallback is a
  shared world-readable directory.

If you work with sensitive material and want the payload screened, this repo's
[`scan-for-secrets`](../scan-for-secrets/) plugin detects the relevant shapes and
can be pointed at the digest before you consult. Wiring it in automatically is
deliberately not done — it would couple two plugins and add a scan to every
consult — but the option is there.

Related: the advisor subagent has `Read`, `Grep`, and `Glob`. It can read any
file your session's permissions allow, not only what the digest contains. That
is what lets it verify a claim against the code rather than trusting a
compressed summary, and it is why it has no `Write` and no `Bash`.

## Limitations

- **The digest is lossy.** It is a reconstruction, not the live context window.
  Tool outputs are truncated and long middles compress to one line per call.
  The advisor gets read tools specifically so it can check the record rather
  than trust the summary.
- **The transcript lags.** Claude Code writes it asynchronously, so the newest
  exchange of the current turn may not be on disk when the digest runs.
- **Subagent traffic is excluded** by default. Work delegated to other agents
  shows up as the delegation, not its internals.
- **One authorization, one spawn.** If the `Agent` call is denied at the
  permission prompt after the hook consumed the token, run `/advisor` again.
