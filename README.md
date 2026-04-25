last updated: 2026-04-25

# fb-claude-skills

> **[Design Principles (VISION.md)](VISION.md)** -- Skills are retrieval, and retrieval serves an architecture. High precision is the constraint, high recall is the goal. Read this first.

A collection of Claude Code plugins, skills, and MCP Apps. Installable as a plugin marketplace in Claude Code, Cowork, and Claude Desktop.

## plugins

Each plugin addresses a different layer of building with AI: planning and decomposition (mece-decomposer), tool environment infrastructure (env-forge), interactive UIs (mcp-apps), development workflows (dev-conventions, tui-design, cogapp-markdown, dimensional-modeling), and plugin management (plugin-toolkit).

| Plugin | Type | Description |
|--------|------|-------------|
| [mece-decomposer](apps/mece-decomposer/) | Hook + Skills + MCP App | MECE decomposition of goals and workflows into Agent SDK-ready components, with interactive tree visualizer. Hook detects Agent SDK imports. |
| [mcp-apps](skills/mcp-apps/) | Skills | Build and migrate MCP Apps (interactive UIs for MCP-enabled hosts) |
| [plugin-toolkit](skills/plugin-toolkit/) | Skills + Agents | Analyze, polish, and manage Claude Code plugins |
| [tui-design](skills/tui-design/) | Hook + Skill | Terminal UI design principles for Rich, Questionary, and Click. Hook detects TUI library imports. |
| [cogapp-markdown](skills/cogapp-markdown/) | Skill | Auto-generate markdown sections using cogapp |
| [dev-conventions](skills/dev-conventions/) | Hook + Skills | Auto-detects Python/JS projects at session start, injects uv/orjson/bun/TDD/doc conventions via composable directive files |
| [dimensional-modeling](skills/dimensional-modeling/) | Hook + Skill | Kimball-style dimensional modeling for DuckDB star schemas. Hook detects DuckDB usage. |
| [env-forge](apps/env-forge/) | Hook + Skill + Scripts | Interface for [Snowflake AWM](https://github.com/Snowflake-Labs/AgentWorldModel) synthesis pipeline. Hook detects .env-forge or fastapi-mcp. |
| [readwise-reader](apps/readwise-reader/) | MCP Server | Search, save, and surface your Readwise Reader library via MCP with OAuth, DuckDB, and full-text search |
| [agent-state-mcp](apps/agent-state-mcp/) | MCP Server | 18 read-only tools over `~/.claude/agent_state.duckdb` (runs, watermarks, skill versions, flywheel). Ergonomic MCP replacement for the `agent-state` CLI. Opt-in via `.mcp.json` (enable with `/agent-state-mcp:enable`). |
| [json-query](skills/json-query/) | Skill | JSON query tool selection and syntax -- jg (jsongrep) for extraction, jq for transformation |
| [scan-for-secrets](skills/scan-for-secrets/) | Skill + Scripts | Pre-share scanner built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets): literal pass + ripgrep regex pass for leaked secrets and privacy-sensitive paths (your `$HOME`/`$USER`, SSH keys, other users' home paths, emails, IPv4, common API-token shapes). |
| [path-privacy](skills/path-privacy/) | Hook + Skill + Scripts | Enforces a single rule across every artifact: every path written into the repo must be relative to the repo root. SessionStart directive plus pre-commit and commit-msg git hooks that hard-block commits whose staged files, message, or branch name reference anything outside the repo. |
| [skill-maintainer](skills/skill-maintainer/) | Skills + Hooks + Agent | Maintenance tools for skill repos: quality, freshness, upstream detection (per-page snapshots + line/char deltas), best practices review, `finish-session` workflow, `session-log-drafter` agent, PostToolUse bundled-ref sync, Stop-event session-log nudge |
| [skill-dashboard](apps/skill-dashboard/) | MCP App | Interactive quality dashboard: checks, token budgets, freshness, version alignment |

### project-scoped

| Module | Description |
|--------|-------------|
| [heylook-monitor](apps/heylook-monitor/) | MCP App dashboard for heylookitsanllm local LLM server |
| [skill-dashboard](apps/skill-dashboard/) | ext-apps MCP App quality dashboard (TypeScript) |

### installable as a package (not a Claude plugin)

| Module | Description |
|--------|-------------|
| [skill-maintainer](tools/skill-maintainer/) | `skill-maintain` CLI for validating, monitoring, and maintaining skill repos. Git-installable into any repo. |
| [agent-state](tools/agent-state/) | `agent-state` CLI for DuckDB audit/state tracking of pipeline, agent, and CLI runs. Watermark history, run trees, skill version lineage with routing metadata and lifecycle management. |

## installation

### from GitHub (recommended)

```bash
# Add the marketplace (once)
/plugin marketplace add fblissjr/fb-claude-skills

# Install individual plugins
/plugin install mece-decomposer@fb-claude-skills
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install tui-design@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
/plugin install dev-conventions@fb-claude-skills
/plugin install env-forge@fb-claude-skills
/plugin install skill-maintainer@fb-claude-skills
/plugin install readwise-reader@fb-claude-skills
/plugin install agent-state-mcp@fb-claude-skills
/plugin install json-query@fb-claude-skills
/plugin install scan-for-secrets@fb-claude-skills
/plugin install path-privacy@fb-claude-skills
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

/mcp-apps:create-mcp-app      # Build an MCP App from scratch
/mcp-apps:migrate-oai-app     # Migrate from OpenAI Apps SDK

/plugin-toolkit                # Analyze and manage plugins
/tui-design                    # Terminal UI design guidance
/cogapp-markdown               # Auto-generate markdown docs
/dimensional-modeling          # Star schema design patterns

/dev-conventions:python-tooling  # Full uv/orjson conversion tables
/dev-conventions:bun-tooling     # Full bun conversion tables
/dev-conventions:tdd-workflow    # Red/green TDD methodology
/dev-conventions:doc-conventions # Documentation standards

/json-query                      # JSON query tool selection + jg syntax
/scan-for-secrets:scan-for-secrets  # Pre-share scan: literal secrets + regex privacy patterns

/env-forge:browse e-commerce   # Browse AWM-1K catalog, materialize an environment
/env-forge:forge               # Generate a new environment from a description

/skill-maintainer:quality              # Quick quality check for all skills
/skill-maintainer:quality tui-design   # Check a specific skill
/skill-maintainer:maintain             # Full maintenance pass
/skill-maintainer:init-maintenance     # Set up maintenance in a new repo
/skill-maintainer:sync-versions tui-design 0.3.0  # Bump version across all sources
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
skill-maintain init
```

Common CLI commands:

```bash
skill-maintain test              # red/green test suite
skill-maintain quality           # validation + budget + freshness report
skill-maintain upstream          # check Claude Code docs for changes
skill-maintain sources           # pull tracked repos, detect changes
skill-maintain log --tail 5      # query audit log
```

The `/skill-maintainer:maintain` skill orchestrates the full pipeline: `sources -> upstream -> quality -> review`. See [skill-maintainer CLI README](tools/skill-maintainer/README.md) for the full CLI reference and data flow diagram.

## documentation

See [docs/README.md](docs/README.md) for the full documentation index: 16 domain reports, ecosystem synthesis, internals reference, and 18 captured upstream docs.

Highlights:
- [Claude Ecosystem Synthesis](docs/reports/claude_ecosystem_synthesis.md) -- full ecosystem overview, decision tree, maturity assessment
- [MCP Ecosystem Field Guide](docs/mcp-ecosystem.md) -- protocol, tools, apps, connectors, and how they relate
- [docs/internals/](docs/internals/) -- API reference, DuckDB schema, troubleshooting
- Each plugin has its own README with detailed usage

## credits

- Original idea for MECE decomposer by [Ron Zika](https://www.linkedin.com/in/ronzika/)
- cogapp-markdown from [simonw](https://github.com/simonw/skills/tree/main/cogapp-markdown)
- scan-for-secrets built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (Apache 2.0) — all literal-matching and escape-variant logic is his work
- MCP Apps SDK from [modelcontextprotocol/ext-apps](https://github.com/modelcontextprotocol/ext-apps)
- More skills: [mlx-skills](https://github.com/fblissjr/mlx-skills) (Apple MLX)
- env-forge synthesis methodology and dataset from [Agent World Model (AWM)](https://github.com/Snowflake-Labs/AgentWorldModel) by Snowflake Labs
