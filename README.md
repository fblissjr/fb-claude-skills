last updated: 2026-02-19

# fb-claude-skills

A collection of Claude Code plugins, skills, and MCP Apps. Installable as a plugin marketplace in Claude Code, Cowork, and Claude Desktop.

## plugins

| Plugin | Type | Description |
|--------|------|-------------|
| [mece-decomposer](mece-decomposer/) | Skills + MCP App | MECE decomposition of goals and workflows into Agent SDK-ready components, with interactive tree visualizer |
| [mcp-apps](mcp-apps/) | Skills | Build and migrate MCP Apps (interactive UIs for MCP-enabled hosts) |
| [plugin-toolkit](plugin-toolkit/) | Skills + Agents | Analyze, polish, and manage Claude Code plugins |
| [web-tdd](web-tdd/) | Skill | TDD workflow for web applications (Vitest, Playwright, Vibium) |
| [tui-design](tui-design/) | Skill | Terminal UI design principles for Rich, Questionary, and Click |
| [cogapp-markdown](cogapp-markdown/) | Skill | Auto-generate markdown sections using cogapp |
| [dimensional-modeling](dimensional-modeling/) | Skill | Kimball-style dimensional modeling for DuckDB star schemas |

### project-scoped (not installable)

| Module | Description |
|--------|-------------|
| [skill-maintainer](skill-maintainer/) | Automated skill maintenance and upstream change monitoring |
| [heylook-monitor](heylook-monitor/) | MCP App dashboard for heylookitsanllm local LLM server |

## installation

### from GitHub (recommended)

```bash
# Add the marketplace (once)
/plugin marketplace add fblissjr/fb-claude-skills

# Install individual plugins
/plugin install mece-decomposer@fb-claude-skills
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install web-tdd@fb-claude-skills
/plugin install tui-design@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
/plugin install dimensional-modeling@fb-claude-skills
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
claude --plugin-dir ./mece-decomposer
```

### uninstall

```bash
claude plugin uninstall mece-decomposer@fb-claude-skills
claude plugin list  # verify
```

## where things work

> **New to MCP?** See [docs/mcp-ecosystem.md](docs/mcp-ecosystem.md) for a field guide to the full MCP ecosystem -- protocols, transports, tools, apps, connectors, and how they all relate.

Plugins from this repo work across multiple Claude surfaces, but capabilities differ by surface:

| Surface | Skills | Commands | MCP App UI | Transport |
|---------|--------|----------|------------|-----------|
| **Claude Code** (terminal) | yes | yes (namespaced) | text fallback | stdio |
| **Claude Desktop** | yes | yes | text fallback | stdio |
| **Cowork** (in Claude Desktop) | yes | yes | yes (interactive) | stdio |
| **Claude.ai** (web) | -- | -- | yes (if hosted) | Streamable HTTP |

**Key points:**
- **Skills and commands** work in Claude Code, Claude Desktop, and Cowork via stdio transport. This is what `.mcp.json` configures with `--stdio`.
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
/web-tdd                       # Set up TDD for a web project
/tui-design                    # Terminal UI design guidance
/cogapp-markdown               # Auto-generate markdown docs
/dimensional-modeling          # Star schema design patterns
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
   cd mece-decomposer/mcp-app
   npm install
   node dist/index.cjs  # starts Streamable HTTP on port 3001
   ```
2. Host the server somewhere network-accessible
3. Register as an MCP connector in Claude.ai settings

The server's `main.ts` supports both transports: `--stdio` for local, HTTP for remote.

## skill-maintainer

This repo includes a self-updating system that monitors upstream docs and source repos for changes. It runs from within this repo (not installable as a plugin).

```bash
cd fb-claude-skills
claude
# /skill-maintainer check
```

Or run scripts directly:

```bash
uv run python skill-maintainer/scripts/docs_monitor.py      # check doc changes
uv run python skill-maintainer/scripts/source_monitor.py     # check source changes
uv run python skill-maintainer/scripts/update_report.py      # generate report
uv run python skill-maintainer/scripts/apply_updates.py --skill <name>  # apply
uv run python skill-maintainer/scripts/check_freshness.py    # check staleness
```

## documentation

### domain reports

In-depth analysis covering the full Claude extension ecosystem:

| Report | Topic |
|--------|-------|
| [Plugin System Architecture](docs/analysis/plugin_system_architecture.md) | Plugin anatomy, schema, components, auto-discovery, implementation audit |
| [Marketplace Distribution](docs/analysis/marketplace_distribution_patterns.md) | Marketplace schema, source types, monorepo patterns, enterprise distribution |
| [MCP Protocol and Servers](docs/analysis/mcp_protocol_and_servers.md) | MCP protocol, primitives, transports, SDKs, registry, security |
| [MCP Apps and UI Development](docs/analysis/mcp_apps_and_ui_development.md) | MCP Apps SDK, UI linkage, React hooks, framework templates, bundling |
| [Hooks System Patterns](docs/analysis/hooks_system_patterns.md) | Hook events, types, matchers, security patterns, automation |
| [Subagents and Agent Teams](docs/analysis/subagents_and_agent_teams.md) | Custom agents, tool control, model selection, teams, delegation |
| [Cross-Surface Compatibility](docs/analysis/cross_surface_compatibility.md) | Surface matrix, transports, permissions, headless, sandboxing |

### existing analysis

| Report | Topic |
|--------|-------|
| [Skills Best Practices](docs/analysis/claude_skills_best_practices_guide_full_report.md) | Comprehensive skills guide from Anthropic documentation |
| [Self-Updating System Design](docs/analysis/self_updating_system_design.md) | CDC architecture decisions and cross-reference analysis |
| [Abstraction Analogies](docs/analysis/abstraction_analogies.md) | Unifying design principle: selection under constraint |
| [DuckDB Dimensional Model](docs/analysis/duckdb_dimensional_model_strategy.md) | Star schema strategy for agent state |
| [Data-Centric Agent State](docs/analysis/data_centric_agent_state_research.md) | Research on star schema patterns for LLM agents |

### synthesis

| Report | Topic |
|--------|-------|
| [Claude Ecosystem Synthesis](docs/reports/claude_ecosystem_synthesis.md) | Full ecosystem overview, decision tree, maturity assessment, building strategies |

### internals

- [docs/](docs/) -- developer documentation index
- [docs/internals/](docs/internals/) -- API reference, DuckDB schema, troubleshooting
- Each plugin has its own README with detailed usage

## credits

- Concept for MECE decomposer by [Ron Zika](https://www.linkedin.com/in/ronzika/)
- cogapp-markdown from [simonw](https://github.com/simonw/skills/tree/main/cogapp-markdown)
- MCP Apps SDK from [modelcontextprotocol/ext-apps](https://github.com/modelcontextprotocol/ext-apps)
- More skills: [mlx-skills](https://github.com/fblissjr/mlx-skills) (Apple MLX)
