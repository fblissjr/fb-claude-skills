last updated: 2026-02-18

# the MCP ecosystem: a field guide

MCP (Model Context Protocol) has become shorthand for "connectors to external data." That undersells it. MCP is a layered protocol with distinct components that serve different purposes on different surfaces. This guide maps the full ecosystem.

## the protocol layer cake

MCP has four layers. Each builds on the one below:

```
┌──────────────────────────────────────────────┐
│  4. Distribution                             │
│     Connectors, Desktop Extensions, Plugins  │
├──────────────────────────────────────────────┤
│  3. Extensions                               │
│     MCP Apps (interactive UIs)               │
├──────────────────────────────────────────────┤
│  2. Server Features (primitives)             │
│     Tools, Resources, Prompts                │
├──────────────────────────────────────────────┤
│  1. Core Protocol                            │
│     JSON-RPC 2.0, Transports, Capabilities   │
└──────────────────────────────────────────────┘
```

Most people only interact with layer 4 (installing connectors). Most developers work at layer 2 (building tools). MCP Apps live at layer 3. Understanding all four layers clears up the confusion.

## layer 1: core protocol

MCP uses JSON-RPC 2.0 over a transport. A **host** (like Claude Desktop) creates **clients** that connect to **servers**. Each client-server pair is a stateful session with negotiated capabilities.

```
Host (Claude Desktop)
 ├── Client 1 ←→ Server A (filesystem)
 ├── Client 2 ←→ Server B (database)
 └── Client 3 ←→ Server C (remote API)
```

### transports

The transport is how messages physically travel between client and server.

| Transport | How it works | Used by | Use case |
|-----------|-------------|---------|----------|
| **stdio** | Server runs as a subprocess; messages flow over stdin/stdout | Claude Code, Claude Desktop, Cowork, VS Code | Local servers, plugins, development |
| **Streamable HTTP** | Server runs as an HTTP service; messages flow over HTTP requests with SSE streaming | Claude.ai (web) | Remote/hosted servers, production deployments |
| **SSE** (deprecated) | Server-Sent Events over HTTP | Legacy Claude.ai | Being replaced by Streamable HTTP |

**Why this matters:** Claude.ai (the website) can't spawn local processes, so it can't use stdio. It needs a server running somewhere on the internet accessible via HTTP. Claude Code and Claude Desktop _can_ spawn processes, so stdio is simpler and preferred.

## layer 2: server features (the three primitives)

Every MCP server exposes some combination of these three primitives:

| Primitive | Controlled by | What it does | Example |
|-----------|--------------|-------------|---------|
| **Tools** | Model (LLM decides when to call) | Execute functions, take actions | `create-issue`, `run-query`, `send-email` |
| **Resources** | Application (client manages) | Provide read-only data/context | File contents, database schemas, API docs |
| **Prompts** | User (explicit invocation) | Pre-built templates/workflows | Slash commands, menu actions |

Plus two client-side features that servers can _request_:

| Feature | What it does |
|---------|-------------|
| **Sampling** | Server asks the host to run an LLM completion (recursive agent behavior) |
| **Roots** | Server asks which filesystem directories it can access |
| **Elicitation** | Server asks the user a follow-up question for clarification |

**The common misconception:** People think MCP = tools. It also includes resources (context injection) and prompts (user workflows). A well-designed MCP server uses all three where appropriate.

## layer 3: MCP Apps (the UI extension)

MCP Apps (formally SEP-1865, package `@modelcontextprotocol/ext-apps`) extend MCP so that **tools can return interactive UIs** instead of just text.

### how it works

1. Server registers a **tool** with `_meta.ui.resourceUri` pointing to a UI resource
2. Server registers a **resource** with `ui://` URI scheme containing bundled HTML
3. When the model calls the tool, the host:
   - Gets the text result (for non-UI hosts)
   - Fetches the HTML resource
   - Renders it in a sandboxed iframe
   - Sends tool data to the iframe via postMessage

```
Model calls mece-decompose tool
        │
        ▼
   ┌─────────┐
   │  Server  │ → Returns text summary + structuredContent (JSON for UI)
   └─────────┘
        │
        ▼
   ┌─────────┐
   │  Host    │ → Fetches ui://mece/mcp-app.html, renders iframe
   └─────────┘
        │
   ┌────┴────┐
   │ Iframe  │ → Receives structuredContent, renders interactive tree
   │ (React) │ → User clicks → calls app.callServerTool() → back to server
   └─────────┘
```

### what MCP Apps can do

- Render dashboards, forms, charts, visualizations, code editors
- Call server tools from UI buttons (e.g., refresh data, paginate, validate)
- Send messages back to the conversation
- Request fullscreen, picture-in-picture, or inline display
- Theme automatically with host colors, fonts, and dark mode
- Declare CSP (Content Security Policy) for network access

### tool visibility

Tools can be scoped to control who sees them:

| Visibility | Model can call? | UI can call? | Use case |
|-----------|----------------|-------------|----------|
| `["model", "app"]` | Yes | Yes | Default -- model invokes, UI displays |
| `["model"]` | Yes | No | Model-only tools (no UI needed) |
| `["app"]` | No | Yes | Internal UI tools (refresh, paginate, poll) |

App-only tools are invisible to the LLM. They're for UI-driven interactions like "refresh data" buttons that shouldn't clutter the model's tool list.

### where MCP App UIs render

| Surface | UI renders? | What happens instead |
|---------|------------|---------------------|
| **Cowork** (Claude Desktop) | Yes -- interactive iframe | Full UI experience |
| **Claude.ai** (web) | Yes -- interactive iframe | Full UI experience |
| **Claude Code** (terminal) | No | Tool returns text summary from `content` field |
| **Claude Desktop** (non-Cowork) | No | Tool returns text summary |
| **VS Code** (Insiders) | Yes | Experimental support |

The key design: **every MCP App tool returns both `content` (text) and `structuredContent` (JSON for UI).** Hosts that don't render UIs still get useful text output. No separate API needed.

## layer 4: distribution

How MCP servers get to users. Five distinct mechanisms:

### 1. MCP Connectors (Claude.ai)

Pre-built or custom integrations in Claude.ai's web interface.

- **Pre-built connectors:** 50+ one-click integrations (Gmail, Slack, Notion, Jira, etc.) available from the Connectors Directory
- **Custom connectors:** Point Claude.ai at any Streamable HTTP MCP server URL
- **Auth:** OAuth flow for third-party services
- **Transport:** Streamable HTTP only (remote servers)
- **Requires:** Paid Claude.ai plan (Pro, Max, Team, Enterprise)

### 2. Desktop Extensions (.mcpb)

One-click installable MCP servers for Claude Desktop. Formerly `.dxt`, now `.mcpb`.

- **Format:** Zip archive containing server code + `manifest.json`
- **Install:** Settings > Extensions > Browse/Install
- **Transport:** stdio (runs locally)
- **Distribution:** Extension directory, direct download, or marketplace
- **Similar to:** Chrome extensions (.crx), VS Code extensions (.vsix)

### 3. Claude Code Plugins

Plugins for Claude Code and Cowork. What this repo distributes.

- **Format:** Directory with `.claude-plugin/plugin.json` manifest
- **Components:** Skills, commands, agents, hooks, MCP servers
- **MCP config:** `.mcp.json` at plugin root (auto-starts servers)
- **Install:** `/plugin marketplace add owner/repo` then `/plugin install name@marketplace`
- **Transport:** stdio (via `.mcp.json`)

### 4. Manual server config

Directly editing `claude_desktop_config.json` or `.mcp.json` to add servers.

- **Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Code:** `.mcp.json` in project root or `~/.claude/mcp.json` globally
- **Transport:** stdio or HTTP
- **Use case:** Development, custom servers, one-off integrations

### 5. npm / PyPI packages

MCP servers distributed as packages.

- **Install:** `npx @modelcontextprotocol/server-github` or `uvx mcp-server-sqlite`
- **Transport:** stdio (spawned by host)
- **Use case:** Community servers, reusable utilities

## what this repo uses

This repo (`fb-claude-skills`) uses **layer 2 + layer 3 + layer 4**:

| Component | Layer | What it is |
|-----------|-------|-----------|
| Skills (SKILL.md) | 2 (prompts/resources) | Domain knowledge auto-loaded by keyword matching |
| Commands (commands/*.md) | 2 (prompts) | Slash commands users invoke explicitly |
| MCP tools | 2 (tools) | `mece-decompose`, `mece-validate`, `mece-export-sdk` |
| MCP App UI | 3 (extension) | Interactive tree visualizer rendered in Cowork/Claude.ai |
| Plugin distribution | 4 (plugins) | Marketplace install via `/plugin marketplace add` |

The mece-decomposer's `server.ts` registers tools with `registerAppTool()` (layer 2 + 3), serves bundled React HTML via `registerAppResource()` (layer 3), and distributes as a Claude Code plugin with `.mcp.json` auto-configuration (layer 4).

## quick reference

### "I want to give Claude access to my API"
→ Build an **MCP server** with **tools**. Distribute as a **connector** (Claude.ai), **Desktop Extension** (Claude Desktop), or **plugin** (Claude Code).

### "I want to build an interactive dashboard in Claude"
→ Build an **MCP App**. Register tools + UI resource. Renders in Cowork and Claude.ai.

### "I want to add a slash command to Claude Code"
→ Create a **plugin** with a `commands/*.md` file. No MCP server needed.

### "I want Claude to have background knowledge about X"
→ Create a **skill** (`skills/*/SKILL.md`). Loads automatically on keyword match. No MCP server needed.

### "I want to connect Claude.ai to my database"
→ Host a **remote MCP server** with Streamable HTTP transport. Add as a **custom connector** in Claude.ai settings.

## further reading

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25) -- the protocol itself
- [MCP Apps Specification (SEP-1865)](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx) -- the UI extension
- [MCP Apps Blog Post](http://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/) -- announcement and overview
- [Desktop Extensions](https://www.anthropic.com/engineering/desktop-extensions) -- .mcpb format docs
- [Custom Connectors](https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp) -- Claude.ai remote MCP setup
- [ext-apps SDK](https://github.com/modelcontextprotocol/ext-apps) -- TypeScript SDK + examples
- [MCP Servers Directory](https://github.com/modelcontextprotocol/servers) -- community servers
