last updated: 2026-02-19

# MCP Ecosystem Audit: fb-claude-skills vs. Claude Code Primitives

Scope: All 7 installable plugins + skill-maintainer (project-scoped) audited against the 4-layer ecosystem model, new Claude Code docs, and Agent Skills best practices.

Sources consulted:
- All SKILL.md files and plugin.json manifests
- `docs/claude-docs/claude_docs_skills.md` (new primitives: allowed-tools, context: fork, dynamic injection, ultrathink)
- `docs/claude-docs/claude_docs_sub-agents.md` (subagent config)
- `docs/claude-docs/claude_docs_hooks-guide.md` (hook events, skill-scoped hooks)
- `docs/analysis/claude_skills_best_practices_guide_full_report.md` (trigger phrase quality)
- mece-decomposer MCP App implementation (server.ts, mcp-app directory)

---

## 1. Executive Summary

### Health scores by plugin

| Plugin | L2 Primitives | L3 MCP App | L4 Distribution | Trigger Quality | New Primitives | Overall |
|--------|:-------------:|:----------:|:---------------:|:---------------:|:--------------:|:-------:|
| mece-decomposer | A | A | A | A | D | B+ |
| skill-maintainer | D | D | N/A (project) | A | D | C |
| plugin-toolkit | D | D | B | B | D | C- |
| mcp-apps | D | D | B | A | D | C |
| dimensional-modeling | D | D | B | B | D | C- |
| tui-design | D | D | B | B | D | C- |
| web-tdd | D | D | B | B | D | C- |
| cogapp-markdown | D | D | B | C | D | D+ |

**L2**: MCP tools/resources/prompts. **L3**: MCP App (interactive UI). **L4**: Plugin distribution conformance. **New Primitives**: allowed-tools, context: fork, dynamic injection, ultrathink.

### Overall assessment

The repo has one fully realized plugin (mece-decomposer) and seven plugins that use only Layer 1 (skill descriptions loaded into context). The distribution layer is clean and consistent. The critical gap is that new Claude Code primitives (allowed-tools, sub-agent execution, dynamic context injection, ultrathink, skill-scoped hooks) are unused across all plugins. This is not a blocking problem today, but as the ecosystem matures these primitives will become table stakes for quality plugins.

---

## 2. Layer-by-Layer Breakdown

### Layer 1: Skill descriptions and SKILL.md content

Status: **Implemented across all plugins.**

All 7 installable plugins have well-formed SKILL.md files with frontmatter. The Agent Skills spec (name, description, metadata.author, metadata.version) is consistently followed. Progressive disclosure via `references/` is used in 6 of 7 plugins (cogapp-markdown has no references directory -- acceptable for its scope).

Gaps at this layer:
- No skill uses `allowed-tools` frontmatter (undeclared tool intent)
- No skill uses `disable-model-invocation: true` (all skills can auto-trigger -- some should not)
- No skill uses `user-invocable: false` (no background-knowledge-only skills)
- No skill uses `model` field (all inherit main model -- costly for haiku-eligible operations)
- No skill uses `hooks` in frontmatter (skill lifecycle hooks entirely unused)

### Layer 2: MCP Primitives (tools, resources, prompts)

Status: **Implemented in mece-decomposer only. Missing from 5 of 7 installable plugins.**

mece-decomposer registers 4 tools with correct visibility scoping:
- `mece-decompose`: visibility `["model","app"]` -- callable by model and app
- `mece-validate`: visibility `["model","app"]` -- callable by model and app
- `mece-refine-node`: visibility `["app"]` -- UI-only, not model-invoked
- `mece-export-sdk`: visibility `["model","app"]` -- callable by model and app

The remaining 5 plugins (web-tdd, cogapp-markdown, tui-design, dimensional-modeling, plugin-toolkit) have no MCP primitives. They teach concepts but Claude cannot use those concepts as callable tools -- all interaction requires a human invoking a skill command.

skill-maintainer runs all operations as Python CLI subprocesses. No MCP tool surface exists.

### Layer 3: MCP Apps (interactive UI)

Status: **Implemented in mece-decomposer only.**

mece-decomposer includes a complete React MCP App:
- `registerAppTool` + `registerAppResource` pattern correctly implemented
- `structuredContent` + text `content` fallback on all tools (CLI-safe)
- `applyDocumentTheme`, `applyHostStyleVariables`, `applyHostFonts` via `onhostcontextchanged`
- `safeAreaInsets` handling on `onhostcontextchanged`
- Visibility-based rendering (IntersectionObserver for expensive renders)
- Bundled CJS at `mcp-app/dist/index.cjs` -- no node_modules at runtime
- Vite + `vite-plugin-singlefile` for single-file HTML bundle

No other plugin has a Layer 3 component.

### Layer 4: Plugin distribution

Status: **Clean and consistent across all plugins.**

All 7 installable plugins conform to the plugin structure:
- `plugin-name/.claude-plugin/plugin.json` with name, version, description, author, repository
- Skills in auto-discovered `skills/` directories (no explicit listing in plugin.json)
- Agents in auto-discovered `agents/` directories (plugin-toolkit: 2 agents)
- Root `marketplace.json` lists all 7 plugins with source paths and versions
- Semver consistent between marketplace.json and individual plugin.json files

One gap: `marketplace.json` has no `mcp_capabilities` or `tools` field -- a user browsing the marketplace cannot tell that mece-decomposer has MCP tools without installing it.

---

## 3. Per-Plugin Audit

### mece-decomposer (version 0.2.0)

**What it does**: MECE decomposition of goals, tasks, and workflows. Four slash commands: `/decompose`, `/interview`, `/validate`, `/export`. Interactive tree visualizer as MCP App.

**Primitives used**:
- L1: SKILL.md with 6 trigger phrases, references/ for methodology/rubrics/schema
- L2: 4 MCP tools with correct visibility scoping, MCP resources
- L3: Full React MCP App with theme integration, streaming support, visibility management
- L4: plugin.json + marketplace.json entry, bundled server

**Gaps**:
- No `allowed-tools` in SKILL.md frontmatter (would clarify which tools the skill itself uses)
- No `ultrathink` in skill body (MECE validation and decomposition are good candidates for extended thinking)
- MCP resources exist but are not advertised in SKILL.md as `uri://mece/*` resources
- Validation heuristics live as a file reference, not as a queryable MCP resource
- No Elicitation primitive for ambiguity resolution during decomposition
- No Sampling primitive for model-driven MECE quality scoring

**Assessment**: The most complete plugin in the repo. Serves as the reference implementation for what a full plugin looks like.

---

### skill-maintainer (project-scoped, version 0.2.0)

**What it does**: Change data capture pipeline for monitoring Anthropic docs and Agent Skills spec. Detects changes, classifies them (breaking/additive/cosmetic), validates updated skills, tracks history in DuckDB star schema.

**Primitives used**:
- L1: SKILL.md with good trigger phrases, references/ for best practices and patterns
- L2: None -- all operations are Python CLI via `uv run`
- L3: None
- L4: Not in marketplace (intentional -- project-scoped)

**Gaps**:
- All commands invoke Python scripts via terminal -- no MCP tool surface means skill-maintainer cannot be called from any MCP client other than the local terminal
- No `context: fork` -- check and status commands are read-only and ideal sub-agent candidates
- No dynamic context injection -- `!`uv run check_freshness.py`` would inject live freshness data at skill load
- No DuckDB query results surfaced as MCP resources

**Assessment**: The Python pipeline is the strongest non-MCP component in the repo. The gap is that it can only be used interactively in the same terminal session. Exposing as MCP tools would allow any client to query skill freshness, budget status, and change history.

---

### plugin-toolkit (version 0.1.0)

**What it does**: Analyze, polish, and manage Claude Code plugins. Three commands: `/plugin-toolkit:analyze`, `/plugin-toolkit:polish`, `/plugin-toolkit:feature`. Uses two custom agents (plugin-scanner, quality-checker) for delegation.

**Primitives used**:
- L1: SKILL.md with command descriptions, references/ for templates and checklists
- L2: None
- L3: None
- L4: plugin.json + marketplace.json entry
- Agents: plugin-scanner.md, quality-checker.md (auto-discovered by runtime)

**Gaps**:
- `analyze` and `polish` are read-heavy operations -- `context: fork` + `agent: Explore` would isolate the scanning from the main context
- No `allowed-tools` -- the analyze command only needs read access but can technically use any tool
- Description trigger phrase "plugin analysis" is too generic; no natural-language user phrases
- The agents (plugin-scanner, quality-checker) are correctly declared but their frontmatter format should be audited against the sub-agents spec

**Assessment**: The agent delegation pattern is architecturally correct. The main gaps are frontmatter quality and lack of `context: fork` for isolation.

---

### mcp-apps: create-mcp-app (version 0.1.0)

**What it does**: Guides creation of MCP Apps with interactive UIs. Framework selection, project setup, SDK API patterns, streaming, visibility, fullscreen mode, testing patterns.

**Primitives used**:
- L1: SKILL.md with 6 trigger phrases, good framework decision tree content
- L4: plugin.json + marketplace.json entry

**Gaps**:
- No MCP primitives (meta-ironic: a skill about building MCP Apps does not itself use MCP)
- No `allowed-tools: Bash(npm *)` -- when the skill runs, it will invoke npm but doesn't declare intent
- No `ultrathink` -- framework selection and architecture decisions could benefit
- References are offline copies only; no live SDK version check at skill invocation

**Assessment**: Best trigger phrase quality in the repo for the mcp-apps plugin. Content is comprehensive and well-organized. Gaps are frontmatter completeness, not content.

---

### mcp-apps: migrate-oai-app (version 0.1.0)

**What it does**: Migrates OpenAI Apps SDK applications to MCP Apps SDK. CSP investigation process, CORS configuration, client/server migration mapping tables, before-finishing checklist.

**Primitives used**:
- L1: SKILL.md with 5 specific trigger phrases, detailed CSP/CORS guidance
- L4: plugin.json + marketplace.json entry

**Gaps**:
- Same as create-mcp-app: no `allowed-tools`, no MCP tools
- "Best Practices" section mixes before-finishing checklist with patterns -- could be clearer

**Assessment**: The CSP investigation process is a genuine differentiator (other migration guides skip this). Solid content.

---

### dimensional-modeling (version 0.1.0)

**What it does**: Kimball-style star schema design for DuckDB agent state persistence. 8-step process from business process identification through meta tables. References schema patterns, query patterns, key generation, anti-patterns, DAG execution modeling.

**Primitives used**:
- L1: SKILL.md with 8 trigger phrases including domain-specific terms ("star schema", "SCD Type 2"), references/ with 5 supporting files
- L4: plugin.json + marketplace.json entry

**Gaps**:
- No MCP tools -- cannot generate DDL, query an existing schema, or scaffold a new database
- A `dm-generate-ddl` tool and `dm-query-schema` tool would make this immediately actionable
- No `ultrathink` -- dimensional modeling decisions (grain selection, dimension vs. degenerate) benefit from extended reasoning
- References include a link to the store.py implementation in a GitHub URL -- this is a dead reference for offline use; should point to the local file

**Assessment**: Good trigger phrase coverage. The 8-step process is well-structured. The primary gap is that it only teaches -- it cannot generate or validate DDL.

---

### tui-design (version 0.1.0)

**What it does**: Terminal UI design principles with Rich, Textual, Questionary, Click. Five principles: semantic color, responsive layout, right component for data, visual hierarchy through typography, progressive density.

**Primitives used**:
- L1: SKILL.md with 7 trigger phrases including framework-specific terms, references/ with 4 supporting files
- L4: plugin.json + marketplace.json entry

**Gaps**:
- No MCP tools -- cannot render a sample TUI, validate a Rich component choice, or run `COLUMNS=80` tests
- No `allowed-tools: Bash(python *)` -- the skill recommends running Python scripts to test layouts but doesn't declare this intent
- The anti-patterns reference file is well-positioned but not preloaded

**Assessment**: Solid pedagogical content. Trigger phrases are specific enough to auto-load reliably. Gap is no executable component.

---

### web-tdd (version 0.1.0)

**What it does**: TDD workflow for web applications. Stack selection (React+Node, React+Python, vanilla+Python), E2E with Playwright or Vibium, spec.md discipline, commit strategy.

**Primitives used**:
- L1: SKILL.md with trigger phrases, references/ for project structures and patterns
- L4: plugin.json + marketplace.json entry

**Gaps**:
- No MCP tools -- cannot scaffold test files, run a test suite, or check coverage
- No `allowed-tools` -- the skill runs npm, vitest, playwright, pytest but doesn't declare which
- The "choose Vibium over Playwright" decision tree mentions MCP integration but the skill itself does not use any MCP
- `disable-model-invocation: true` should be considered -- deploying test scaffolding should probably be user-initiated

**Assessment**: Practical content with clear workflow. The Vibium recommendation is appropriate. The main gap is no executable surface.

---

### cogapp-markdown (version 0.1.0)

**What it does**: Teaches cogapp for auto-generating markdown sections. Syntax, common patterns (CLI --help embedding, table generation), GitHub Actions CI integration.

**Primitives used**:
- L1: SKILL.md (no references/ directory)
- L4: plugin.json + marketplace.json entry

**Gaps**:
- Description is the weakest in the repo -- "Use cogapp to auto-generate sections" is accurate but not trigger-phrase optimized
- Missing trigger phrases: "keep docs in sync", "regenerate readme", "embed --help output", "cog -r", "outdated documentation"
- No `allowed-tools: Bash(uv run *)` -- the skill's primary action is running cog via uv
- No references/ directory -- the skill is short enough that this is acceptable, but a `cog_patterns.md` reference with more examples would help
- `pip install cogapp` in the Install section contradicts project convention (always use uv)

**Assessment**: The weakest description quality in the repo. Content is correct. `pip install` line needs to be changed to `uv add cogapp` (or `uv add --dev cogapp`).

---

## 4. New Claude Code Primitives Gap Analysis

The following primitives are documented in the new Claude Code docs but unused in any skill or plugin in this repo:

### allowed-tools

**What it is**: Frontmatter field that declares which tools Claude can use without prompting when this skill is active. Example: `allowed-tools: Bash(npm *), Read, Grep`.

**Current status**: Absent from all 9 SKILL.md files.

**Impact**: Every tool use during skill execution may trigger a permission prompt (depending on user's permission mode). Users running skills like web-tdd or cogapp-markdown will see prompts for every npm or uv run command. Declaring intent also documents the skill's actual tool requirements.

**Which skills need it**:
| Skill | Tools to declare |
|-------|-----------------|
| web-tdd | `Bash(npm *), Bash(npx *), Bash(uv run *)` |
| cogapp-markdown | `Bash(uv run *)` |
| tui-design | `Bash(python *)` |
| skill-maintainer | `Bash(uv run *)` |
| mcp-apps:create-mcp-app | `Bash(npm *), Bash(git *)` |
| mcp-apps:migrate-oai-app | `Bash(npm *)` |
| plugin-toolkit | `Read, Glob, Grep` |

### context: fork + agent

**What it is**: `context: fork` runs the skill in an isolated subagent context. `agent:` selects which subagent type (Explore, general-purpose, Bash, or a custom agent). The subagent has no access to conversation history and returns results to the parent.

**Current status**: Absent from all 9 SKILL.md files.

**Best candidates**:
- `plugin-toolkit:analyze` -- pure exploration, should not modify conversation context
- `skill-maintainer check` and `status` -- read-only monitoring, ideal for isolation
- `web-tdd` project setup phase -- running setup commands in isolation prevents cluttering the main context

**Example for plugin-toolkit**:
```yaml
---
name: plugin-toolkit
context: fork
agent: Explore
allowed-tools: Read, Glob, Grep
---
```

### Dynamic context injection (!`command`)

**What it is**: Backtick syntax `!`command`` executes a shell command before the skill content is sent to Claude. Output replaces the placeholder. This is preprocessing -- Claude sees the result, not the command.

**Current status**: Absent from all 9 SKILL.md files.

**Best candidates**:
- `skill-maintainer`: `!`uv run python skill-maintainer/scripts/check_freshness.py`` would inject current freshness data at skill load, giving Claude actual state instead of static instructions
- `skill-maintainer budget`: `!`uv run python skill-maintainer/scripts/measure_content.py`` would inject live budget measurements
- `mece-decomposer:validate`: Could inject current DuckDB state

**Example for skill-maintainer**:
```
## Current Freshness State
!`uv run python skill-maintainer/scripts/check_freshness.py`

## Your task
Review the above freshness data and...
```

### Extended thinking (ultrathink)

**What it is**: Including the word `ultrathink` anywhere in skill content enables extended thinking mode for that skill invocation.

**Current status**: Absent from all 9 SKILL.md files.

**Best candidates**:
- `mece-decomposer`: Decomposition dimension selection, MECE boundary validation, grain-level arbitration all benefit from extended reasoning chains
- `skill-maintainer update`: Change classification (breaking vs. additive) and patch generation require careful multi-step reasoning
- `dimensional-modeling`: Grain selection and dimension vs. degenerate dimension decisions are non-obvious trade-offs

**Risk**: ultrathink increases latency and cost. Apply only to complex decision-making steps, not to reference lookup steps.

### Skill-scoped hooks

**What it is**: `hooks:` in skill frontmatter defines hooks that only fire during that skill's execution. Events: `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`.

**Current status**: Absent from all 9 SKILL.md files.

**Best candidates**:
- `skill-maintainer`: PostToolUse hook to log all file writes to the JSONL buffer for audit trail
- `web-tdd`: PreToolUse hook to prevent `git push` during TDD workflow (enforce manual push discipline)
- `plugin-toolkit:analyze`: Stop hook to confirm analysis docs were written before exiting

**Example for web-tdd**:
```yaml
hooks:
  PreToolUse:
    - matcher: Bash(git push*)
      command: echo "web-tdd: push is manual -- review commits first" && exit 1
```

### model field

**What it is**: Selects which Claude model runs when a skill is active. Useful for routing haiku-eligible operations to cheaper/faster models.

**Current status**: Absent from all 9 SKILL.md files.

**Best candidates**:
- `skill-maintainer status`: Freshness display is a haiku-eligible lookup with no complex reasoning
- `plugin-toolkit:analyze` (scan phase): Structural inventory is mechanical, not reasoning-intensive
- Any skill where `context: fork` is added -- subagent model can be independently controlled

---

## 5. Skill Description / Trigger Phrase Quality Assessment

Descriptions must include natural-language phrases users would actually say. Without them, Claude cannot auto-load the skill when relevant.

### A tier: specific and trigger-complete

**mece-decomposer**:
> "MECE decomposition methodology, scoring rubrics, and Agent SDK mapping for process analysis. Loaded automatically when decomposing goals, tasks, processes, or workflows... Use when user says 'decompose', 'break down this process', 'MECE analysis', 'interview me about a workflow', 'map process to agents', 'validate decomposition', or 'export to Agent SDK'."

Passes: 6 explicit trigger phrases, domain-specific terminology, clear scope.

**skill-maintainer**:
> "Monitors upstream documentation... Use when user says 'check for skill updates', 'are my skills current', 'update skills', 'token budget', 'skill history'..."

Passes: 5 trigger phrases, action-oriented, specific commands listed.

**mcp-apps:create-mcp-app**:
> "...when the user asks to 'create an MCP App', 'add a UI to an MCP tool', 'build an interactive MCP View', 'scaffold an MCP App'..."

Passes: 4 exact user phrases, good coverage.

### B tier: good but room for improvement

**dimensional-modeling**:
> "...triggers on 'star schema', 'dimensional model', 'DuckDB schema', 'fact table', 'dimension table', 'SCD Type 2', 'surrogate keys', 'data warehouse for agents'."

Passes: 8 technical terms. Gap: no user-action phrases ("design a schema for", "help me track", "I need to store agent state"). A user who doesn't know the terminology won't trigger it.

**tui-design**:
> "...Triggers on 'terminal UI', 'TUI', 'Rich table', 'CLI output', 'terminal dashboard', 'questionary prompt', 'make this look better in the terminal'."

Passes: 7 trigger phrases including one natural user phrase ("make this look better in the terminal"). Solid.

**web-tdd**:
> "TDD workflow for web applications with Vitest... Use when building web apps, adding tests to existing projects, or implementing features with test-driven development."

Partial: situation-based ("when building web apps") without user phrases. Missing: "write tests for", "add Playwright", "test-first", "red-green-refactor".

**plugin-toolkit**:
> "Analyze, polish, and manage Claude Code plugins. Use when user wants to evaluate a plugin (/plugin-toolkit:analyze), add standard utility commands (/plugin-toolkit:polish)..."

Partial: references slash commands, not user phrases. Missing: "review my plugin", "add help command to", "check plugin quality", "what's wrong with my plugin".

### C/D tier: needs revision

**cogapp-markdown**:
> "Use cogapp to auto-generate sections of markdown documentation by embedding Python code... Use when a project needs to keep documentation in sync with code..."

Fails: situation-based without user phrases. Missing: "keep my readme updated", "regenerate docs", "embed --help output", "run cog -r", "documentation is out of date", "sync docs with code".

**mcp-apps:migrate-oai-app**:
> "...when the user asks to 'migrate from OpenAI Apps SDK', 'convert OpenAI App to MCP', 'port from window.openai', 'migrate from skybridge', 'convert openai/outputTemplate'..."

Passes: 5 specific phrases. Gap: the `skybridge` term is unfamiliar to most users; "convert from OpenAI tool UI" would be more natural.

### Description improvement formula

Pattern: `[primary action verb] + [what it operates on] + [specific user trigger phrases in quotes]`

Apply to all B/C/D tier skills before the P1 work begins.

---

## 6. Prioritized Backlog

### P0: Quick wins -- pure SKILL.md/frontmatter edits (< 30 min each, no new code)

| ID | Item | File | Effort |
|----|------|------|--------|
| P0-1 | Add `allowed-tools` to web-tdd (`Bash(npm *), Bash(npx *), Bash(uv run *)`) | `web-tdd/skills/web-tdd/SKILL.md` | XS |
| P0-2 | Add `allowed-tools: Bash(uv run *)` to cogapp-markdown | `cogapp-markdown/skills/cogapp-markdown/SKILL.md` | XS |
| P0-3 | Add `allowed-tools: Bash(uv run *)` to skill-maintainer | `skill-maintainer/SKILL.md` | XS |
| P0-4 | Add `allowed-tools: Bash(npm *), Bash(git *)` to mcp-apps skills | `mcp-apps/skills/*/SKILL.md` (2 files) | XS |
| P0-5 | Add `allowed-tools: Read, Glob, Grep` to plugin-toolkit | `plugin-toolkit/skills/plugin-toolkit/SKILL.md` | XS |
| P0-6 | Add `ultrathink` to mece-decomposer skill body (decomposition and validation sections) | `mece-decomposer/skills/mece-decomposer/SKILL.md` | XS |
| P0-7 | Add `ultrathink` to skill-maintainer (update/classify sections) | `skill-maintainer/SKILL.md` | XS |
| P0-8 | Add `ultrathink` to dimensional-modeling (grain selection section) | `dimensional-modeling/skills/dimensional-modeling/SKILL.md` | XS |
| P0-9 | Fix cogapp-markdown description: add trigger phrases ("keep docs in sync", "regenerate readme", "embed --help output", "cog -r", "documentation out of date") | `cogapp-markdown/skills/cogapp-markdown/SKILL.md` | XS |
| P0-10 | Fix cogapp-markdown: change `pip install cogapp` to `uv add --dev cogapp` | `cogapp-markdown/skills/cogapp-markdown/SKILL.md` | XS |
| P0-11 | Add trigger phrases to plugin-toolkit description ("review my plugin", "add help command", "check plugin quality") | `plugin-toolkit/skills/plugin-toolkit/SKILL.md` | XS |
| P0-12 | Add user-action trigger phrases to web-tdd description ("write tests for", "add Playwright", "test-first") | `web-tdd/skills/web-tdd/SKILL.md` | XS |
| P0-13 | Add trigger phrases to dimensional-modeling description ("design a schema for", "help me track agent state", "store execution data") | `dimensional-modeling/skills/dimensional-modeling/SKILL.md` | XS |
| P0-14 | Add `disable-model-invocation: true` to skill-maintainer update/add-source commands (side-effect operations) | `skill-maintainer/SKILL.md` (command-level) | S |
| P0-15 | Fix dimensional-modeling store.py reference: change GitHub URL to relative local path | `dimensional-modeling/skills/dimensional-modeling/SKILL.md` | XS |

### P1: Medium effort -- structural improvements (1-4 hours each)

| ID | Item | File(s) | Effort |
|----|------|---------|--------|
| P1-1 | Add `context: fork` + `agent: Explore` to plugin-toolkit (scan phase is read-only exploration) | `plugin-toolkit/skills/plugin-toolkit/SKILL.md` | S |
| P1-2 | Add dynamic context injection to skill-maintainer (`!`uv run check_freshness.py`` at skill load) | `skill-maintainer/SKILL.md` | S |
| P1-3 | Add dynamic context injection to skill-maintainer budget command (`!`uv run measure_content.py``) | `skill-maintainer/SKILL.md` | S |
| P1-4 | Add `hooks: PreToolUse` to web-tdd (block `git push` during skill execution, enforce manual push) | `web-tdd/skills/web-tdd/SKILL.md` | M |
| P1-5 | Add `model: claude-haiku-4-5-20251001` to plugin-toolkit (scanner/inventory is mechanical) | `plugin-toolkit/skills/plugin-toolkit/SKILL.md` | XS |
| P1-6 | Audit and update plugin-scanner.md and quality-checker.md agent frontmatter against sub-agents spec | `plugin-toolkit/agents/*.md` | S |
| P1-7 | Add mece-decomposer output schema as a declared MCP resource (uri://mece/output-schema) | `mece-decomposer/mcp-app/server.ts` | M |
| P1-8 | Add validation heuristics as a declared MCP resource (uri://mece/validation-heuristics) | `mece-decomposer/mcp-app/server.ts` | M |
| P1-9 | Add `mcp_capabilities` and `tools` fields to marketplace.json entries that have MCP tools | `.claude-plugin/marketplace.json` | S |

### P2: High effort -- new MCP primitives or new MCP Apps (1-3 days each)

| ID | Item | Complexity |
|----|------|-----------|
| P2-1 | skill-maintainer MCP tools: `skill-check`, `skill-budget`, `skill-history` (expose Python pipeline as MCP tools) | High |
| P2-2 | skill-maintainer MCP App: budget dashboard with change timeline (React, reads DuckDB via tool) | Very High |
| P2-3 | plugin-toolkit MCP tool: `plugin-audit` (structural scan returning JSON, usable from any MCP client) | High |
| P2-4 | dimensional-modeling MCP tools: `dm-generate-ddl` (takes business process description, returns DuckDB DDL) | Medium |
| P2-5 | dimensional-modeling MCP tool: `dm-query-schema` (introspect existing DuckDB file) | Medium |
| P2-6 | web-tdd MCP tool: `tdd-scaffold` (generate test file + component stub from a feature description) | High |

### P3: Architectural / exploratory (research + design first)

| ID | Item | Notes |
|----|------|-------|
| P3-1 | Convert mece-decomposer validation from `uv run python` subprocess to inline TypeScript | Removes Python runtime dependency from MCP server; bundled JSON Schema validation instead |
| P3-2 | Add Elicitation primitive to mece-decomposer for ambiguity resolution during decomposition | Requires Elicitation API support in host (Claude Desktop, Cowork) |
| P3-3 | Add Sampling to mece-validate for model-driven MECE quality scoring (vs. deterministic only) | Claude-as-judge pattern via Sampling; complements deterministic structural validation |
| P3-4 | heylook-monitor: convert from standalone MCP App to installable plugin | Currently project-scoped; generalizing as a plugin enables reuse for other local LLM servers |
| P3-5 | Add agent teams support to skill-maintainer (parallel doc monitoring + source monitoring as separate agents) | Currently sequential; parallelizing via agent teams would reduce check latency |

---

## 7. Quick-Win Checklist

Copy-paste actionable items -- pure SKILL.md text edits, no new code, no new files. Do these in a single session.

### Step 1: cogapp-markdown description and pip fix

File: `cogapp-markdown/skills/cogapp-markdown/SKILL.md`

Change frontmatter `description` to:
```
description: Auto-generate and keep markdown documentation in sync with code using cogapp. Use when user says "keep docs in sync", "regenerate readme", "embed --help output", "run cog -r", "documentation is out of date", "sync CLI help into README", or when a project generates markdown from code.
```

Change line in Install section:
```bash
# before
pip install cogapp
# after
uv add --dev cogapp
```

### Step 2: allowed-tools for all skills

Add to each SKILL.md frontmatter:

- `web-tdd/skills/web-tdd/SKILL.md`: `allowed-tools: Bash(npm *), Bash(npx *), Bash(uv run *)`
- `cogapp-markdown/skills/cogapp-markdown/SKILL.md`: `allowed-tools: Bash(uv run *)`
- `skill-maintainer/SKILL.md`: `allowed-tools: Bash(uv run *)`
- `mcp-apps/skills/create-mcp-app/SKILL.md`: `allowed-tools: Bash(npm *), Bash(git *)`
- `mcp-apps/skills/migrate-oai-app/SKILL.md`: `allowed-tools: Bash(npm *)`
- `plugin-toolkit/skills/plugin-toolkit/SKILL.md`: `allowed-tools: Read, Glob, Grep`
- `mece-decomposer/skills/mece-decomposer/SKILL.md`: `allowed-tools: Bash(uv run *)`

### Step 3: ultrathink in three skills

- `mece-decomposer/skills/mece-decomposer/SKILL.md`: In the "Dimension Selection" section, add a sentence: "When selecting the decomposition dimension and validating MECE boundaries, use ultrathink to reason through all candidate dimensions and boundary cases."
- `skill-maintainer/SKILL.md`: In the update command section, add: "When classifying changes as breaking vs. additive, use ultrathink."
- `dimensional-modeling/skills/dimensional-modeling/SKILL.md`: In Step 2 (Declare the Grain), add: "When choosing between grain levels, use ultrathink to reason through the trade-offs."

### Step 4: trigger phrase improvements

- `plugin-toolkit/skills/plugin-toolkit/SKILL.md`: Append to description: `Also use when user says "review my plugin", "check plugin quality", "what's wrong with my plugin", "add a help command to my plugin", or "improve my plugin structure".`
- `web-tdd/skills/web-tdd/SKILL.md`: Append to description: `Also triggers on "write tests for", "add Playwright", "test first", "red-green-refactor", "add test coverage", or "scaffold tests".`
- `dimensional-modeling/skills/dimensional-modeling/SKILL.md`: Append to description: `Also triggers on "design a schema for", "help me track agent state", "store execution data in DuckDB", "I need to persist", or "how do I model".`

### Step 5: fix dimensional-modeling store.py link

File: `dimensional-modeling/skills/dimensional-modeling/SKILL.md`

Change:
```
Working proof: [fb-claude-skills/skill-maintainer/scripts/store.py](https://github.com/fblissjr/fb-claude-skills/blob/main/skill-maintainer/scripts/store.py)
```
To:
```
Working proof: `skill-maintainer/scripts/store.py` -- the full Kimball schema (v0.6.0) with 3 dimensions, 6 fact tables, analytical views, and automatic schema migration.
```

---

## Appendix: Primitive Coverage Matrix

| Plugin | allowed-tools | context:fork | agent: | ultrathink | hooks | dynamic inject | model | MCP tools | MCP App |
|--------|:------------:|:------------:|:------:|:----------:|:-----:|:--------------:|:-----:|:---------:|:-------:|
| mece-decomposer | - | - | - | - | - | - | - | yes (4) | yes |
| skill-maintainer | - | - | - | - | - | - | - | - | - |
| plugin-toolkit | - | - | - | - | - | - | - | - | - |
| mcp-apps:create | - | - | - | - | - | - | - | - | - |
| mcp-apps:migrate | - | - | - | - | - | - | - | - | - |
| dimensional-modeling | - | - | - | - | - | - | - | - | - |
| tui-design | - | - | - | - | - | - | - | - | - |
| web-tdd | - | - | - | - | - | - | - | - | - |
| cogapp-markdown | - | - | - | - | - | - | - | - | - |

All `-` cells are opportunities. The 15 P0 items alone would fill in 6 columns with 2 hours of SKILL.md edits.
