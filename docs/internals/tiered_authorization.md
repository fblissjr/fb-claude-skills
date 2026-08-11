last updated: 2026-08-01

# Tiered authorization for expensive and external calls

> Verified against the official hooks reference on 2026-08-01 by fetching
> `https://code.claude.com/docs/en/hooks.md` (the raw markdown — the rendered
> page truncates, and a summarizing fetch silently loses the sections that
> matter). Quotes below are verbatim from that file.
>
> Applies to `gemini-bridge` — SHIPPED as of gemini-bridge 0.11.0 through
> 0.15.1 (UserPromptExpansion minting, CLI enforcement, single-use ceiling
> tokens, and a cumulative session cap the proposal below does not describe;
> the shipped shape also drops this document's `--json`/USD estimates). The
> code, its README, and the SKILL.md are the authority on current behaviour;
> from here down this is the design record that preceded them. Generalizes to
> any plugin that spends money or sends data off-machine. Companion to
> [gemini_bridge_design.md](gemini_bridge_design.md).

## The problem

Two requirements that pull in opposite directions:

- **Ergonomics.** "Have Gemini describe this video" should work without typing
  a command, and a delegated subagent should be able to reach the cheap path.
  `disable-model-invocation: true` forecloses both. Its documented effects are
  broader than "you must type the command":
  - "Set to `true` to prevent Claude from automatically loading this skill...
    Also prevents the skill from being preloaded into subagents."
  - "You can't preload skills that set `disable-model-invocation: true`, since
    preloading draws from the same set of skills Claude can invoke."
  - As of v2.1.196 it also "prevents the skill from running when a scheduled
    task fires with the skill as its prompt."

  A subagent holding the `Skill` tool can still *discover* project, user, and
  plugin skills — but the flag disables model invocation universally, so it
  cannot invoke this one. Net effect matches the original concern; the mechanism
  is the universal flag, not the absence of a keyboard.
- **Control.** Nothing expensive, and nothing that hands Gemini a loop on the
  local filesystem, should happen because a model judged it a good idea.

Treating this as one binary — model-invocable or not — forces a bad trade. The
capabilities differ by three or four orders of magnitude in cost and blast
radius. They deserve different gates.

## Mechanism inventory (verified)

Claude Code exposes 30 hook events. Four are relevant here.

### UserPromptExpansion — the provenance primitive

> "Runs when a user-typed command expands into a prompt before reaching Claude.
> Use this to block specific commands from direct invocation, inject context for
> a particular skill, or log which commands users invoke. For example, a hook
> matching `deploy` can block `/deploy` unless an approval file is present."

And the property the whole pattern rests on, stated upstream verbatim:

> "This event covers the path `PreToolUse` doesn't: a `PreToolUse` hook matching
> the `Skill` tool fires only when Claude calls the tool, but typing
> `/skillname` directly bypasses `PreToolUse`. `UserPromptExpansion` fires on
> that direct path."

So the two invocation paths are distinguishable at the harness level:

| Path | Event that fires |
|---|---|
| Claude invokes a skill on its own judgment | `PreToolUse` on the `Skill` tool |
| A human types `/skillname` | `UserPromptExpansion` |

Matches on `command_name`. Payload carries `expansion_type` (`slash_command` or
`mcp_prompt`), `command_name`, `command_args`, `command_source`, the original
`prompt`, plus `session_id`, `cwd`, and `permission_mode`.

Note that the approval-file pattern is not a workaround someone invented — it is
the documented example for this event.

### PreToolUse — the policy gate

Returns inside `hookSpecificOutput`:

| Field | Behavior |
|---|---|
| `permissionDecision` | `allow` / `deny` / `ask` / `defer` |
| `permissionDecisionReason` | for `deny`, **shown to Claude**; for `allow`/`ask`, shown to the user but not Claude; for `defer`, ignored |
| `updatedInput` | replaces the entire input object before execution |
| `additionalContext` | added to Claude's context alongside the tool result |

Three properties worth designing around:

- **Silence is not approval.** "Exit code 0 with no output means the hook has no
  decision to report... The hook can deny the call, but staying silent doesn't
  approve it." Fail-open on hook error, and the normal permission flow still
  runs.
- **The settings layer still wins.** "Deny and ask rules are still evaluated
  regardless of what the hook returns." A hook returning `allow` cannot override
  a user's `deny`/`ask` rule in `settings.json`.
- **Multi-hook precedence is `deny` > `defer` > `ask` > `allow`.** Several
  independent hooks can vote and the strictest wins, so a tiered gate can be
  composed from small single-purpose hooks rather than one branching monster.

### `defer` — not usable here

Multiple third-party write-ups describe `defer` as the primitive for "external
approval workflows before executing costly operations." **That is wrong for
interactive Claude Code.** Upstream:

> "`defer` is for integrations that run `claude -p` as a subprocess and read its
> JSON output, such as an Agent SDK app or a custom UI built on top of Claude
> Code... Claude Code honors this value only in non-interactive mode with the
> `-p` flag. **In interactive sessions it logs a warning and ignores the hook
> result.**"

It also "only works when Claude makes a single tool call in the turn." If Claude
batches calls, `defer` is ignored with a warning.

So `defer` is for SDK-embedded apps that own their own UI. Do not build the
gemini gate on it. Worth recording because the incorrect version is what surfaces
first in search results.

### PermissionRequest — the subagent path

> "Runs when Claude Code is about to ask you for permission. In sessions that
> can't show a prompt, such as background subagents in non-interactive mode,
> Claude Code still runs these hooks, and **if no hook returns a decision, it
> denies the tool call.**"

This is the most useful thing found in the whole investigation, and it inverts
part of the earlier reasoning.

A subagent that hits a permission prompt in non-interactive mode is
**default-denied**. So the concern that drove the model-invocable decision — "a
slash-only skill locks subagents out" — is only half the story. Subagents are
already locked out of anything that would prompt, unless a `PermissionRequest`
hook explicitly decides on their behalf.

That makes `PermissionRequest` the correct place to express "subagents may make
cheap Gemini calls, and only cheap ones," rather than trying to encode it in
skill frontmatter.

## What advisor does today

`skills/advisor` is this repo's existing implementation of the pattern, and it
chose maximum strictness:

1. `disable-model-invocation: true` — the skill never enters context on Claude's
   judgment.
2. A `UserPromptExpansion` hook matching `advisor` mints a spend authorization.
   It is the only place one is created. Gated on
   `expansion_type == "slash_command"`, re-checks `command_name` in case the
   matcher is misconfigured, and skips housekeeping args (`install`, `config`,
   `status`) that spend nothing.
3. A `PreToolUse` hook on `Agent|Task|Skill|Write|Edit|MultiEdit` denies any
   spawn whose authorization is missing, expired, lacking user-typed provenance,
   or naming a different model.

Two design details worth copying:

- **The mint moved out of a Bash script.** It used to live in
  `prepare-consult.sh`, "which was wrong: that script runs under Bash, so the
  agent could mint its own authorization and satisfy the gate it was supposed to
  be constrained by." A gate the gated party can operate is not a gate. Any
  authorization must originate in an event the main loop cannot reach.
- **The stated threat model.** From the script's own comments: "this raises the
  bar, it does not make forgery impossible. The authorization is a file, and
  anything holding Bash or Write can fabricate one. What it guarantees is that
  nothing on the *normal, helpful* path creates one — which is the actual threat
  here. **An eager agent is the risk, not a hostile one.**"

That last line is the correct frame. These gates are not a security boundary.
An agent with shell access can always defeat them. They exist to ensure that the
helpful, plausible, well-intentioned path never spends your money without you.

For reference, the first-party `claude-security` plugin also uses
`UserPromptExpansion`, but only as a display-only banner — a sensor, not a gate.
Advisor is the more developed example.

## Proposed tiering for gemini-bridge

Three tiers, split by cost and blast radius rather than by modality.

| Tier | Examples | Gate |
|---|---|---|
| **Cheap read** | a few images, no thinking budget, no tools, under a token/dollar threshold | Ordinary Bash permission prompt. `PermissionRequest` hook may auto-allow for subagents. |
| **Expensive read** | video, `thinking: high`, `store=true`, anything over the threshold | `PreToolUse` returns `ask` with the cost estimate in the reason. Denied outright for subagents. |
| **Loop** | `--tools` local function calling — Gemini driving execution on the machine | Requires an advisor-style authorization minted only by `UserPromptExpansion` on a user-typed command. `PreToolUse` denies otherwise. Never allowlisted. |

The skill stays model-invocable, so natural language works and subagents reach
tier 1. The gates live in the harness, where they are enforced rather than
requested.

### Why classification belongs in the CLI, not the hook

The hook should not re-implement cost estimation by parsing a command line. Give
the CLI a classification mode:

```
gemini-bridge classify --json <same args>   # → {"tier": "expensive_read", "est_tokens": ..., "est_usd": ...}
```

The `PreToolUse` hook shells out to that and maps the tier to a decision. One
implementation of the cost model, used by `--dry-run`, by the hook, and by the
budget cap. No copy that can drift — the criterion from invariant 1b.

Note this means the hook trusts the CLI, and the CLI is on disk. That is fine
under the stated threat model: an eager agent will not rewrite the classifier to
lie to the gate; a hostile one could, and could equally just call the API
directly with `curl`.

### Composition detail

Because precedence is `deny` > `defer` > `ask` > `allow`, the three tiers can be
three small hooks that each answer one question, rather than one script with
nested conditionals. The strictest answer wins automatically. Easier to test,
easier to disable one layer without touching the others.

### `permissionDecisionReason` is a channel to Claude

On `deny` the reason is shown to Claude, not the user. Use it. A denial that
says "tier 3 requires a user-typed `/gemini --tools`; ask the user to run it"
turns a dead end into a correct next action. On `ask` the reason goes to the
user instead, so that is where the cost estimate belongs.

## Does Opus 5 change the calculus?

The public guidance around the Opus 5 release argues *for* structural gates, not
against them. The consistent framing is that a more proactive model hands more
judgment to the model, and that "with clear goals and human review of output,
that's leverage; without them, it's a confident agent acting on your behalf with
less oversight than you may think."

Applied here: a more capable model is *more* likely to correctly identify that a
Gemini call would help, and therefore more likely to make one. Capability raises
the frequency of the eager-path failure rather than lowering it. The gate earns
its place more, not less.

The counter-argument — "a better model can be trusted to judge when the spend is
warranted" — fails on a specific point: the model does not know your budget, your
data-sharing constraints, or whether this particular video is something you want
sitting on Google's servers for 55 days. Those are not capability questions.

## Honest limits

- **Not a security boundary.** Anything with `Bash` or `Write` can forge an
  authorization file. See advisor's own comment. These gates constrain the
  helpful path.
- **Hook failure is fail-open.** A hook that errors or times out returns no
  decision, and the call proceeds through the normal permission flow. Depend on
  the CLI's own budget cap as the layer that does not require a hook to have run.
- **`updatedInput` is a sharper tool than it looks.** A hook can rewrite the
  command — e.g. force `--media-resolution low` on a subagent call — rather than
  denying it. Powerful, and confusing when someone later reads the transcript and
  sees a command they did not compose. If used, `additionalContext` should say so.
- **One claim still unverified after a dedicated search.** Several third-party
  posts state that PreToolUse hooks run before permission-*mode* checks, so a
  `deny` blocks even under `bypassPermissions` / `--dangerously-skip-permissions`.
  Neither the hooks page nor the permissions page addresses it. What the docs
  *do* say, verbatim:

  > "When Claude Code makes a tool call, PreToolUse hooks run before the
  > permission prompt, for every tool except EndConversation."

  > "A blocking hook also takes precedence over allow rules. A hook that exits
  > with code 2 stops the tool call before permission rules are evaluated, so
  > the block applies even when an allow rule would otherwise let the call
  > proceed."

  Both are about the *prompt* and about *allow rules* — not about permission
  modes, whose entire purpose is to skip prompts. The adjacent statements read
  like an answer and are not one. Do not rely on the blog claim.

  Worth noting separately: **exit code 2 is a distinct blocking mechanism** from
  `permissionDecision: "deny"`, and it is documented as stopping the call
  *before permission rules are evaluated*. If a hard block is ever needed, that
  is the stronger primitive.

## Recommendation

Keep the skill model-invocable. Put the gates in hooks, tiered by cost and blast
radius, with classification delegated to the CLI so there is one cost model.
Reserve the advisor-style minted authorization for the local function-calling
loop, which is the only tier where Gemini drives execution on the machine.

This is a revision of the flat "model-invocable, rely on the Bash prompt"
decision recorded in `gemini_bridge_design.md`. That decision was made before
`PermissionRequest`'s subagent default-deny behavior was known, which is the
fact that most changes the picture.

## Sources

- [Hooks reference](https://code.claude.com/docs/en/hooks) — fetch
  `https://code.claude.com/docs/en/hooks.md` for the untruncated version
- `skills/advisor/hooks/` — this repo's working implementation
- `coderef/claude-plugins-official/plugins/claude-security/hooks/hooks.json` —
  first-party `UserPromptExpansion` use (display-only)
- [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)
