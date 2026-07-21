last updated: 2026-07-21

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
      SKILL.md             # frontmatter: name, description, metadata.author/version
  hooks/                   # optional: SessionStart/PreToolUse hooks
    hooks.json             # hook registration (event -> command)
    session-start.sh       # detection logic + directive assembly
    directives/            # composable directive files (# trigger: <signal>)
  agents/                  # optional: agent .md files
  references/              # optional: supporting docs loaded on demand
```

Components in default directories (`skills/`, `agents/`) are auto-discovered. Don't list them in `plugin.json`.

For full plugin architecture, schemas, and patterns, see [docs/analysis/plugin_system_architecture.md](../analysis/plugin_system_architecture.md).

## Hooks vs. skills (the directive distinction)

- **Hooks inject behavioral directives** — what to do, when to do it. Loaded automatically when the event fires.
- **Skills provide reference material** — how to do it in detail. On-demand only; load when triggered by keywords or explicit invocation.

Rule of thumb: if something must always be active when a project matches certain markers, it belongs in a hook directive. Skills are for the deep-dive content the model pulls in when the work calls for it.

## Composable directive pattern

Each plugin with behavioral content has a `hooks/` directory with:

- `hooks.json` — event-to-command registration
- `session-start.sh` — detection logic + directive assembly
- `directives/*.md` — composable directive files, each declaring `# trigger: <signal>` on line 1

Adding a new convention = dropping a `.md` file in `directives/`. No shell editing.

Detection logic in `session-start.sh` orders cheap checks (file/dir stat) before expensive checks (grep) and emits matched directives concatenated. Signals are plugin-specific:

- `dev-conventions`: `python`, `typescript`, `tdd`, `docs`
- `path-privacy`: emitted unconditionally inside any git repo
- `dimensional-modeling`: `duckdb`
- `mece-decomposer`: `agent-sdk`
- `env-forge`: `envforge`

Plugins using this pattern: `dev-conventions`, `tui-design`, `dimensional-modeling`, `mece-decomposer`, `env-forge`, `path-privacy`.

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
  "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"]
}
```

Not shell form (`"command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"` with
no `args`). Shell form hands the whole string to `sh -c`, so a plugin root
containing a space — a user account named `First Last`, for instance — splits at
the space and the hook dies with `sh: /Users/First: No such file or directory`.
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

Two notes on checking this yourself. A summarising fetch of the page may report
that neither sentence exists — the page is over 230KB and a single sentence is
easy to lose in summarisation; grep the raw text instead, via
`skill-maintain upstream`. And quote sentences, not line numbers: the snapshots
are gitignored and renumber on every fetch, which makes a line citation
unverifiable by exactly the person who most needs to check it.

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

For local DuckDB instances under `<HOME>/.claude/` (e.g., `agent_state.duckdb`) or per-app (e.g., readwise-reader's), prefer `CREATE OR REPLACE VIEW` + schema re-init on next connection over migration bridges. "OK to drop data, greenfield is fine" is the working default for non-production state.

## Schema evolution: production-facing

The exception to greenfield. `marketplace.json` and any data shape consumed by users of installed plugins needs additive evolution: add fields, don't rename, don't drop. Use the existing version cascade to carry users forward. Applies to MCP tool schemas, agent-state tables exposed by `agent-state-mcp`, and any artifact other repos pull from this one.
