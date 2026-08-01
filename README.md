last updated: 2026-07-26

# fb-claude-skills

> **[Design Principles (VISION.md)](VISION.md)** -- Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal. Read this first.

A collection of Claude Code plugins, skills, and MCP Apps. Installable as a plugin marketplace in Claude Code, Cowork, and Claude Desktop.

## plugins

Grouped by purpose: development conventions & authoring, decomposition & model routing, plugin & skill maintenance, MCP servers & apps, privacy & pre-share safety.

### development conventions & authoring

| Plugin | Type | Description |
|--------|------|-------------|
| [dev-conventions](skills/dev-conventions/) | Hooks + Skills | Three tiers: a PreToolUse hook blocks pip in uv projects, npm in bun projects, and lockfile edits; a small SessionStart directive carries only what no hook can enforce; skills hold what Claude cannot derive. Per-repo overrides in a tracked `.dev-conventions.json`. |
| [dimensional-modeling](skills/dimensional-modeling/) | Skill | Kimball-style dimensional modeling for DuckDB star schemas. A skill you invoke when designing a schema -- the SessionStart hook was removed, since the principles are needed at a decision point rather than before every session. |
| [writing](skills/writing/) | Skill | Writing skills for clear, accessible prose. `plain-language-us` — an American plain-language house style (plain English, active voice, front-loaded content, sentence case, no bold for emphasis). `voice-match` — write in the user's own voice, learned from the conversation and a saved profile; overrides the house style where they conflict. Both split into a short body plus `references/`. |
| [postmortem](skills/postmortem/) | Skills | Evidence-grounded retrospectives. `postmortem` — verdicted look-back at a session, feature, or span (git history, session logs, changelogs); every finding cites an artifact, empty sections are valid, annotate-don't-rewrite. Filed as standalone dated files in a per-repo resolved location, optionally rendered to a self-contained HTML file. `postmortem-index` — a generated browsable page over them, answering "has anything been written about this file". `test-audit` — does each green test still mean anything: claim recovery, spot-mutation oracle checks, reachability-envelope mapping, keep/rewrite/delete verdicts. |
| [json-query](skills/json-query/) | Skill | JSON query tool selection and syntax -- jg (jsongrep) for extraction, jq for transformation |
| [pyright-autoconfig](skills/pyright-autoconfig/) | Hook | Points pyright at the project's uv venv automatically, self-heals once `.venv` appears, and retracts its config when the project declares its own `[tool.pyright]` |
| [ruff-diagnostics](skills/ruff-diagnostics/) | Hook | Runs Ruff on each edited Python file and reports findings. A hook rather than an LSP because Claude Code starts only one language server per file extension, so `ruff server` cannot run alongside pyright. Silent on clean files. |

### decomposition & model routing

| Plugin | Type | Description |
|--------|------|-------------|
| [mece-decomposer](apps/mece-decomposer/) | Hook + Skills + MCP App | MECE decomposition of goals and workflows into Agent SDK-ready components, with interactive tree visualizer. Hook detects Agent SDK imports. |
| [model-routing](skills/model-routing/) | Skill | Opt a project into down-tier model delegation: installs a standalone `.claude/rules/model-delegation.md` telling Claude to route well-specified data/coding tasks to a cheaper model in a subagent, keeping judgment-heavy work in the main loop. Optional layers: pre-shaped `fast-executor` / `task-coder` agents, and an `agent-state` feedback loop. Implements VISION.md "route to the cheapest capable model". |
| [advisor](skills/advisor/) | Skill + hooks | Consult a higher-tier advisor model about the current session, emulating the Claude API's advisor tool inside Claude Code. Reconstructs the session transcript into a bounded digest so a stronger model can see what was actually done. Strictly user-invoked: only a typed `/advisor` mints the spend authorization, and hooks deny any spawn without it. Mirror image of `model-routing`. |

### plugin & skill maintenance

| Plugin | Type | Description |
|--------|------|-------------|
| [plugin-toolkit](skills/plugin-toolkit/) | Skills + Agents | Analyze, polish, and manage Claude Code plugins |
| [skill-maintainer](skills/skill-maintainer/) | Skills + Hooks + Agent | Maintenance tools for skill repos: quality, freshness, upstream detection (per-page snapshots + line/char deltas), best practices review, wiki-sanity `lint` (orphans, count drift, link-rot), tracked pre-commit hook scaffolding, `finish-session` workflow, `session-log-drafter` agent, PostToolUse bundled-ref sync, Stop-event session-log nudge |
| [skill-dashboard](apps/skill-dashboard/) | MCP App | Interactive quality dashboard: checks, token budgets, freshness, version alignment |

### MCP servers & apps

| Plugin | Type | Description |
|--------|------|-------------|
| [readwise-reader](apps/readwise-reader/) | MCP Server | Search, save, and surface your Readwise Reader library via MCP with OAuth, DuckDB, and full-text search |
| [agent-state-mcp](apps/agent-state-mcp/) | MCP Server | 18 read-only tools over `<HOME>/.claude/agent_state.duckdb` (runs, watermarks, skill versions, flywheel). Ergonomic MCP replacement for the `agent-state` CLI. Opt-in via `.mcp.json` (enable with `/agent-state-mcp:enable`). |

### privacy & pre-share safety

| Plugin | Type | Description |
|--------|------|-------------|
| [scan-for-secrets](skills/scan-for-secrets/) | Skill + Scripts | Pre-share scanner built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets): literal pass + ripgrep regex pass for leaked secrets and privacy-sensitive paths (your `$HOME`/`$USER`, SSH keys, other users' home paths, emails, IPv4, common API-token shapes). <!-- path-privacy: ignore --> |
| [path-privacy](skills/path-privacy/) | Hook + Skill + Scripts | Enforces a single rule across every artifact: every path written into the repo must be relative to the repo root. SessionStart directive plus pre-commit and commit-msg git hooks that hard-block commits whose staged files, message, or branch name reference anything outside the repo. |

### project-scoped

| Module | Description |
|--------|-------------|
| [heylook-monitor](apps/heylook-monitor/) | MCP App dashboard for heylookitsanllm local LLM server |

### installable as a package (not a Claude plugin)

| Module | Description |
|--------|-------------|
| [skill-maintainer](tools/skill-maintainer/) | `skill-maintain` CLI for validating, monitoring, and maintaining skill repos. Git-installable into any repo. |
| [agent-state](tools/agent-state/) | `agent-state` CLI for DuckDB audit/state tracking of pipeline, agent, and CLI runs. Watermark history, run trees, skill version lineage with routing metadata and lifecycle management, delegation outcome tracking (acceptance rates per model/domain). |

## installation

### from GitHub (recommended)

```bash
# Add the marketplace (once)
/plugin marketplace add fblissjr/fb-claude-skills

# Install individual plugins
/plugin install mece-decomposer@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
/plugin install dev-conventions@fb-claude-skills
/plugin install skill-maintainer@fb-claude-skills
/plugin install readwise-reader@fb-claude-skills
/plugin install agent-state-mcp@fb-claude-skills
/plugin install json-query@fb-claude-skills
/plugin install pyright-autoconfig@fb-claude-skills
/plugin install ruff-diagnostics@fb-claude-skills
/plugin install skill-dashboard@fb-claude-skills
/plugin install scan-for-secrets@fb-claude-skills
/plugin install path-privacy@fb-claude-skills
/plugin install writing@fb-claude-skills
/plugin install model-routing@fb-claude-skills
/plugin install advisor@fb-claude-skills
/plugin install postmortem@fb-claude-skills
```

Or from the terminal:

```bash
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mece-decomposer@fb-claude-skills
```

### from local clone

```bash
git clone https://github.com/fblissjr/fb-claude-skills.git
cd fb-claude-skills
/plugin marketplace add .
/plugin install mece-decomposer@fb-claude-skills
```

### temporary loading (development)

```bash
claude --plugin-dir ./apps/mece-decomposer
```

### uninstall

```bash
claude plugin uninstall mece-decomposer@fb-claude-skills
claude plugin list  # verify
```

### updating

Installed plugins auto-update at Claude Code startup when a newer version is published to the marketplace. To pull updates immediately, without waiting for a restart:

```bash
# refresh the marketplace catalog from GitHub
claude plugin marketplace update fb-claude-skills

# update a plugin to its latest version (repeat per plugin)
claude plugin update dev-conventions@fb-claude-skills
```

`claude plugin list` shows installed plugins and versions. To sweep every plugin from this marketplace at once, loop `claude plugin update` over its `@fb-claude-skills` entries. On a multi-machine setup, wrap the marketplace-update + per-plugin-update in a small script and run it after each push to keep every machine current.

## where things work

> **New to MCP?** See [docs/mcp-ecosystem.md](docs/mcp-ecosystem.md) for a field guide to the full MCP ecosystem -- protocols, transports, tools, apps, connectors, and how they all relate.

Plugins from this repo work across multiple Claude surfaces, but capabilities differ by surface:

| Surface | Skills (slash commands) | MCP App UI | Transport |
|---------|------------------------|------------|-----------|
| **Claude Code** (terminal) | yes (namespaced) | text fallback | stdio |
| **Claude Desktop** | yes | text fallback | stdio |
| **Cowork** (in Claude Desktop) | yes | yes (interactive) | stdio |
| **Claude.ai** (web) | -- | yes (if hosted) | Streamable HTTP |

**Key points:**
- **Skills** (including user-invocable slash commands) work in Claude Code, Claude Desktop, and Cowork via stdio transport. This is what `.mcp.json` configures with `--stdio`.
- **MCP App interactive UIs** (like the MECE tree visualizer) render in Cowork and Claude.ai. On CLI/Desktop surfaces, the tools return text summaries instead.
- **Claude.ai requires HTTP transport.** The web interface can't spawn local processes, so it needs a hosted server using Streamable HTTP (not stdio). See [Claude.ai deployment](#deploying-mcp-apps-to-claudeai) below.

## usage

### slash commands

Once installed, invoke as namespaced slash commands:

```
/mece-decomposer:decompose    # Break down a goal into MECE components
/mece-decomposer:interview    # Extract process knowledge from an SME
/mece-decomposer:validate     # Check MECE compliance and scores
/mece-decomposer:export       # Generate Agent SDK Python scaffolding


/plugin-toolkit                # Analyze and manage plugins
/dimensional-modeling          # Star schema design patterns

/dev-conventions:python-tooling  # Full uv conversion tables, pinning, lock file workflow
/dev-conventions:configure      # Per-repo convention overrides
/dev-conventions:dep-audit     # Full bun conversion tables
/dev-conventions:doc-conventions # Documentation standards

/json-query                      # JSON query tool selection + jg syntax
/scan-for-secrets:scan-for-secrets  # Pre-share scan: literal secrets + regex privacy patterns
/writing:plain-language-us       # Write or rewrite prose in an American plain-language style
/writing:voice-match             # Write in your own voice, learned from the thread and a saved profile
/model-routing:model-routing     # Install per-project rule: delegate scoped tasks to cheaper models
/advisor                         # Consult a higher-tier model about this session (user-invoked only)
/postmortem:postmortem           # Evidence-grounded retrospective of a session, feature, or span
/postmortem:postmortem-index     # Browsable HTML index over a repo's postmortems
/postmortem:test-audit           # Audit the test suite: claims, oracles, envelope, verdicts


/skill-maintainer:quality              # Quick quality check for all skills
/skill-maintainer:quality path-privacy   # Check a specific skill
/skill-maintainer:maintain             # Full maintenance pass
/skill-maintainer:init-maintenance     # Set up maintenance in a new repo
/skill-maintainer:sync-versions path-privacy 0.7.4  # Bump version across all sources
/skill-maintainer:finish-session       # Orchestrate end-of-session: log -> sync -> bumps -> quality
```

### keyword activation

Skills also trigger automatically on relevant keywords. Say "decompose this process" or "interview me about this workflow" and the mece-decomposer skill loads.

### MCP App tools

Plugins with MCP Apps expose tools that the model calls automatically during conversations:

| MCP Tool | Plugin | What it does |
|----------|--------|-------------|
| `mece-decompose` | mece-decomposer | Render decomposition as interactive tree |
| `mece-validate` | mece-decomposer | Validate and display score gauges + issues |
| `mece-refine-node` | mece-decomposer | Edit nodes from the UI (app-only) |
| `mece-export-sdk` | mece-decomposer | Preview generated Agent SDK code |
| `skill-quality-check` | skill-dashboard | Quality checks, token budgets, freshness, version alignment |
| `skill-measure` | skill-dashboard | Per-file token breakdown for a single skill |
| `skill-verify` | skill-dashboard | Mark a skill as verified (app-only, updates SKILL.md on disk) |

On Cowork, these render as interactive React UIs. On CLI, they return text.

## MCP Apps

### what are MCP Apps?

MCP Apps are interactive UIs served by MCP servers. They pair a tool (server logic) with a resource (bundled HTML/React) so that when the model calls the tool, a rich UI renders in the host.

The mece-decomposer plugin includes an MCP App that visualizes decomposition trees with collapsible nodes, score gauges, validation panels, and code export preview.

### how they work

1. Model calls an MCP tool (e.g., `mece-decompose`)
2. Server processes the request, returns text (fallback) + structured data (for UI)
3. Host fetches the UI resource (`ui://mece/mcp-app.html`)
4. Host renders the HTML in a sandboxed iframe
5. Host sends tool data to the iframe via MCP messaging
6. UI renders interactively -- user can click nodes, run validation, export code

### deploying MCP Apps to Claude.ai

The plugins in this repo use stdio transport (local process). To use MCP Apps on Claude.ai (web):

1. Run the server as an HTTP service (not stdio):
   ```bash
   cd apps/mece-decomposer/mcp-app
   bun install
   node dist/index.cjs  # starts Streamable HTTP on port 3001
   ```
2. Host the server somewhere network-accessible
3. Register as an MCP connector in Claude.ai settings

The server's `main.ts` supports both transports: `--stdio` for local, HTTP for remote.

## skill-maintainer

Two interfaces: a **plugin** for interactive use in Claude Code, and a **CLI package** for CI/headless automation.

**Plugin** (recommended): install via the marketplace (see above), then use `/skill-maintainer:quality`, `/skill-maintainer:maintain`, `/skill-maintainer:init-maintenance`, `/skill-maintainer:sync-versions`. Skills accept `$ARGUMENTS` for targeting specific skills or directories.

**CLI**: available after `uv sync --all-packages` in this repo, or git-installable into other repos:

```bash
uv add git+https://github.com/fblissjr/fb-claude-skills#subdirectory=tools/skill-maintainer
uv run skill-maintain init     # writes .skill-maintainer/config.json + installs the bundled pre-commit hook
```

`skill-maintain init` is idempotent — re-running on a repo that already has the hook prints `already up to date`. Pass `--force-hook` to replace an existing hook (the prior is preserved as `.git/hooks/pre-commit.local`).

Common CLI commands:

```bash
uv run skill-maintain test              # red/green test suite
uv run skill-maintain quality           # validation + budget + freshness report
uv run skill-maintain upstream          # check Claude Code docs for changes
uv run skill-maintain sources           # pull tracked repos, detect changes
uv run skill-maintain lint              # wiki sanity: orphans, count drift, broken links
uv run skill-maintain log --tail 5      # query audit log
```

The `/skill-maintainer:maintain` skill orchestrates the full pipeline: `sources -> upstream -> quality -> review`. See [skill-maintainer CLI README](tools/skill-maintainer/README.md) for the full CLI reference and data flow diagram.

## documentation

See [docs/README.md](docs/README.md) for the full documentation index.

Highlights:
- [MCP Ecosystem Field Guide](docs/mcp-ecosystem.md) -- protocol, tools, apps, connectors, and how they relate
- [docs/internals/](docs/internals/) -- repo-specific operating reference (version cascade, plugin patterns, maintenance commands, gotchas)
- Upstream Claude Code docs are **not** vendored here — `skill-maintain upstream` fetches them to `.skill-maintainer/state/pages/` (gitignored)
- [docs/analysis/](docs/analysis/) -- what survived the 2026-07-21 triage: the agent-state decision record, the MCP protocol reference, and the decision log explaining what went and why
- Each plugin has its own README with detailed usage

## credits

- Original idea for MECE decomposer by [Ron Zika](https://www.linkedin.com/in/ronzika/)
- scan-for-secrets built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (Apache 2.0) — all literal-matching and escape-variant logic is his work
- More skills: [mlx-skills](https://github.com/fblissjr/mlx-skills) (Apple MLX)
- env-forge (removed 2026-07-26; in git history) built on the synthesis methodology and dataset from [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) by Snowflake Labs
