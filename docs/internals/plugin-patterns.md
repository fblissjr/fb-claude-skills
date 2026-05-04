last updated: 2026-05-04

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
