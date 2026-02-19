last updated: 2026-02-19

# Claude Extension Ecosystem Synthesis

A unified view of the Claude Code extension architecture, drawn from 15 analysis
reports covering skills, plugins, hooks, MCP servers, MCP Apps, subagents, agent
teams, marketplaces, cross-surface compatibility, the memory and rules system, and
the maintenance systems that keep them all current. This document ties together
findings across every domain and provides architectural guidance for building,
distributing, and maintaining Claude extensions.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Extension Model](#2-the-extension-model)
   - [2.5 Memory and Rules System](#25-memory-and-rules-system)
3. [Architecture Decision Tree](#3-architecture-decision-tree)
4. [Component Maturity Assessment](#4-component-maturity-assessment)
5. [Building Strategies](#5-building-strategies)
6. [Cross-Surface Strategy](#6-cross-surface-strategy)
7. [MCP Ecosystem](#7-mcp-ecosystem)
8. [The Maintenance Problem](#8-the-maintenance-problem)
9. [Forward-Looking](#9-forward-looking)
10. [This Repo as Reference Implementation](#10-this-repo-as-reference-implementation)
11. [Report Index](#11-report-index)

---

## 1. Executive Summary

The Claude extension ecosystem provides six component types for extending Claude's
capabilities:

- **Skills** -- markdown-based knowledge and workflow instructions (SKILL.md with
  YAML frontmatter). The primary unit of domain expertise. Loaded into context
  via progressive disclosure: frontmatter always present, body loaded when
  relevant, linked files loaded on demand.

- **Agents** -- subagent definitions that run in isolated context windows with
  custom system prompts and restricted tool access. Claude delegates to them
  automatically based on description matching.

- **Hooks** -- deterministic event handlers that fire at specific lifecycle
  points (session start, tool execution, file writes, etc.). Unlike skills,
  hooks guarantee execution -- no probabilistic element.

- **MCP Servers** -- external processes exposing tools, resources, and prompts
  via the Model Context Protocol. The connectivity layer: databases, APIs,
  cloud services, local file systems.

- **MCP Apps** -- interactive user interfaces served from MCP servers, rendered
  in sandboxed iframes by compatible hosts. Charts, dashboards, forms, and
  visualizations that go beyond text output.

- **LSP Servers** -- Language Server Protocol integrations providing code
  intelligence (completions, diagnostics, hover info) to Claude's editing
  capabilities.

- **Memory & Rules** -- CLAUDE.md files and `.claude/rules/*.md` files that
  load instructions unconditionally into context. Six levels: managed policy
  (org), project, project-local, user, auto memory (Claude-written notes), and
  path-scoped rules. Independent of the plugin system -- these load at session
  start based on filesystem location, regardless of plugin installation.

These six components are packaged into **plugins** -- self-contained directories
with a `.claude-plugin/plugin.json` manifest. Plugins are distributed through
**marketplaces** -- catalogs defined by `.claude-plugin/marketplace.json` at the
root of a git repository.

The fundamental challenge is **maintenance**. Skills encode knowledge about
upstream APIs, documentation, and best practices. When those sources change,
skills become stale. The CDC (Change Data Capture) pipeline in this repo
demonstrates a closed-loop solution: detect upstream changes, classify their
impact, apply updates, validate against the Agent Skills spec, and surface
results for human review.

---

## 2. The Extension Model

### Layered Architecture

The Claude extension system is layered. Each layer serves a distinct purpose and
communicates through well-defined interfaces.

```
+-----------------------------------------------------------------------+
|                        User Request                                   |
+-----------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------+
|  Routing Layer (Frontmatter + Descriptions)                           |
|  - Skill frontmatter scanned for description match                    |
|  - Agent descriptions evaluated for delegation decisions              |
|  - Commands matched by name (slash invocation)                        |
+-----------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------+
|  Knowledge Layer (Skills + References)                                |
|  - SKILL.md body loaded into context                                  |
|  - references/ loaded on demand (progressive disclosure)              |
|  - scripts/ executed when skill instructions require it               |
+-----------------------------------------------------------------------+
         |                                    |
         v                                    v
+----------------------------+   +----------------------------+
|  Delegation Layer          |   |  Interception Layer        |
|  - Subagents (isolated)    |   |  - Hooks (deterministic)   |
|  - Agent teams (parallel)  |   |  - PreToolUse blocking     |
|  - Model selection per     |   |  - PostToolUse observation  |
|    agent (haiku/sonnet/    |   |  - Session lifecycle       |
|    opus)                   |   |    management              |
+----------------------------+   +----------------------------+
         |                                    |
         v                                    v
+-----------------------------------------------------------------------+
|  Tool Execution Layer                                                 |
|  - Built-in tools (Read, Write, Bash, Glob, Grep, etc.)              |
|  - MCP server tools (external APIs, databases, services)              |
|  - LSP server queries (code intelligence)                             |
+-----------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------+
|  Presentation Layer                                                   |
|  - Text output (all surfaces)                                         |
|  - MCP App UIs (Cowork, Claude.ai with HTTP servers)                  |
|  - Graceful degradation (text fallback where UI unavailable)          |
+-----------------------------------------------------------------------+
```

### Information Flow

A typical request flows through these layers as follows:

1. **User submits a prompt.** `UserPromptSubmit` hooks fire first (can block).
2. **Routing evaluates which skills are relevant.** Frontmatter descriptions are
   matched against the user's intent. Relevant skills have their SKILL.md body
   loaded into context.
3. **Claude processes the request** with loaded skill instructions guiding its
   behavior.
4. **Delegation occurs** when the task matches a subagent's description. The
   subagent runs in an isolated context window, works over multiple tool-use
   turns, and returns results.
5. **Tool execution** is intercepted by hooks. `PreToolUse` hooks can validate,
   modify, or block tool calls. `PostToolUse` hooks observe results.
6. **MCP server tools** are called via the protocol. The server processes the
   request and returns structured data, optionally with `ui://` resource URIs
   for interactive rendering.
7. **Output is rendered.** Text goes to all surfaces. MCP App UIs render in
   compatible hosts (Cowork, Claude.ai). Other surfaces receive text fallback.

### Composition

Components compose rather than compete. A single plugin can contain skills (for
knowledge), agents (for delegation), hooks (for enforcement), an MCP server
(for external data), and an MCP App (for visualization). The mece-decomposer
plugin in this repo demonstrates this: it bundles skills, commands, an MCP
server (`.mcp.json`), and an MCP App (React tree visualizer).

---

## 2.5 Memory and Rules System

Memory and rules are distinct from the six plugin-packaged components. They load
unconditionally at session start based on filesystem location -- no plugin installation
required, no description matching needed.

### The Six-Level Hierarchy

| Level | Location | Shared With | Priority |
|-------|----------|-------------|----------|
| Managed policy | OS system directory (MDM-deployed) | All users in org | Broadest |
| Project memory | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via source control | |
| Project rules | `./.claude/rules/*.md` | Team via source control | |
| User memory | `~/.claude/CLAUDE.md` | Just you, all projects | |
| Project memory (local) | `./CLAUDE.local.md` (auto-gitignored) | Just you, current project | |
| Auto memory | `~/.claude/projects/<project>/memory/` | Just you, per project | Most specific |

More specific instructions take precedence over broader ones.

### Auto Memory

Auto memory is Claude's self-maintained knowledge base. Unlike CLAUDE.md files (written by
humans for Claude), auto memory contains notes Claude writes for itself based on session
discoveries.

Storage: `~/.claude/projects/<project>/memory/`, derived from the git repository root. All
subdirectories of a repo share one auto memory directory. Worktrees get separate directories.

Structure:
```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Index -- first 200 lines loaded into every session
├── debugging.md       # Detailed debugging patterns (loaded on demand)
├── patterns.md        # Architectural patterns (loaded on demand)
└── ...                # Other topic files created as needed
```

Key behaviors:
- `MEMORY.md` first 200 lines load into every session's system prompt.
- Topic files load on demand via Claude's file tools when needed.
- Control with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=0` (force on) or `=1` (force off).
- `/memory` command opens the file selector during a session.

What Claude saves: project build commands, debugging insights, key file paths, architecture
decisions, user preferences, and patterns that would otherwise require re-explanation.

### CLAUDE.md Imports

CLAUDE.md files can import additional files with `@path/to/import` syntax:

```
See @README for project overview.

# Instructions
- git workflow @docs/git-instructions.md
- personal preferences @~/.claude/my-project.md
```

Rules: relative and absolute paths supported; relative paths resolve from the importing file
(not cwd); max depth 5 hops; imports not evaluated inside code spans or blocks; one-time
approval dialog per project on first use.

### Modular Rules with `.claude/rules/`

The `.claude/rules/` directory allows teams to maintain focused rule files instead of one
large CLAUDE.md. All `.md` files are auto-discovered recursively.

Path-scoped rules with YAML frontmatter:
```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/**/*.{ts,tsx}"
---

# API Rules
- All endpoints must include input validation
```

Rules without `paths` frontmatter apply unconditionally. Glob patterns supported: `**/*.ts`,
`src/**/*`, `*.md`, brace expansion. Subdirectory organization supported. Symlinks supported
and resolved (circular symlinks handled gracefully).

User-level rules at `~/.claude/rules/` apply across all projects (lower priority than project
rules).

### Memory vs Skills vs Hooks

| Dimension | Memory / Rules | Skills | Hooks |
|-----------|---------------|--------|-------|
| Loading | Unconditional | Description-match | Event-triggered |
| Guarantee | Loaded (not guaranteed followed) | Probabilistic | Deterministic |
| Path-scoping | Yes (`rules/` frontmatter) | No | Yes (matcher) |
| Org-level | Yes (managed policy) | No | No |
| Plugin system | Independent | Core component | Core component |
| Who writes | Humans / Claude | Skill authors | Automation authors |

Use memory to set baseline context and org-wide standards. Use skills for domain expertise.
Use hooks for enforcement where compliance must be guaranteed.

See [memory_and_rules_system.md](../analysis/memory_and_rules_system.md) for full details.

---

## 3. Architecture Decision Tree

### "I want to..." Decision Guide

| Goal | Recommended Component | Why |
|------|----------------------|-----|
| Teach Claude a workflow or best practice | **Skill** | Skills are knowledge injection. They guide Claude's behavior without requiring external tools. Cheapest to build and maintain. |
| Enforce a rule that must always hold | **Hook** (command or prompt type) | Hooks are deterministic. A `PreToolUse` hook blocking `rm -rf /` fires every time, unlike a skill instruction that Claude might ignore under pressure. |
| Add access to an external API or database | **MCP Server** | MCP is the connectivity standard. One server works with every MCP-compatible client. |
| Show interactive charts, dashboards, or forms | **MCP App** | MCP Apps render in sandboxed iframes. Design with text fallback for surfaces that cannot render UIs. |
| Isolate a complex subtask (code review, search) | **Subagent** | Subagents preserve the main context window by running in isolation. Route to cheaper models (Haiku) for read-only work. |
| Coordinate multiple parallel workstreams | **Agent Team** (experimental) | Agent teams span separate sessions with independent context windows. Use for sustained parallelism beyond what subagents provide. |
| Add code intelligence (completions, diagnostics) | **LSP Server** | LSP provides structured language features that Claude can use during editing. |
| Distribute extensions to other users | **Plugin + Marketplace** | Plugins bundle components; marketplaces provide discovery, versioning, and governance. |
| Run deterministic validation on every file write | **Hook** (`PostToolUse` on Write/Edit) | Hooks are the only mechanism that guarantees execution after every tool call. |
| Inject context at session start | **Hook** (`SessionStart` event) | Load project state, set environment variables, or initialize resources deterministically. |
| Block dangerous commands conditionally | **Hook** (`PreToolUse` with matcher) | Match specific tool names and validate inputs. Exit code 2 blocks; stderr becomes Claude's feedback. |

### Combining Components

Most real-world extensions combine multiple component types:

| Pattern | Components Used | Example |
|---------|----------------|---------|
| Guided workflow with enforcement | Skill + Hook | Skill teaches the workflow; hook blocks violations |
| External data with visualization | MCP Server + MCP App | Server fetches data; App renders dashboard |
| Delegated analysis with reporting | Subagent + Skill | Agent performs analysis; skill defines report format |
| Automated pipeline | Hook + MCP Server | Hook triggers on file change; server processes data |
| Full-stack plugin | Skill + Agent + Hook + MCP + App | Complete extension with knowledge, delegation, enforcement, connectivity, and UI |

---

## 4. Component Maturity Assessment

| Component | Maturity | Docs Quality | Adoption | Stability | Notes |
|-----------|----------|-------------|----------|-----------|-------|
| **Skills** | Stable | High | High | Solid | Core primitive. Well-documented via Anthropic guide + official docs. Agent Skills spec provides validation. |
| **Agents (subagents)** | Stable | High | Medium | Solid | Built-in agents (Explore, Plan) well-tested. Custom agents straightforward. Cannot nest (subagents cannot spawn subagents). |
| **Hooks** | Stable | High | Medium | Solid | 14 event types. Three handler types (command, prompt, agent). Well-documented but requires shell scripting knowledge. |
| **MCP Servers** | Stable | High | High | Solid | Hundreds of servers in the ecosystem. Protocol version 2025-11-25. SDKs in 10+ languages. Registry infrastructure maturing. |
| **MCP Apps** | Maturing | Medium | Low | Evolving | SEP-1865 stable since 2026-01-26. Two SDK paths converging. Only Cowork and Claude.ai (HTTP) render interactive UIs. |
| **Plugins** | Stable | High | Medium | Solid | Auto-discovery of components in default directories. Namespacing prevents collisions. Version-driven cache invalidation. |
| **Marketplaces** | Stable | Medium | Low | Solid | Five source types (relative, GitHub, git URL, npm, pip). npm and pip "not yet fully implemented." |
| **Agent Teams** | Experimental | Low | Very Low | Unstable | Multi-session coordination. `TeammateIdle` and `TaskCompleted` hook events exist. Limited documentation. |
| **LSP Servers** | Stable | Low | Very Low | Solid | Configuration via `.lsp.json`. Only supported on CLI and VS Code. Minimal public documentation. |
| **Memory & Rules** | Stable | High | High | Solid | Core mechanism. Six-level hierarchy. Path-scoped rules (`.claude/rules/`) are a lightweight alternative to plugin hooks for conditional instruction loading. Auto memory is in gradual rollout. |

Key observations:

- Skills and MCP Servers are the most mature and widely adopted components.
- Hooks are powerful but underutilized -- most users do not know they exist.
- MCP Apps are the newest addition and the most likely to see breaking changes.
- Agent Teams are experimental and should not be relied on for production workflows.
- LSP Servers work but have almost no public documentation or community adoption.

---

## 5. Building Strategies

### Solo Developer Tier

For individual developers building personal extensions:

- Start with **skills only**. A single SKILL.md with well-written frontmatter
  and instructions covers most use cases. No infrastructure needed.
- Add **hooks** for enforcement. If there are rules you always forget
  (formatting, naming conventions, commit message style), a hook guarantees
  compliance without relying on memory.
- Use **CLAUDE.local.md** for private project preferences (sandbox URLs, local
  test data, personal flags) that should not be committed. It is auto-gitignored.
- Use **auto memory** to avoid re-explaining project architecture every session.
  Tell Claude directly: "remember that we use pnpm, not npm" to save specific facts.
- Keep skills **project-scoped** (`.claude/skills/`) until they prove useful
  across projects. Then promote to user-scoped (`~/.claude/skills/`) or
  package as a plugin.
- Use **progressive disclosure**. Frontmatter under 200 words. SKILL.md body
  under 500 lines. Verbose examples, directory structures, and API references
  go in `references/`.
- Validate with `skills-ref validate` before sharing.

### Team Tier

For teams sharing extensions across projects and developers:

- **Package as plugins.** Every shared extension should be a plugin with
  `plugin.json`, semantic versioning, and a README.
- **Create a marketplace.** A team-internal git repository with
  `marketplace.json` provides discovery, version tracking, and a single
  installation source.
- Add **agents** for specialized tasks. Code review, security scanning,
  and documentation generation are natural delegation targets.
- Use **hooks for team standards.** Pre-commit validation, license checking,
  and architecture constraint enforcement.
- Use **`.claude/rules/`** for modular team standards. Each file covers one
  topic (testing conventions, API design, security requirements). Scope rules
  to specific file types using `paths:` frontmatter instead of bloating CLAUDE.md.
- Establish a **maintenance cadence.** Upstream docs change. APIs evolve.
  Without monitoring, skills rot within months.

### Enterprise Tier

For organizations managing Claude at scale:

- **Managed settings** define organization-wide configuration. Allowlists,
  deny rules, permission modes, and default models are set centrally.
- **Managed policy CLAUDE.md** deployed via MDM/Group Policy/Ansible enforces
  org-wide coding standards, security policies, and compliance requirements
  without requiring individual developer configuration.
- **Private marketplaces** distribute vetted plugins across the organization.
  GitHub Enterprise or internal git hosting serves as the distribution layer.
- **MCP servers** provide controlled access to internal APIs, databases, and
  cloud services. Use Streamable HTTP transport for cloud-native deployments.
- **Hook-based governance** enforces compliance. Block access to production
  databases, require approval for destructive operations, audit tool usage.
- **Agent teams** (when stable) enable parallelism across large codebases.

---

## 6. Cross-Surface Strategy

Claude runs on six surfaces: CLI (terminal), Desktop, Cowork, Claude.ai (web),
Agent SDK (Python/TypeScript), and VS Code. Each exposes a different subset of
capabilities.

### Compatibility Summary

The CLI is the most capable surface. Desktop and VS Code support most features
except MCP App interactive rendering. Claude.ai requires HTTP transport for MCP
servers but supports MCP App UIs. The Agent SDK provides programmatic access but
lacks interactive commands. Cowork is currently the only non-web surface that
renders MCP App UIs.

Critical gaps:

- **MCP App interactive UI** renders only on Cowork and Claude.ai (HTTP).
  CLI, Desktop, SDK, and VS Code receive text fallback only.
- **Hooks** work on CLI, SDK, and VS Code. Desktop and Claude.ai do not
  support them.
- **Agent Teams** work on CLI and SDK only.
- **LSP Servers** work on CLI and VS Code only.
- **Skills** work everywhere except Claude.ai (which does not load
  project-scoped files).

### Design Principles for Maximum Reach

1. **Text-first design.** Every extension should produce useful text output.
   Interactive UIs are enhancements, not requirements. Use `renderData` to
   attach structured data alongside text for hosts that support rendering.
2. **Transport-agnostic servers.** Build MCP servers that work over both
   stdio (local development, CLI, Desktop) and Streamable HTTP (Claude.ai,
   cloud deployment). The SDK handles both; the server code stays the same.
3. **Graceful degradation.** MCP Apps should detect their rendering context
   and adjust. If running in text-only mode, return formatted markdown. If
   running in an iframe, render the full interactive UI.
4. **Avoid surface-specific logic in skills.** Skills should describe what
   to do, not how to render it. Let the surface handle presentation.
5. **Test on CLI first.** The CLI supports every feature except interactive
   MCP App rendering. If it works on CLI, it works almost everywhere.

See [cross_surface_compatibility.md](../analysis/cross_surface_compatibility.md)
for the full feature compatibility matrix and transport requirements.

---

## 7. MCP Ecosystem

### Protocol Overview

The Model Context Protocol is a JSON-RPC 2.0 based standard for connecting AI
applications to external tools and data sources. It defines three primitives:

- **Tools** (model-controlled) -- functions the LLM can invoke. Analogous to
  POST endpoints. Each has a name, description, input schema, and optional
  output schema with annotations (read-only, destructive, idempotent).
- **Resources** (user-controlled) -- data the user selects to include in
  context. Analogous to GET endpoints. Support URI templates, subscriptions,
  and pagination.
- **Prompts** (user-invoked) -- reusable LLM interaction templates triggered
  via slash commands.

Two transport mechanisms: **stdio** for local servers (spawned as child
processes, communicating over stdin/stdout) and **Streamable HTTP** for remote
servers (HTTP POST with optional SSE streaming, session management, and
resumability). SSE transport is deprecated.

### The Three-Entity Model for MCP Apps

MCP Apps introduce a three-entity architecture:

1. **Server** -- a standard MCP server that declares tools and `ui://` resources.
   The `registerAppTool` helper links a tool to a UI resource so that tool
   results trigger UI rendering.
2. **Host** -- the chat client (Claude Code, Claude Desktop, Cowork, etc.)
   that connects to servers, embeds Views in sandboxed iframes, and proxies
   communication between View and Server via `AppBridge`.
3. **View** -- the UI running inside a sandboxed iframe. Built with React or
   vanilla HTML/JS. Communicates with the Host via `PostMessageTransport`.
   Can call server tools, send messages to the conversation, and request
   display mode changes (inline, fullscreen, picture-in-picture).

### When to Add UI vs Stay Text-Only

Add a UI when:
- The data is inherently visual (charts, graphs, spatial layouts, trees).
- The workflow requires interactive input (forms, configuration wizards).
- Real-time monitoring or dashboards are needed.

Stay text-only when:
- The output is naturally textual (code, logs, reports).
- Maximum surface compatibility is required.
- The extension must work in headless/SDK mode.

Always implement a text fallback. The `hasUiCapability()` function from the
ext-apps SDK detects whether the connected host supports MCP App rendering.

See [mcp_protocol_and_servers.md](../analysis/mcp_protocol_and_servers.md) and
[mcp_apps_and_ui_development.md](../analysis/mcp_apps_and_ui_development.md)
for full protocol details and SDK references.

---

## 8. The Maintenance Problem

### Why Things Rot

Skills encode knowledge about external systems: API calling conventions,
documentation structures, best practices, and upstream library interfaces.
These sources change independently of the skills that reference them:

- **Upstream API changes.** A library renames a function, deprecates a
  parameter, or changes its return type. The skill's instructions become
  wrong.
- **Documentation drift.** Official docs update with new best practices,
  new fields, or revised recommendations. The skill teaches outdated
  patterns.
- **Spec evolution.** The Agent Skills specification adds new frontmatter
  fields or tightens validation rules. Skills that passed validation last
  month now fail.
- **Platform changes.** Claude Code adds new features (hooks, agent teams,
  MCP Apps). Skills that do not reference these features miss optimization
  opportunities.

Without monitoring, skills degrade silently. Users follow stale instructions,
produce incorrect output, and lose trust in the skill system.

### The CDC Pipeline

This repository implements a three-layer Change Data Capture pipeline to detect
and classify upstream changes:

1. **Detect** -- HEAD request on `llms-full.txt` (Mintlify's clean markdown
   export of documentation sites). Compare `Last-Modified` header to stored
   watermark. Zero bytes transferred if unchanged.
2. **Identify** -- If the watermark changed, fetch the full content. Split
   by `Source:` delimiters, hash each watched page independently, compare
   to stored per-page hashes.
3. **Classify** -- Run keyword heuristics on the diff text. Categorize as
   breaking (API removal, field rename), additive (new feature, new field),
   or cosmetic (typo fix, formatting change).

For source code monitoring, `source_monitor.py` shallow-clones configured
repositories, extracts commits since the last check, parses Python files via
AST to detect API changes, and scans commit messages for deprecation keywords.

### The Closed Loop

Detection feeds into application:

```
detect -> identify -> classify -> apply -> validate -> human review
```

`apply_updates.py` supports three modes: `report-only` (show what would
change), `apply-local` (update files, create backups, validate with
`skills-ref`), and `create-pr` (branch, commit, open a pull request).
The system never auto-commits. Human review is always the final gate.

Staleness tracking via `check_freshness.py` reads `state.json` timestamps
and warns if a skill has not been checked in N days. Runs in under 100ms
and never blocks skill invocation.

See [self_updating_system_design.md](../analysis/self_updating_system_design.md)
for the full source inventory and change detection strategies.

---

## 9. Forward-Looking

### Agent Teams Evolution

Agent teams are currently experimental, with limited documentation and
support only on CLI and SDK surfaces. As they mature, expect:

- Persistent task boards with cross-session state.
- Richer coordination primitives beyond `TeammateIdle` and `TaskCompleted`
  hooks.
- Integration with managed settings for enterprise-scale task distribution.
- UI surfaces in Cowork and Desktop for monitoring team progress.

Agent teams represent the path from single-session agents to sustained,
multi-session workflows. The `subagents_and_agent_teams.md` report covers
the current state in detail.

### MCP Apps Maturation

MCP Apps (SEP-1865) stabilized in January 2026, but adoption is early.
Expected developments:

- Broader host support. Currently only Cowork and Claude.ai (HTTP) render
  interactive UIs. Desktop, VS Code, and CLI are likely to add iframe
  rendering.
- Richer communication primitives. The current `callServerTool` and
  `sendMessage` API covers core use cases, but streaming data updates and
  bidirectional eventing will grow.
- Template and component libraries. The community is building reusable
  React components for common patterns (data tables, charts, forms).
- Convergence of the two SDK paths (ext-apps and mcp-ui) into a single
  recommended approach.

### Agent SDK Integration

The Claude Agent SDK (Python and TypeScript) packages the same agent loop
that powers Claude Code as embeddable libraries. This enables:

- Custom agent applications with full tool control.
- Headless automation pipelines with structured output.
- Integration with existing orchestration systems (Airflow, Temporal, etc.).
- Programmatic access to skills, agents, and MCP servers without the CLI.

The SDK's `-p` (print) mode and `--output-format json` support are already
production-ready for batch processing.

### Protocol Evolution

MCP protocol versions use date-based format (currently 2025-11-25). Active
areas of development include:

- **Authentication standardization.** OAuth 2.1 / PKCE flow is documented
  but adoption varies across servers and hosts.
- **Registry infrastructure.** mcp.so, Smithery, Glama, PulseMCP, and
  opentools.ai provide discoverability. An official registry API is expected.
- **Elicitation.** Server-initiated requests for user input (URLs,
  credentials, configuration) via `elicitation/create`.
- **Completions.** Auto-complete support for resource URIs and prompt
  arguments via `completion/complete`.

---

## 10. This Repo as Reference Implementation

fb-claude-skills demonstrates most patterns described in this synthesis.
The following table maps architectural patterns to their concrete
implementations in this repository.

| Pattern | Implementation | Location |
|---------|---------------|----------|
| Plugin structure with manifest | Every plugin has `.claude-plugin/plugin.json`, auto-discovered skills, and optional agents/hooks | `mcp-apps/`, `plugin-toolkit/`, `web-tdd/`, `cogapp-markdown/`, `tui-design/`, `mece-decomposer/`, `dimensional-modeling/` |
| Marketplace distribution | Root marketplace catalog lists all installable plugins | `.claude-plugin/marketplace.json` |
| Multi-plugin monorepo | Single repo contains marketplace + all plugin directories using relative source paths | Repository root |
| Progressive disclosure | Frontmatter for routing, SKILL.md body for instructions, `references/` for detailed docs | All skills follow this pattern |
| Skills with agents | Plugin-toolkit bundles skills alongside scanner and quality-checker subagents | `plugin-toolkit/agents/` |
| MCP server in a plugin | mece-decomposer includes `.mcp.json` for stdio server auto-start | `mece-decomposer/.mcp.json` |
| MCP App with text fallback | mece-decomposer includes React tree visualizer as an MCP App | `mece-decomposer/mcp-app/` |
| Commands (slash invocation) | mece-decomposer provides decompose, interview, validate, export commands | `mece-decomposer/commands/` |
| CDC docs monitoring | Three-layer pipeline: watermark, per-page hash, keyword classification | `skill-maintainer/scripts/docs_monitor.py` |
| CDC source monitoring | Git-based: shallow clone, commit extraction, AST parsing, deprecation scanning | `skill-maintainer/scripts/source_monitor.py` |
| Closed-loop updates | detect -> classify -> apply -> validate with skills-ref -> human review | `skill-maintainer/scripts/apply_updates.py` |
| Dimensional model for state | DuckDB star schema with SCD Type 2, MD5 surrogate keys, session events | `skill-maintainer/scripts/store.py` |
| Freshness checking | Timestamp-based staleness detection, under 100ms, never blocking | `skill-maintainer/scripts/check_freshness.py` |
| Source registry | YAML config mapping sources to skills with detection methods | `skill-maintainer/config.yaml` |
| Spec validation | All skills validated against Agent Skills spec via skills-ref | `coderef/agentskills/skills-ref/` |
| Self-referential maintenance | skill-maintainer monitors its own upstream sources and maintains itself | `skill-maintainer/config.yaml` (self-entry) |
| Selection under constraint | Decompose, route, prune, synthesize, verify -- applied at every system level | `docs/analysis/abstraction_analogies.md` |
| Database analogy | Skills as view definitions + stored procedures; context window as temp table | `docs/analysis/abstraction_analogies.md` |
| Auto memory | Claude maintains MEMORY.md with project patterns, key file paths, conventions, and gotchas for cross-session persistence | `~/.claude/projects/.../memory/MEMORY.md` |
| Project memory | CLAUDE.md at project root with full architecture, conventions, and documentation index | `CLAUDE.md` |

### Three-Repo Architecture

This repository is one component of a three-repo system:

- **star-schema-llm-context/** -- Storage engine / kernel. I/O, schema,
  key generation. The shared DuckDB library.
- **fb-claude-skills/** -- Stored procedures / system catalog. Business
  logic, skills, maintenance automation. This repo.
- **ccutils/** and consumers -- Client applications. Orchestration,
  dashboards, CLI tools.

The database analogy holds: star-schema provides the storage layer,
fb-claude-skills defines the procedures and views, and ccutils is the
application layer that queries both.

---

## 11. Report Index

### Existing Analysis Reports

These reports were created during earlier phases of the project and cover
foundational topics: skill design, CDC architecture, dimensional modeling,
and the unifying abstraction framework.

| Report | File | Description |
|--------|------|-------------|
| Skills Guide (Structured) | [skills_guide_structured.md](../analysis/skills_guide_structured.md) | Verbatim structured extraction from "The Complete Guide to Building Skills for Claude" (Anthropic, January 2026). Ground truth for change detection. |
| Skills Best Practices | [claude_skills_best_practices_guide_full_report.md](../analysis/claude_skills_best_practices_guide_full_report.md) | Full analysis of the Anthropic skills guide: fundamentals, planning, testing, distribution, patterns, and troubleshooting. Distilled best practices. |
| Skills Guide Gap Analysis | [skills_guide_analysis.md](../analysis/skills_guide_analysis.md) | Gap analysis comparing guide recommendations against actual repo state. Actionable findings for each skill module. |
| Self-Updating System Design | [self_updating_system_design.md](../analysis/self_updating_system_design.md) | Source inventory, change detection strategies, and mapping to skill components. Architecture of the CDC pipeline. |
| Data-Centric Agent State | [data_centric_agent_state_research.md](../analysis/data_centric_agent_state_research.md) | Research on DuckDB-backed star schema for agent state management. Context window economics, temporal queries, cross-session intelligence. |
| DuckDB Dimensional Model | [duckdb_dimensional_model_strategy.md](../analysis/duckdb_dimensional_model_strategy.md) | Strategic analysis of Kimball-style dimensional modeling for LLM agent systems. SCD Type 2, session events, token budget tracking. |
| Abstraction Analogies | [abstraction_analogies.md](../analysis/abstraction_analogies.md) | The database analogy (skills as views + stored procedures), routing spine (decompose/route/prune/synthesize/verify), selection under constraint. |

### New Domain Reports

These reports cover the seven remaining extension system domains, each
analyzed from primary sources and cross-referenced against implementations
in this repository.

| Report | File | Description |
|--------|------|-------------|
| Plugin System Architecture | [plugin_system_architecture.md](../analysis/plugin_system_architecture.md) | Plugin anatomy, plugin.json schema, all six component types, auto-discovery rules, namespacing, development workflow, and audit of every plugin in this repo. |
| Hooks System Patterns | [hooks_system_patterns.md](../analysis/hooks_system_patterns.md) | All 14 hook events, three handler types (command/prompt/agent), matcher patterns, resolution flow, decision control, async hooks, security patterns, and anti-patterns. |
| Marketplace Distribution | [marketplace_distribution_patterns.md](../analysis/marketplace_distribution_patterns.md) | marketplace.json schema, five source types, version management, multi-plugin monorepo patterns, enterprise governance, and fb-claude-skills case study. |
| MCP Apps and UI Development | [mcp_apps_and_ui_development.md](../analysis/mcp_apps_and_ui_development.md) | Official MCP Apps SDK (ext-apps) and MCP UI SDK. Three-entity model, React integration, bundling, CSP security, testing, host compatibility, graceful degradation. |
| Subagents and Agent Teams | [subagents_and_agent_teams.md](../analysis/subagents_and_agent_teams.md) | Built-in agents, custom agent creation, tool control, model selection, persistent memory, hooks integration, and experimental agent teams. |
| Cross-Surface Compatibility | [cross_surface_compatibility.md](../analysis/cross_surface_compatibility.md) | Six surfaces (CLI, Desktop, Cowork, Claude.ai, SDK, VS Code), feature compatibility matrix, transport requirements, and design principles for maximum reach. |
| MCP Protocol and Servers | [mcp_protocol_and_servers.md](../analysis/mcp_protocol_and_servers.md) | JSON-RPC 2.0 wire format, three primitives, transport mechanisms, authentication (OAuth 2.1), SDK implementations, testing infrastructure, and registry ecosystem. |
| Memory and Rules System | [memory_and_rules_system.md](../analysis/memory_and_rules_system.md) | Six-level memory hierarchy, auto memory storage and behavior, CLAUDE.md import syntax, `.claude/rules/` modular path-scoped rules, organization-level management, and how this repo uses memory. |

### Synthesis

| Report | File | Description |
|--------|------|-------------|
| Claude Ecosystem Synthesis | [claude_ecosystem_synthesis.md](claude_ecosystem_synthesis.md) | This document. Unified view tying together all 14 analysis reports with architectural guidance, decision trees, maturity assessments, and forward-looking analysis. |
