# mece-decomposer

last updated: 2026-02-18

A plugin for Claude Code and Cowork that decomposes goals, tasks, processes, and workflows into MECE (Mutually Exclusive, Collectively Exhaustive) components. Produces dual output -- a human-readable tree for SME validation and structured JSON that maps directly to Claude Agent SDK primitives for agentic execution. Includes an interactive tree visualizer (MCP App).

## Problem

Business SMEs have tacit knowledge about processes that is stuck in their heads as assumptions. When building agentic workflows with Claude Agent SDK, the hardest part is defining "what good looks like" -- and SMEs can't articulate that without decomposing the process into granular components first.

## What It Does

Takes any input -- a goal, a process description, an SOP, a live conversation with an SME -- and produces:

1. **Human-readable tree** for validation and communication
2. **Structured JSON** that maps directly to Agent SDK primitives (`Agent`, `Runner`, hooks, handoffs)
3. **Interactive visualization** (MCP App) for exploring, validating, and refining the tree

The decomposition itself becomes the shared contract between humans and agents.

## Installation

Works in both **Claude Code** and **Cowork**:

```bash
# Claude Code (CLI or Desktop)
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install mece-decomposer@fb-claude-skills

# Cowork
# Install from plugins UI or:
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mece-decomposer@fb-claude-skills
```

The MCP server starts automatically -- no build step needed. The bundled server is self-contained.

### Development Setup

If you want to modify the MCP App:

```bash
cd mece-decomposer/mcp-app
npm install
npm run dev     # hot reload for UI + server
```

To rebuild the production bundle:

```bash
npm run build   # outputs dist/index.cjs (self-contained) + dist/mcp-app.html
```

## Commands

Invoke these directly as slash commands:

| Command | Purpose |
|---------|---------|
| `/decompose` | Break down a goal, process, or workflow into MECE components with SDK mapping |
| `/interview` | Extract process knowledge from an SME through structured conversation |
| `/validate` | Check a decomposition for MECE compliance and structural integrity |
| `/export` | Generate Agent SDK Python code scaffolding from a validated decomposition |

In Claude Code, these are namespaced: `/mece-decomposer:decompose`, etc.

## Background Skill

The `mece-decomposer` skill loads automatically when the conversation involves process decomposition. It provides:

- MECE decomposition methodology and dimension selection rubrics
- Atomicity criteria and fan-out/depth limits
- ME/CE scoring rubrics with depth-adaptive rigor
- Agent SDK mapping rules
- References to detailed documentation (progressive disclosure)

## Interactive Visualizer (MCP App)

On surfaces that support MCP Apps (Claude Desktop, Cowork, Claude.ai), the decomposition renders as an interactive React UI:

- Collapsible tree with orchestration type and execution type badges
- ME/CE/Overall score gauges
- Click nodes for detail inspection and editing
- Validation panel with clickable issue navigation
- SDK code export preview with copy

| MCP Tool | Visibility | Purpose |
|----------|-----------|---------|
| `mece-decompose` | model + app | Render decomposition as interactive tree |
| `mece-validate` | model + app | Validate and display score gauges + issues |
| `mece-refine-node` | app-only | Edit nodes from the UI |
| `mece-export-sdk` | model + app | Preview generated Agent SDK code |

On CLI (Claude Code terminal), the tools return text summaries.

## Plugin Structure

```
mece-decomposer/
+-- .claude-plugin/
|   +-- plugin.json                                    # Plugin manifest
+-- .mcp.json                                          # MCP server auto-configuration
+-- README.md
+-- commands/                                          # Slash commands (user-invoked)
|   +-- decompose.md                                   # /decompose
|   +-- interview.md                                   # /interview
|   +-- validate.md                                    # /validate
|   +-- export.md                                      # /export
+-- skills/
|   +-- mece-decomposer/
|       +-- SKILL.md                                   # Domain knowledge (auto-loaded)
|       +-- references/
|       |   +-- decomposition_methodology.md           # 8-step procedure
|       |   +-- sme_interview_protocol.md              # 5-phase extraction protocol
|       |   +-- validation_heuristics.md               # ME/CE scoring rubrics
|       |   +-- agent_sdk_mapping.md                   # Tree -> SDK mapping rules
|       |   +-- output_schema.md                       # Full JSON schema
|       +-- scripts/
|           +-- validate_mece.py                       # Deterministic validator
+-- mcp-app/                                           # MCP App (self-contained)
    +-- dist/
    |   +-- index.cjs                                  # Bundled server (committed)
    |   +-- mcp-app.html                               # Bundled React UI (committed)
    +-- server.ts                                      # Source: MCP tools + resources
    +-- main.ts                                        # Source: HTTP/stdio entry point
    +-- src/                                           # Source: React components
    +-- package.json
```

## Example Output

```
Invoice Approval Workflow (sequential)
+-- Invoice Receipt and Logging (sequential)
|   +-- [tool] Extract Invoice Data (~10s, OCR/parse)
|   +-- [agent] Validate Invoice Completeness (~1m, haiku)
|   +-- [agent] Match to Purchase Order (~2m, sonnet)
+-- Review and Approval (conditional)
|   condition: invoice_amount threshold
|   +-- Standard Approval (sequential)        [amount < $5000]
|   |   +-- [agent] Auto-Approve Check (~30s, haiku)
|   |   +-- [human] Manager Sign-Off (~4h, webhook)
|   +-- Escalated Approval (sequential)       [amount >= $5000]
|       +-- [human] Director Review (~8h, webhook)
|       +-- [human] VP Sign-Off (~24h, webhook)
+-- Payment Processing (sequential)
    +-- [agent] Generate Payment Instructions (~1m, sonnet)
    +-- [external] Submit to Payment System (~30s, rest_api)
    +-- [agent] Send Confirmation (~30s, haiku)
```

## Credits

Concept by [Ron Zika](https://www.linkedin.com/in/ronzika/).
