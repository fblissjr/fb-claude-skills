last updated: 2026-08-03

# Plugin patterns

How plugins in this repo are structured, how their components compose, and the conventions that make them work across surfaces.

## Required structure

```
plugin-name/
  .claude-plugin/
    plugin.json            # name, version, description, author, repository
  README.md                # last updated date, installation, skills table
  skills/
    skill-name/
      SKILL.md             # frontmatter: name, description, metadata.last_verified (no author/version -- context-loaded on activation)
  hooks/                   # optional: SessionStart/PreToolUse hooks
    hooks.json             # hook registration (event -> command)
    session-start.sh       # detection logic + directive assembly
    directives/            # composable directive files (# trigger: <signal>)
  agents/                  # optional: agent .md files
  references/              # optional: supporting docs loaded on demand
```

Components in default directories (`skills/`, `agents/`) are auto-discovered. Don't list them in `plugin.json`.


## Hooks vs. skills (the directive distinction)

- **Hooks inject behavioral directives** — what to do, when to do it. Loaded automatically when the event fires.
- **Skills provide reference material** — how to do it in detail. On-demand only; load when triggered by keywords or explicit invocation.

Rule of thumb: if something must always be active when a project matches certain markers, it belongs in a hook directive. Skills are for the deep-dive content the model pulls in when the work calls for it.

## Composable directive pattern

Each plugin with behavioral content has a `hooks/` directory with:

- `hooks.json` — event-to-command registration
- `session-start.sh` — detection logic + directive assembly
- `directives/*.md` — composable directive files, each declaring `# trigger: <signal>` on line 1. As of dev-conventions 0.15.0 a directive may also declare `# ground: <ERE>` on line 2 — the hook greps that pattern across the repo's own conventions surfaces (root CLAUDE.md, `.claude/rules/*.md`, config `rules[]`) and silences the block where covered, per block. Shipped directives must declare ground; a missing line fails open to broadcast so custom directives keep working.

Adding a new convention = dropping a `.md` file in `directives/`. No shell editing.

Detection logic in `session-start.sh` orders cheap checks (file/dir stat) before expensive checks (grep) and emits matched directives concatenated. Signals are plugin-specific:

- `dev-conventions`: `python`, `typescript`, `tdd`, `docs`
- `path-privacy`: emitted unconditionally inside any git repo
- `dimensional-modeling`: `duckdb`
- `mece-decomposer`: `agent-sdk`
- `env-forge`: `envforge`

Plugins using this pattern: `dev-conventions`, `dimensional-modeling`, `mece-decomposer`, `env-forge`, `path-privacy`.

## Scaffolder, not broadcaster

First instance shipped 2026-08-03 (dev-conventions 0.15.0); the pattern is
provisional until a second plugin adopts it or fleet evidence lands (a
consumer repo's pre-registered measurement reports 2026-08-24).

Broadcast prose has four structural friction properties: generic by necessity
(so it states forms, which collide with mature local practice), paid every
session, unownable by the repo (mute is rent reduction on a two-party
structure, not dissolution), and coupled to plugin updates. The inversion,
for any plugin whose value is "inject conventions":

1. **Enforce facts centrally** — mechanical rules stay hooks, updated by the
   plugin, zero ambient cost. This is the one tier where central updates are
   correct.
2. **Scaffold preferences locally** — an init skill writes tailored
   convention lines into the repo's own files, once. The load-bearing fact:
   scaffolded text reaches every collaborator's Claude through normal context
   loading; broadcast only ever reached installers.
3. **Silence by ground coverage, per block** — each directive declares its
   ground pattern; the hook stays quiet exactly where the repo's own files
   cover it. Per block, not per file-existence: an architecture-only
   CLAUDE.md covers nothing and silences nothing.
4. **The remaining ambient tier trends toward one self-extinguishing
   pointer** for repos with no conventions at all (deliberately not yet
   shipped — gated on the consumer-repo evidence).

Candidates when next touched: `dimensional-modeling`, `mece-decomposer` —
both disabled in this repo for exactly the broadcast reason.

Ground-pattern limits, measured by the first consumer report (2026-08-03),
and what shipped against them in 0.15.2 the same day. The founding specimen
pair: a bare package-manager token in a tooling list ("Tooling: bun,
three@0.185.1 + playwright-core@1.61.1 (both pinned)") is a genuine
declaration that matches nothing, while a fenced command invocation
("bun run <script> --parity-only") matched despite being an example, not a
rule. The verdict on that specimen settled in three steps, worth keeping because
each was a measurement: first "right verdict, wrong line read" (recorded
here); then the consumer's correction — the trigger gate short-circuits
coverage, so the coverage verdict was moot on any clone and, on the one
machine where it ran, rested on a bogus line; then their own partial
walk-back — the block is manifest-management advice and that repo has no
root manifest (bun as runtime, not as package), so the *outcome* was
defensible even though the *mechanism* was wrong. The durable sentence:
judge the gate and the outcome separately — a control can be right for a
bogus reason, and both facts belong in the record.

What shipped against it: **fence-stripping** (coverage greps prose only —
the rule-vs-command discriminator is positional, not lexical; the strip can
only remove coverage, erring toward the recoverable direction), **force
overrides both gates** (a trigger miss from gitignored/deep markers was the
second unrecoverable silence; force originally recovered only coverage),
and **`--explain`** (three byte-identical causes of silence, now narrated
per directive with the matched line — this is also the specimen-accumulation
instrument: without it every specimen costs a manual `bash -x` dig, so any
"tune after N specimens" trigger stays unreachable by construction). New
specimens go into `test_token_mentions_do_not_silence`'s parametrize list —
that test IS the specimen file.

A second specimen was raised and withdrawn the same evening, and the
withdrawal is the part worth keeping. The claim: the two hooks disagree
about whether a mixed-language repo "is JS" (SessionStart's deep marker
scan said yes via a gitignored fixture; the PreToolUse guard, tested from
repo root, did not block npm). Measured properly — running the guard with
cwd *inside* the fixture — the guard blocked npm and yarn there and allowed
them at root: it walks up from cwd and resolves the managing lockfile
per directory. The hooks ask different questions with different consequence
profiles, and both scopes are correct: presence-of-language scans down
(prose tier, cheap to be wrong), evidence-of-manager-choice walks up from
the action (enforcement tier, expensive to be wrong). The reasoning hygiene
that survives: trigger-vs-coverage and detection-vs-enforcement are
non-interchangeable gates, and "tested from the wrong cwd" produced a
confident false inconsistency. One noted limit stands, prose tier only:
SessionStart marker detection sees gitignored files, so a directive trigger
can be true on one machine and false on every clone — bounded blast radius
(a few coverage-gated lines on the machine where the fixture exists), noted
rather than filed as a defect.

The strategic step, filed for the 0.16.0 round alongside the bare-repo
pointer: the regex is lossy inference of a fact `/dev-conventions:init`
could simply record. Init knows exactly what it wrote — have it declare
coverage in `.dev-conventions.json` (tracked, so the declaration travels
like the scaffolded prose), and the regex demotes to a fallback for repos
that wrote their rules by hand, where `--explain` is what makes it
debuggable.

## Agent vs. skill

- **Skill** (in `skills/<name>/SKILL.md`): static reference. Loads when the description matches the user's intent. Read by the model in the main session.
- **Agent** (in `agents/<name>.md`): a forked subagent. Runs in its own context with its own tool budget. Used when the work is bookkeeping the main session shouldn't be doing — log drafting, isolated reviews, fan-out research.

Agents have their own `metadata.version` independent of the plugin version. Bump the agent's version when its content changes; the plugin version bumps too because agents count as plugin content.

When designing an agent, deduplicate against existing skills and global rules — don't restate doc-conventions, language tooling rules, or path-privacy in the agent body. Reference them.

## Catalog-as-exemplar

When generating new artifacts, first search existing catalogs for structurally similar examples. Use the closest match as a few-shot reference — adapt patterns, don't copy verbatim. The `env-forge:forge` skill's step 2 documents this for environment generation; the principle applies to any new SKILL.md, hook, or directive.

## Hook invocation: exec form

Every plugin hook in this repo runs a bundled `.sh` and therefore references
`${CLAUDE_PLUGIN_ROOT}`. All of them use **exec form**:

```json
{
  "type": "command",
  "command": "bash",
  "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/<plugin>-session-start.sh"]
}
```

Not shell form (`"command": "${CLAUDE_PLUGIN_ROOT}/hooks/<plugin>-session-start.sh"` with
no `args`). Shell form hands the whole string to `sh -c`, so a plugin root
containing a space — a user account named `First Last`, for instance — splits at
the space and the hook dies with `sh: /Users/First: No such file or directory`.  <!-- path-privacy: ignore -->
Exec form passes each `args` element as exactly one argument, no shell, no
quoting rules.

Name `bash` as the `command` and put the script path in `args`, rather than
making the script path the `command`. A `.sh` file is not a spawnable executable
on Windows; naming the interpreter works everywhere. The upstream docs make the
same point with `node`.

Keep shell form only where you genuinely need pipes, `&&`, redirects, or globs.

### `timeout` is in seconds, and its failure mode is undocumented

`"timeout": 3000` is fifty minutes, not three seconds. Both hooks in this repo
that set the field had it wrong from the day they were written — `path-privacy`
at 3000 and `pyright-autoconfig` at 5000 — and it survived review, a version
cascade, and an exec-form conversion before anyone noticed. Milliseconds are the
instinct from every other JS API here, which is why the unit needs stating.

Note the upstream default is **600 seconds** for `command`, `http`, and
`mcp_tool`. So 3000 was five times the default, not a wild outlier — which is
part of why it read as plausible for so long.

**What happens when a command hook times out is not documented.** Be careful
here; we got this wrong once already by generalizing from an adjacent section.
Only two timeout behaviours are stated anywhere on
<https://code.claude.com/docs/en/hooks>, and neither is about command hooks.
Both are quoted verbatim so the next person can check them without trusting a
line number into a snapshot we do not keep:

- Under the **HTTP hook** fields: *"Error handling differs from command hooks:
  non-2xx responses, connection failures, and timeouts all produce non-blocking
  errors that allow execution to continue."* Fails open — but the same section
  says HTTP hooks "use HTTP status codes and response bodies instead of exit
  codes", so it does not transfer.
- Under **`### PreToolUse`**: *"An Agent SDK callback hook on `PreToolUse` that
  exceeds its timeout blocks the tool call, and Claude receives an error result
  naming the timeout."* Fails closed — but an Agent SDK callback hook is a
  different mechanism from a `command` hook in `hooks.json`, so this is the same
  event, not the same surface. It is weak evidence, not an analogy.

For a `command` hook, upstream says nothing. Treat it as unknown.

Two notes on checking this yourself.

**A summary cannot establish absence.** For any claim of the form "the docs do
not say X", a summarising fetch can never be the source, because absence is
precisely what summarisation discards — its silence is not evidence. This is not
a caveat about large pages; it is categorical. A grep answers the question, a
summary cannot. Both sides of this exchange got it wrong the same way on the same
day: one query against the 230KB hooks page returned "not stated for any hook
type" for a sentence that appears three times in the raw text. Use
`skill-maintain upstream` and grep the snapshot.

**Quote sentences, not line numbers.** The snapshots are gitignored and renumber
on every fetch, so a line citation is unverifiable by exactly the person who most
needs to check it.

**Choose the value so that the unknown does not matter.** Cross the two
possibilities with too-short and too-long:

| | too short | too long |
|---|---|---|
| **fails open** | silent bypass — the gate skips, the write proceeds, no message | visible stall |
| **fails closed** | spurious block — annoying, but loud and obvious | visible stall |

Only one cell is catastrophic, and it is the silent one. Every other outcome
announces itself and gets fixed. So for a hook that gates anything, **err long**:
a stall is recoverable, a silent bypass is a leaked path nobody sees.

`path-privacy`'s `PreToolUse` scan measures 0.25s against a deliberately extreme
1.4MB, 20,000-line payload. It is set to **30s** — roughly 120x headroom, still
fast enough to diagnose inside one turn, and 20x below upstream's own default.
The earlier value of 3s was 12x headroom measured warm, which compresses under
load and shell startup, and it bet on a failure mode we cannot actually confirm.

`pyright-autoconfig` is set to 5s on 0.03s of work, and deliberately stays tight:
it gates nothing, so it has no silent-bypass mode, and its only real risk is
stalling session start. Different risk profile, different value.

### The same rule applies inside plugin scripts

This is not a `hooks.json` rule. It is a rule about spawning subprocesses with
interpolated paths, and it applies anywhere a plugin does that — most often
`execSync` in a bundled Node or Bun script:

```js
// wrong: goes through a shell, so a path with a space splits into two arguments
execSync(`bun run ${scriptPath} ${sceneFile}`);

// right: no shell, each element is exactly one argument
execFileSync('bun', ['run', scriptPath, sceneFile], { stdio: 'inherit' });
```

`execSync` and `exec` run their whole string through `/bin/sh`. `execFileSync`
and `spawnSync` with an argument array do not. Same failure, same fix, one layer
down: `${CLAUDE_PLUGIN_ROOT}` and any user-supplied filename can contain spaces,
and a filename can additionally contain `;`, `$`, backticks, and quotes — which
a shell will happily interpret.

Quoting the interpolation (`"${path}"`) papers over the space case and leaves
the metacharacter case. Prefer the array form; reach for a shell only when you
actually need shell features, and then quote deliberately.

Two related traps in the same family, both worth checking when you write one of
these scripts:

- **A glob in the command is expanded by the shell, not by your program.** That
  caps how many paths can be passed before hitting `ARG_MAX`, and the limit is
  reached quietly at a few thousand entries. If you are passing a frame sequence
  or similar, pass a pattern the tool itself understands, or feed a file list.
- **Derived outputs must not write into a source directory.** A step that
  regenerates `frames/` to build a preview will destroy the frames an expensive
  full render produced. Give the derived step its own output directory.

## Bash 3.2 portability

Plugin scripts use `#!/usr/bin/env bash` and may run on macOS system bash (3.2). Avoid bash 4+ features:

- `mapfile` / `readarray` (not available)
- `declare -A` (associative arrays — not available)
- `[[ =~ ]]` when a `case` will do (slower and less portable than `case`)

For per-line file reads use:

```bash
i=0
while IFS= read -r line; do
    arr[$i]="$line"
    i=$((i+1))
done < "$f"
```

The pre-commit hook (jq-based), `regex-scan.sh`, and `find-external-paths.sh` all stick to this subset. New plugin scripts should too.

## Greenfield default for local DBs

For local DuckDB instances (e.g. readwise-reader's), prefer `CREATE OR REPLACE VIEW` + schema re-init on next connection over migration bridges. "OK to drop data, greenfield is fine" is the working default for non-production state.

## Schema evolution: production-facing

The exception to greenfield. `marketplace.json` and any data shape consumed by users of installed plugins needs additive evolution: add fields, don't rename, don't drop. Use the existing version cascade to carry users forward. Applies to MCP tool schemas and any artifact other repos pull from this one.

## Hook anti-patterns

Salvaged from `docs/analysis/hooks_system_patterns.md` before it was deleted on
2026-07-21. Only the items that are environmental, or that we verified
independently, were kept — the rest of that document's claims were unverified
against current upstream and importing them here would have moved the problem
rather than solved it.

- **Mixing exit codes and JSON.** Exit 2 makes Claude Code read stderr and ignore
  stdout entirely. Pick one: exit 2 + stderr to block, or exit 0 + JSON stdout
  for a structured decision. (Verified 2026-07-21: only exit 2 blocks; exit 0
  means "no decision reported" and does *not* approve; exit 1 is a non-blocking
  error despite being the conventional Unix failure code.)
- **Blocking on a non-blockable event.** Exit 2 from `PostToolUse`,
  `SessionStart`, `SessionEnd` or `PreCompact` blocks nothing — the action has
  already happened. The stderr is shown; the action proceeds.
- **Shell profile pollution.** An unconditional `echo` in `<HOME>/.zshrc` prepends to
  hook stdout and breaks JSON parsing. Guard with `if [[ $- == *i* ]]`.
- **Unquoted variable expansions.** `$FILE_PATH` word-splits on paths containing
  spaces. This is the same defect class as shell-form hook commands and as
  `execSync` with an interpolated path — see "Hooks use exec form". It bit this
  repo's own plugin scripts on 2026-07-21.
- **Treating a matcher as a security boundary.** Matchers filter the tool name,
  which is not user-controlled. Tool *inputs* still need validating inside the
  hook.
- **Trusting a diff-scoped check to enforce a whole-tree invariant.** A
  pre-commit hook sees only added lines, so anything predating it survives
  indefinitely. If the rule is about repo *content*, something must audit
  content — `check_path_privacy` exists because five leaked paths survived 157
  days and a full docs triage behind clean diffs.

## Bracket-the-hook

Field-tested in a sibling repo's claims-reminder apparatus (2026-08-03): a hook
that classifies tool calls and speaks or stays silent is itself check-shaped,
so it gets its own control — a small script that pipes synthetic hook payloads
through the real hook binary and asserts on the JSON out. Without one, the hook
is the least-checked artifact in the plugin: correct when written, silently
wrong after the first edit.

The arms that earn their place, each pinning a specific rot mode:

- **A speaks arm per class** — the only proof the hook ever fires at all. Assert
  the message *content* (a regex), not just presence; a hook emitting the wrong
  class's message passes a presence check.
- **The dedup arm** — same payload twice, second must be silent. Record it red
  against a dedup-stripped mutant before trusting it: without that, deleting the
  state-file check leaves every arm green while the hook wallpapers every edit.
- **Edge-pinning silence arms** — payloads just *outside* each class (a tool
  file, a plain command) must stay silent. These go red first when a pattern
  widens by accident. Pin a second path per multi-path class, or accidental
  *narrowing* goes red nowhere.
- **Malformed-stdin arm** — garbage in must produce a clean allow and exit 0. A
  hook that crashes on bad input is worse than one that says nothing.
- **Cited-examples-resolve arm** — if the hook's messages teach from commit shas
  or file paths, assert they still resolve. A reminder citing a dangling example
  reads as archaeology and stops being believed; this is how the control's
  *pedagogy* rots while its logic stays green.
- **State-lifecycle arms** where state exists — e.g. fire, clear (the
  PostCompact path), fire again.

Delivery semantics worth knowing when writing the hook under test (verified
against the 2026-07-21 upstream snapshot): PreToolUse `additionalContext` is
delivered *next to the tool result* — the model reads it one half-step after
the action, not before it. Mid-session injections are replayed verbatim on
`--resume`, not re-run. And compaction can summarize a delivered reminder out
of context while the hook's dedup state survives — pair any once-per-session
reminder with a PostCompact state clear or its second half runs unguarded.

The authoring checklist for the hook itself (header sections, measured FP rate,
retirement trigger, factual-statement phrasing) lives in
`skill-maintainer`'s best-practices reference under "control authoring".

## Per-repo plugin config

A plugin that needs per-repo overrides ships its own root-level
`.<plugin-name>.json`, tracked rather than gitignored, with the shape
`dev-conventions` established:

```json
{ "enforce": { "some-rule": false }, "rules": ["extra house rule"] }
```

Omitted keys mean "default", so the file only ever states exceptions.

**A convention, deliberately not a shared mechanism.** One shared config file
would couple plugins that release independently and force a schema versioned
across all of them, and there is exactly one consumer today. Writing the shape
down is what stops the third plugin inventing a third format — and if three
files ever become genuinely painful, a migration is mechanical because they
already agree on structure.

Root-level rather than under `.claude/`: that directory is Claude Code's
namespace, not the plugin's, and a root dotfile is more discoverable to humans.
