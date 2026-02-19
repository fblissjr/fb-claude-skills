last updated: 2026-02-19

# Cross-Surface Compatibility

A domain report on building Claude Code extensions that work across every surface where Claude runs -- terminal, desktop, web, SDK, and IDE.

---

## 1. Overview

Claude runs as a CLI tool, a desktop application, a collaborative workspace (Cowork), a web chat interface (Claude.ai), a programmatic SDK in Python and TypeScript, and a VS Code extension. Each surface exposes a different subset of capabilities, uses different transport mechanisms, enforces different permission models, and renders tool outputs differently.

For plugin and skill authors, this creates a fundamental design problem: how do you write an extension once and have it work everywhere? The answer is that you cannot write it once and have it work identically everywhere, but you can design it so the core logic works on every surface and the presentation degrades gracefully where interactive features are unavailable.

This report inventories every surface, maps which features each supports, documents the transport and permission differences, and provides concrete guidance for building extensions with maximum reach.

---

## 2. Surface Inventory

### 2.1 Claude Code CLI (Terminal)

The original and most capable surface. A terminal-based agent with full access to the filesystem, tools, and development environment. Supports skills, commands, agents, hooks, MCP servers, plugins, LSP, and sandboxing.

- **Transport**: stdio for local MCP servers; HTTP/SSE for remote servers
- **UI**: Text-only terminal output; no interactive MCP App rendering
- **Permissions**: Interactive approval prompts; allowlists, deny rules, sandboxing, `bypassPermissions`
- **Configuration**: `~/.claude/`, `~/.claude.json`, project `.claude/`, `.mcp.json`, managed settings

### 2.2 Claude Desktop

Standalone desktop application with MCP server support. Reads `claude_desktop_config.json` for MCP servers and can import servers from Claude Code. Skills and commands work; all output rendered as text (no interactive MCP App UI).

- **Transport**: stdio for local MCP servers; HTTP/SSE for remote
- **UI**: Desktop chat interface; text-based tool output
- **Permissions**: Application-level approval; users approve MCP server connections
- **Configuration**: Application-specific config file; supports importing from Claude Code

### 2.3 Cowork (in Claude Desktop)

Collaborative workspace mode within Claude Desktop. Currently the only non-web surface that renders interactive MCP App UIs. When an MCP server returns a tool result with an associated UI resource, Cowork renders it in a sandboxed iframe.

- **Transport**: stdio (local process spawned by the desktop app)
- **UI**: Interactive -- renders MCP App HTML/React UIs in sandboxed iframes alongside text
- **Permissions**: Inherited from Claude Desktop; user approves server connections
- **Configuration**: Shares Claude Desktop configuration; `.mcp.json` for project-scoped servers

### 2.4 Claude.ai (Web)

Web interface at claude.ai. Cannot spawn local processes, so all MCP server connections must use Streamable HTTP transport. MCP Apps hosted as HTTP services can render interactive UIs via MCP connectors registered in settings.

- **Transport**: Streamable HTTP only (no stdio)
- **UI**: Interactive -- renders MCP App UIs when connected to hosted MCP servers
- **Permissions**: OAuth-based authentication for MCP connectors; no filesystem-level permissions
- **Configuration**: Account-level settings; MCP connectors added through the web UI

### 2.5 Agent SDK (Python and TypeScript)

The SDK packages provide the same agent loop and tools that power Claude Code, as libraries for programmatic control. The CLI entry point (`claude -p`) is the simplest form. Supports structured output (`--output-format json`), streaming (`stream-json`), tool approval via `--allowedTools`, and JSON schema extraction.

- **Transport**: stdio for spawned MCP servers; HTTP for remote servers
- **UI**: None (programmatic output only)
- **Permissions**: `--allowedTools` / `--disallowedTools`; no interactive prompts in `-p` mode
- **Configuration**: Same as CLI; `~/.claude.json`, project `.claude/`, `.mcp.json`, env vars

### 2.6 VS Code Extension

Claude Code as a VS Code extension, providing an agent panel within the IDE. Same tools as the CLI; text-based output within the VS Code UI. Full support for skills, agents, hooks, plugins, and LSP.

- **Transport**: stdio for local MCP servers; HTTP for remote
- **UI**: VS Code panel; text-based tool output
- **Permissions**: Inherits CLI permission model; interactive approval within VS Code
- **Configuration**: Same as CLI (`~/.claude/`, project `.claude/`)

---

## 3. Feature Compatibility Matrix

| Feature | CLI | Desktop | Cowork | Claude.ai | SDK Py/TS | VS Code |
|---------|-----|---------|--------|-----------|-----------|---------|
| **Skills (SKILL.md)** | Yes | Yes | Yes | No | Partial [1] | Yes |
| **Commands (slash)** | Yes | Yes | Yes | No | No [2] | Yes |
| **Agents (subagents)** | Yes | Partial | Partial | No | Yes [3] | Yes |
| **Hooks** | Yes | No | No | No | Yes | Yes |
| **MCP Servers (stdio)** | Yes | Yes | Yes | No | Yes | Yes |
| **MCP Servers (HTTP)** | Yes | Yes | Yes | Yes | Yes | Yes |
| **MCP Apps (interactive)** | No [4] | No [4] | Yes | Yes [5] | No | No [4] |
| **MCP Apps (text fallback)** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Plugins** | Yes | Yes | Yes | No | Partial [6] | Yes |
| **Plugin Marketplaces** | Yes | Yes | Yes | No | No | Yes |
| **LSP Servers** | Yes | No | No | No | No | Yes |
| **Sandboxing (OS-level)** | Yes | No | No | N/A | Yes | Yes |
| **Agent Teams** | Yes | No | No | No | Yes | No |

**Notes:**

1. Skills available when the project directory with `.claude/skills/` is accessible. Headless mode cannot invoke `/name` commands; describe the task instead.
2. Slash commands are interactive-only. In SDK/headless mode, describe what you want.
3. Subagents work via `--agents` CLI flag or programmatic definitions.
4. These surfaces receive text fallback only; no iframe rendering.
5. Requires the MCP server to be hosted as HTTP and registered as an MCP connector.
6. Plugins loadable via `--plugin-dir` but marketplace discovery is interactive-only.

---

## 4. Transport Requirements

### 4.1 stdio

Default transport for local MCP servers. The host spawns the server as a child process and communicates over stdin/stdout.

**Supported on**: CLI, Desktop, Cowork, SDK Python/TS, VS Code

**Use for**: Local development tools, marketplace-distributed plugins (`.mcp.json` with stdio commands), servers needing direct filesystem access, testing and development.

**Cannot be used from Claude.ai** -- the browser cannot spawn local processes.

### 4.2 HTTP (Streamable HTTP)

Connects to remote MCP servers over the network. The only transport available on Claude.ai. Recommended for cloud-based services.

**Supported on**: All surfaces

**Use for**: Cloud services (GitHub, Sentry, Notion), MCP Apps deployed for Claude.ai, multi-user servers, production deployments.

### 4.3 SSE (Deprecated)

Deprecated in favor of Streamable HTTP. Still functional where HTTP is supported.

### 4.4 Dual-Transport Servers

For maximum compatibility, MCP servers should support both stdio and HTTP. The mece-decomposer in this repo demonstrates this pattern:

```bash
# Local (stdio) -- CLI, Desktop, Cowork, SDK, VS Code
node dist/index.cjs --stdio

# Remote (HTTP) -- all surfaces including Claude.ai
node dist/index.cjs  # starts Streamable HTTP on port 3001
```

---

## 5. Plugin Distribution per Surface

| Surface | Install | Marketplace | `--plugin-dir` | Auto-updates |
|---------|---------|-------------|----------------|--------------|
| CLI | Yes | Yes | Yes | Yes |
| Desktop | Yes | Yes | No | Yes |
| Cowork | Via Desktop | Via Desktop | No | Yes |
| Claude.ai | No | No | No | No |
| SDK Py/TS | No | No | Yes | No |
| VS Code | Yes | Yes | Yes | Yes |

**From GitHub marketplace**:
```bash
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mece-decomposer@fb-claude-skills
```

**Local development**: `claude --plugin-dir ./my-plugin`

**Official marketplace**: `claude-plugins-official` is available automatically. Includes code intelligence (LSP for 11 languages), external integrations (GitHub, Slack, Sentry, Notion, etc.), and workflow plugins.

**Component availability by surface**: Skills and commands on CLI/Desktop/Cowork/VS Code. Agents on CLI/VS Code (partial on Desktop/Cowork). Hooks on CLI/SDK/VS Code. MCP servers (stdio) on CLI/Desktop/Cowork/SDK/VS Code. LSP servers on CLI and VS Code only.

---

## 6. MCP App Rendering

### 6.1 How MCP Apps Work

MCP Apps pair a tool (server logic) with a UI resource (bundled HTML/React). When the model calls the tool, the server returns text content (always) plus a resource reference (for UI). If the host supports interactive rendering, it fetches the resource and renders it in a sandboxed iframe.

### 6.2 Rendering by Surface

| Surface | Rendering | Notes |
|---------|-----------|-------|
| CLI | Text fallback | No iframe available |
| Desktop | Text fallback | Same as CLI |
| Cowork | Interactive | Sandboxed iframe with full React UI |
| Claude.ai | Interactive | Requires hosted HTTP server registered as connector |
| SDK Py/TS | Text fallback | Programmatic output only |
| VS Code | Text fallback | Text in VS Code panel |

### 6.3 Designing for Graceful Degradation

Every MCP App tool must return a meaningful text result. On most surfaces, text is the only output the user sees. The interactive UI is an enhancement, not a replacement.

```typescript
return {
  content: [
    { type: "text", text: formatTextSummary(result) },          // Always present
    { type: "resource", resource: { uri: "ui://mece/app.html" }} // Interactive surfaces only
  ]
};
```

The text fallback should be genuinely useful -- not a stub saying "see UI." On CLI, this is the only output.

---

## 7. Permission Model Differences

### 7.1 Interactive Surfaces (CLI, VS Code, Desktop)

Full permission system with interactive approval:

- **Read-only tools**: No approval required
- **Bash commands**: Require approval; "don't ask again" is permanent per project/command
- **File modifications**: Require approval; "don't ask again" lasts for the session
- **Permission modes**: `default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`
- **Rules**: `allow`, `ask`, `deny` with tool-specific specifiers and glob patterns
- **Evaluation order**: deny > ask > allow (first match wins)
- **PreToolUse hooks**: Extend the permission system dynamically (exit 0 = approve, exit 2 = deny)

### 7.2 SDK / Headless (`-p`)

No interactive prompts:

- `--allowedTools "Read,Edit,Bash(npm run *)"` -- explicit allowlist
- `--disallowedTools` -- explicit denylist
- Tools not allowed are auto-denied
- Agent operates autonomously within granted permissions

### 7.3 Claude.ai (Web)

- OAuth-based authentication for MCP connectors
- Users approve connector registrations, not individual tool calls
- No filesystem permissions; no sandboxing (no local execution)

### 7.4 Managed (Enterprise)

Centralized policy via `managed-settings.json` in system directories. Cannot be overridden by user or project settings. Managed-only settings: `disableBypassPermissionsMode`, `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `strictKnownMarketplaces`. Server-managed settings available as alternative for orgs without device management.

---

## 8. Configuration Paths

| Path | Purpose | Surfaces |
|------|---------|----------|
| `~/.claude/` | User skills, agents, settings | CLI, SDK, VS Code |
| `~/.claude.json` | User/local MCP servers, global config | CLI, SDK, VS Code |
| `.claude/` (project) | Project skills, agents, settings | CLI, SDK, VS Code |
| `.claude/settings.local.json` | Local settings (gitignored) | CLI, SDK, VS Code |
| `.mcp.json` (project root) | Shared MCP servers (version-controlled) | CLI, Desktop, Cowork, SDK, VS Code |
| `claude_desktop_config.json` | Desktop MCP config | Desktop, Cowork |
| System managed dirs | Enterprise policy | CLI, SDK, VS Code |

**Managed settings locations**:
- macOS: `/Library/Application Support/ClaudeCode/`
- Linux/WSL: `/etc/claude-code/`
- Windows: `C:\Program Files\ClaudeCode\`

**MCP scope precedence** (highest first): local (in `~/.claude.json` per project) > project (`.mcp.json`) > user (`~/.claude.json` global).

**Key environment variables**: `CLAUDE_CONFIG_DIR` (override config dir), `ENABLE_TOOL_SEARCH` (MCP tool search), `MAX_MCP_OUTPUT_TOKENS` (default 25000), `MCP_TIMEOUT` / `MCP_TOOL_TIMEOUT`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`.

---

## 9. Headless and Automation

### 9.1 CLI Headless Mode

The `-p` flag runs Claude Code non-interactively for CI/CD, scripting, and SDK use:

```bash
claude -p "Fix the bug in auth.py" --allowedTools "Read,Edit,Bash"
claude -p "Summarize this project" --output-format json
claude -p "Extract functions" --output-format json --json-schema '{...}'
claude -p "Explain recursion" --output-format stream-json --verbose
```

### 9.2 Session Continuity

```bash
claude -p "Review this codebase"
claude -p "Now focus on database queries" --continue
session_id=$(claude -p "Start review" --output-format json | jq -r '.session_id')
claude -p "Continue" --resume "$session_id"
```

### 9.3 CI/CD Patterns

- `--allowedTools` for minimal permissions
- `--output-format json` for machine-readable output
- `--json-schema` for structured extraction
- `--append-system-prompt` for role-specific instructions
- Slash commands unavailable -- describe the task directly

### 9.4 Limitations

Slash commands, interactive MCP App UIs, marketplace discovery, and permission prompts are all unavailable in headless mode.

---

## 10. Sandboxing

OS-level filesystem and network isolation for Bash commands. Uses native security primitives immune to prompt injection.

| Platform | Mechanism | Status |
|----------|-----------|--------|
| macOS | Seatbelt | Works out of the box |
| Linux/WSL2 | bubblewrap + socat | Requires package install |
| WSL1 | N/A | Not supported |
| Windows (native) | Planned | Not yet available |

**Available on**: CLI, SDK, VS Code. **Not available on**: Desktop, Cowork, Claude.ai (N/A).

**Sandbox modes**: Auto-allow (sandboxed commands run without prompts; unsandboxable commands fall back to normal flow) and regular (standard permission flow even when sandboxed).

Sandboxing and permissions are complementary layers. Permissions control which tools Claude uses (all tools). Sandboxing restricts what Bash can access at the OS level. Both should be configured for defense-in-depth.

The sandbox runtime is open source: `npx @anthropic-ai/sandbox-runtime <command>`.

---

## 11. Building for Maximum Reach

### 11.1 Design Principles

**Always provide text output.** Every tool, skill, and MCP App must produce meaningful text. Interactive UI is a bonus for Cowork/Claude.ai; text is the universal format.

**Default to stdio transport.** Plugins use stdio in `.mcp.json`. Add HTTP separately for Claude.ai.

**Keep skills self-contained.** Skills depending only on SKILL.md and standard tools (Read, Edit, Bash, Grep, Glob) work everywhere that supports skills.

**Use progressive disclosure.** SKILL.md under 500 lines; detailed references in supporting files.

### 11.2 Plugin Structure

```
my-plugin/
  .claude-plugin/plugin.json    # name, version, description
  .mcp.json                     # stdio MCP servers (optional)
  skills/my-skill/SKILL.md      # frontmatter + instructions
  agents/                       # subagent definitions (optional)
  hooks/hooks.json              # event handlers (optional)
  commands/                     # simple slash commands (optional)
```

### 11.3 No Runtime Surface Detection

There is no API for detecting which surface is running. Design for the lowest common denominator (text output, stdio transport) and let richer surfaces enhance automatically. The host renders HTML resources when it can; otherwise it uses text. No conditional logic is needed in tool handlers.

### 11.4 Avoid Surface-Specific Dependencies

- No interactive prompts in skill logic (breaks headless mode)
- No filesystem assumptions in MCP App UIs (breaks Claude.ai)
- No HTTP-only core functionality (breaks local-only setups)
- No LSP dependency (only CLI and VS Code)

---

## 12. Testing Across Surfaces

### 12.1 Workflows

**Local**: `claude --plugin-dir ./my-plugin` -- invoke skills, check `/mcp`, verify text output.

**Headless**: `claude -p "task" --plugin-dir ./my-plugin --allowedTools "Read,Grep"` -- verify JSON output.

**MCP Apps**: Test text fallback on CLI; interactive UI on Cowork; HTTP transport on Claude.ai.

### 12.2 Cross-Surface Checklist

- Skills load and respond correctly on CLI
- Skills work in headless mode (`-p`)
- MCP servers start and connect (check `/mcp`)
- MCP App tools return meaningful text (not "see UI")
- Hooks execute on correct events
- Agents appear in `/agents` and delegate correctly
- Plugin installs from marketplace without errors
- Permissions allow expected operations
- Sandbox does not block required commands

### 12.3 Known Gaps

No automated cross-surface testing framework exists. Cowork and Claude.ai interactive rendering require manual verification. Desktop behavior must be tested in the Desktop application. Agent teams are experimental and may behave differently across SDK versions.

---

## 13. Forward-Looking

**Agent teams** -- Experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Multiple Claude instances with shared task lists across separate sessions. Available on CLI and SDK. Cross-surface team coordination will matter as this matures.

**Transport evolution** -- SSE deprecated for Streamable HTTP. Tool search (`ENABLE_TOOL_SEARCH`) loads MCP tools on demand, reducing context consumption. `list_changed` notifications enable dynamic capability updates. OAuth 2.0 becoming standard for remote authentication.

**New surfaces** -- Mobile, additional IDE integrations, embedded agents in third-party products. Core principle holds: design for text over stdio, let richer surfaces enhance.

**Plugin ecosystem** -- Official marketplace growing (code intelligence, integrations, workflows). Community marketplaces via GitHub repos. Enterprise control via `strictKnownMarketplaces`. Auto-updates via `FORCE_AUTOUPDATE_PLUGINS`.

**Sandboxing expansion** -- Native Windows support planned. Open-source runtime enables third-party adoption. Network filtering likely to gain fine-grained capabilities.

---

## 14. Cross-References

Analysis reports in this repository:

- [abstraction_analogies.md](abstraction_analogies.md) -- Selection under constraint framework
- [claude_skills_best_practices_guide_full_report.md](claude_skills_best_practices_guide_full_report.md) -- Skill authoring best practices
- [skills_guide_structured.md](skills_guide_structured.md) -- Structured extraction from Anthropic skills guide
- [skills_guide_analysis.md](skills_guide_analysis.md) -- Gap analysis of skills capabilities
- [self_updating_system_design.md](self_updating_system_design.md) -- CDC pipeline design
- [data_centric_agent_state_research.md](data_centric_agent_state_research.md) -- Agent state management research
- [duckdb_dimensional_model_strategy.md](duckdb_dimensional_model_strategy.md) -- Dimensional modeling strategy

Source documentation:

- [claude_docs_skills.md](../claude-docs/claude_docs_skills.md) -- Skills
- [claude_docs_plugins.md](../claude-docs/claude_docs_plugins.md) -- Plugins
- [claude_docs_mcp.md](../claude-docs/claude_docs_mcp.md) -- MCP
- [claude_docs_permissions.md](../claude-docs/claude_docs_permissions.md) -- Permissions
- [claude_docs_settings.md](../claude-docs/claude_docs_settings.md) -- Settings
- [claude_docs_headless.md](../claude-docs/claude_docs_headless.md) -- Headless / Agent SDK
- [claude_docs_sandboxing.md](../claude-docs/claude_docs_sandboxing.md) -- Sandboxing
- [claude_docs_sub-agents.md](../claude-docs/claude_docs_sub-agents.md) -- Subagents
