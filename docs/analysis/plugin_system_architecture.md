last updated: 2026-02-19

# Plugin System Architecture

A comprehensive reference for the Claude Code plugin system: anatomy, schema, component types, auto-discovery, namespacing, development workflow, migration, and a real implementation audit of every plugin in this repository.

---

## 1. Overview

Plugins are the distribution and packaging unit for Claude Code extensions. A plugin bundles one or more of five component types -- skills, agents, hooks, MCP servers, and LSP servers -- into a self-contained directory that can be installed, versioned, updated, and shared through marketplaces.

Without plugins, Claude Code extensions live in the `.claude/` directory of a single project. They work, but they cannot travel. A skill in `.claude/skills/review/SKILL.md` is invisible outside that project. A hook in `settings.json` must be manually copied to every repo that needs it.

Plugins solve three problems:

1. **Portability** -- install once, use everywhere. A plugin installed at user scope is available in every project.
2. **Namespacing** -- `/review` becomes `/my-plugin:review`, preventing collisions when multiple extensions define the same skill name.
3. **Versioning** -- semantic versions in `plugin.json` drive the cache and update system. Change the code but not the version, and users never see the update.

The standalone `.claude/` directory remains the right choice for personal, project-scoped, or experimental work. Plugins are for anything that crosses a project boundary.

---

## 2. Plugin Anatomy

### Directory structure

Every plugin is a directory. The only file with a fixed path is the manifest at `.claude-plugin/plugin.json`, and even that is optional (Claude Code can derive the plugin name from the directory name and auto-discover components in default locations).

Standard layout:

```
my-plugin/
  .claude-plugin/
    plugin.json              # Manifest (optional, but recommended)
  skills/                    # Agent Skills (auto-discovered)
    my-skill/
      SKILL.md
      references/            # Supporting files loaded on demand
      scripts/               # Scripts Claude can execute
  commands/                  # Slash commands as simple markdown files (auto-discovered)
    do-thing.md
  agents/                    # Subagent definitions (auto-discovered)
    reviewer.md
  hooks/                     # Event handler configuration (auto-discovered)
    hooks.json
  .mcp.json                  # MCP server definitions (auto-discovered)
  .lsp.json                  # LSP server definitions (auto-discovered)
  scripts/                   # Utility scripts referenced by hooks or skills
  README.md                  # Documentation for users
  CHANGELOG.md               # Version history
```

### Required vs optional files

| File | Required | Purpose |
|------|----------|---------|
| `.claude-plugin/plugin.json` | No | Metadata, component path overrides. If absent, directory name becomes plugin name, and components are discovered in default locations. |
| `skills/<name>/SKILL.md` | No | Agent Skills with frontmatter and markdown instructions. At least one component of any type is needed for the plugin to do anything. |
| `commands/*.md` | No | Legacy skill format (simple markdown files). Still supported, same functionality as skills. |
| `agents/*.md` | No | Subagent definitions with name and description frontmatter. |
| `hooks/hooks.json` | No | Hook configurations triggered by Claude Code events. |
| `.mcp.json` | No | MCP server configurations started when plugin is enabled. |
| `.lsp.json` | No | LSP server configurations for code intelligence. |
| `README.md` | No | Recommended for distribution. |

### Critical constraint

Components must live at the plugin root, never inside `.claude-plugin/`. Only `plugin.json` belongs in `.claude-plugin/`. This is the single most common structural mistake.

```
WRONG:
  .claude-plugin/
    plugin.json
    commands/        <-- will not be discovered
    agents/          <-- will not be discovered

RIGHT:
  .claude-plugin/
    plugin.json
  commands/          <-- at plugin root
  agents/            <-- at plugin root
```

---

## 3. plugin.json Schema

### Required fields

If a manifest is present, only `name` is strictly required:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier in kebab-case. Becomes the namespace prefix for all components. |

### Recommended fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `version` | string | Semantic version. Drives cache invalidation and update detection. | `"1.2.0"` |
| `description` | string | Brief explanation shown in plugin manager. | `"Code review automation"` |
| `author` | object | `{ "name": string, "email"?: string, "url"?: string }` | `{ "name": "Fred Bliss" }` |

### Optional metadata fields

| Field | Type | Description |
|-------|------|-------------|
| `homepage` | string | Documentation URL |
| `repository` | string | Source code URL |
| `license` | string | SPDX identifier (MIT, Apache-2.0, etc.) |
| `keywords` | string[] | Discovery tags |

### Component path fields

These fields point to non-default locations. They supplement auto-discovered defaults; they do not replace them.

| Field | Type | Description |
|-------|------|-------------|
| `commands` | string or string[] | Additional command files/directories |
| `agents` | string or string[] | Additional agent files |
| `skills` | string or string[] | Additional skill directories |
| `hooks` | string, string[], or object | Hook config paths or inline config |
| `mcpServers` | string, string[], or object | MCP config paths or inline config |
| `lspServers` | string, string[], or object | LSP config paths or inline config |
| `outputStyles` | string or string[] | Additional output style files/directories |

### Path rules

- All paths must be relative to plugin root and start with `./`
- Custom paths add to auto-discovered defaults, never replace them
- Multiple paths can be specified as arrays
- `${CLAUDE_PLUGIN_ROOT}` resolves to the absolute path of the installed plugin directory at runtime

### Version precedence

Version can be declared in `plugin.json` and/or in the marketplace entry (`marketplace.json`). When both are present, `plugin.json` wins silently. For relative-path plugins in a marketplace, set the version in the marketplace entry. For all other sources, set it in `plugin.json`.

---

## 4. Component Types

### 4.1 Skills

**What they do**: Extend Claude's knowledge and capabilities. A skill is a markdown file with optional frontmatter that Claude loads into context either automatically (based on description matching) or manually (via `/plugin:skill-name`).

**Location**: `skills/<skill-name>/SKILL.md` (directory per skill) or `commands/<name>.md` (flat file, legacy format).

**Key frontmatter fields**:

| Field | Effect |
|-------|--------|
| `name` | Display name and slash command name |
| `description` | How Claude decides when to auto-load the skill. Must include trigger phrases. |
| `disable-model-invocation` | `true` prevents Claude from auto-loading. User must invoke with `/name`. |
| `user-invocable` | `false` hides from the `/` menu. Claude can still auto-load. |
| `allowed-tools` | Tools Claude can use without permission when skill is active |
| `context` | `fork` runs in an isolated subagent |
| `agent` | Which subagent type to use (Explore, Plan, general-purpose, or custom) |
| `argument-hint` | Shown during autocomplete (e.g., `[issue-number]`) |

**Progressive disclosure**: `SKILL.md` stays under 500 lines. Heavy reference material goes in sibling files (`references/`, `examples/`) and is loaded on demand when Claude encounters a pointer in the main file.

### 4.2 Agents

**What they do**: Define specialized subagents that Claude can delegate tasks to. An agent has its own system prompt, capabilities, and tool access.

**Location**: `agents/<agent-name>.md`

**Format**:
```yaml
---
name: agent-name
description: What this agent specializes in and when to invoke it
---

Detailed system prompt describing role, expertise, and behavior.
```

**Integration points**:
- Appear in the `/agents` interface
- Claude can invoke them automatically based on task context
- Users can invoke manually
- Plugin agents work alongside built-in agents (Explore, Plan, etc.)

### 4.3 Hooks

**What they do**: Execute code in response to Claude Code lifecycle events. Hooks run shell commands, evaluate prompts, or spawn verification agents.

**Location**: `hooks/hooks.json` or inline in `plugin.json` under the `hooks` key.

**Available events**:

| Event | When it fires |
|-------|---------------|
| `PreToolUse` | Before Claude uses any tool |
| `PostToolUse` | After Claude successfully uses a tool |
| `PostToolUseFailure` | After a tool execution fails |
| `PermissionRequest` | When a permission dialog is shown |
| `UserPromptSubmit` | When user submits a prompt |
| `Notification` | When Claude Code sends notifications |
| `Stop` | When Claude attempts to stop |
| `SubagentStart` | When a subagent is started |
| `SubagentStop` | When a subagent attempts to stop |
| `SessionStart` | At the beginning of sessions |
| `SessionEnd` | At the end of sessions |
| `TeammateIdle` | When an agent team teammate is about to go idle |
| `TaskCompleted` | When a task is being marked as completed |
| `PreCompact` | Before conversation history is compacted |

**Hook types**:
- `command` -- execute shell commands or scripts
- `prompt` -- evaluate a prompt with an LLM
- `agent` -- run an agentic verifier with tools

**Example**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh"
        }]
      }
    ]
  }
}
```

### 4.4 MCP Servers

**What they do**: Connect Claude Code with external tools and services via the Model Context Protocol. Plugin MCP servers start automatically when the plugin is enabled.

**Location**: `.mcp.json` at plugin root, or inline in `plugin.json` under `mcpServers`.

**Configuration**:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server",
      "args": ["--stdio"],
      "env": {
        "DATA_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    }
  }
}
```

**Integration**: Server tools appear as standard MCP tools in Claude's toolkit. They integrate seamlessly with Claude's existing tools.

### 4.5 LSP Servers

**What they do**: Provide Language Server Protocol integration for real-time code intelligence: diagnostics, go-to-definition, find-references, hover info.

**Location**: `.lsp.json` at plugin root, or inline in `plugin.json` under `lspServers`.

**Required fields**:

| Field | Description |
|-------|-------------|
| `command` | LSP binary to execute (must be in PATH) |
| `extensionToLanguage` | Maps file extensions to language identifiers |

**Optional fields**: `args`, `transport` (stdio or socket), `env`, `initializationOptions`, `settings`, `workspaceFolder`, `startupTimeout`, `shutdownTimeout`, `restartOnCrash`, `maxRestarts`.

**Important**: LSP plugins configure the connection; they do not bundle the language server binary. Users must install the binary separately.

---

## 5. Auto-Discovery Rules

Claude Code discovers components in default directories without any configuration in `plugin.json`. This is the recommended approach for standard layouts.

### Default discovery locations

| Component | Default path | File pattern |
|-----------|-------------|--------------|
| Skills | `skills/` | `<name>/SKILL.md` |
| Commands | `commands/` | `*.md` |
| Agents | `agents/` | `*.md` |
| Hooks | `hooks/` | `hooks.json` |
| MCP servers | `.mcp.json` | (single file) |
| LSP servers | `.lsp.json` | (single file) |

### When explicit paths are needed

Use the component path fields in `plugin.json` only when:

1. Components live outside default directories (e.g., `./custom/agents/reviewer.md`)
2. You have multiple hook files (e.g., `./hooks/security-hooks.json` in addition to the default)
3. You want to expose individual files rather than entire directories

Explicit paths supplement defaults. If both `agents/` exists and `"agents": "./custom/agents.md"` is declared, both sources are loaded.

### Manifest-optional plugins

If a plugin directory has no `.claude-plugin/plugin.json`, Claude Code:
1. Derives the plugin name from the directory name
2. Auto-discovers all components in default locations
3. Uses no version (the plugin cannot be cached or updated via version comparison)

This works for `--plugin-dir` development but is not recommended for marketplace distribution.

---

## 6. Namespacing

Every component in a plugin is prefixed with the plugin name from `plugin.json`:

| Plugin name | Component | Resulting identifier |
|-------------|-----------|---------------------|
| `mcp-apps` | skill `create-mcp-app` | `/mcp-apps:create-mcp-app` |
| `plugin-toolkit` | agent `plugin-scanner` | `plugin-toolkit:plugin-scanner` |
| `mece-decomposer` | command `decompose` | `/mece-decomposer:decompose` |

### Why namespacing matters

Two plugins can define a skill called `review` without collision. `/plugin-a:review` and `/plugin-b:review` are distinct. This is a hard requirement of the plugin system -- there is no way to opt out of namespacing for installed plugins.

### Standalone vs plugin names

| Context | Skill name |
|---------|------------|
| `.claude/skills/review/SKILL.md` | `/review` |
| `my-plugin/skills/review/SKILL.md` | `/my-plugin:review` |

To change the namespace prefix, change the `name` field in `plugin.json`.

### Priority resolution

When skills share the same name across scopes: enterprise > personal > project. Plugin skills use namespaced names, so they cannot conflict with non-plugin skills at other levels.

---

## 7. Development Workflow

### Local testing with --plugin-dir

The `--plugin-dir` flag loads a plugin from a local directory without installation:

```bash
claude --plugin-dir ./my-plugin
```

This is the primary development workflow. The plugin is loaded for the session but not installed to any scope.

### Iteration loop

1. Edit plugin files (SKILL.md, agents, hooks, etc.)
2. Restart Claude Code to pick up changes
3. Test components:
   - Skills: invoke with `/plugin-name:skill-name`
   - Agents: check `/agents` list
   - Hooks: trigger the relevant event
   - MCP servers: verify tools appear
4. Repeat

### Loading multiple plugins

```bash
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

### Debugging

Run `claude --debug` or use `/debug` in the TUI to see:
- Which plugins are being loaded
- Manifest validation errors
- Component registration details
- MCP server initialization status

### Validation

Use `claude plugin validate .` or `/plugin validate .` from the plugin directory to check for structural issues before distribution.

---

## 8. Migration Path: Standalone to Plugin

### Step 1: Create plugin structure

```bash
mkdir -p my-plugin/.claude-plugin
```

### Step 2: Create manifest

```json
{
  "name": "my-plugin",
  "description": "Migrated from standalone configuration",
  "version": "1.0.0"
}
```

### Step 3: Copy existing files

```bash
cp -r .claude/commands my-plugin/
cp -r .claude/agents my-plugin/
cp -r .claude/skills my-plugin/
```

### Step 4: Migrate hooks

Extract the `hooks` object from `.claude/settings.json` or `settings.local.json` into `my-plugin/hooks/hooks.json`. The format is identical.

### Step 5: Update script paths

Replace any absolute or project-relative paths with `${CLAUDE_PLUGIN_ROOT}` in hooks and MCP server configs:

```json
"command": "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh"
```

### Step 6: Test

```bash
claude --plugin-dir ./my-plugin
```

### What changes

| Standalone | Plugin |
|-----------|--------|
| Available in one project only | Shareable via marketplaces |
| `/review` | `/my-plugin:review` |
| Hooks in `settings.json` | Hooks in `hooks/hooks.json` |
| Manual copy to share | `claude plugin install` |

### What does not change

- Skill frontmatter format
- Agent markdown format
- Hook event types and matchers
- MCP/LSP configuration structure

---

## 9. Implementation Audit

This repository contains 7 installable plugins plus 1 project-scoped module (skill-maintainer, which cannot be installed as a plugin because it depends on repo-local state). The marketplace at `.claude-plugin/marketplace.json` lists all 7 installable plugins.

### Plugin inventory

| Plugin | Version | Skills | Commands | Agents | MCP | Hooks | LSP | References |
|--------|---------|--------|----------|--------|-----|-------|-----|------------|
| mcp-apps | 0.1.0 | 2 (create-mcp-app, migrate-oai-app) | 0 | 0 | 0 | 0 | 0 | yes |
| plugin-toolkit | 0.1.0 | 1 (plugin-toolkit) | 0 | 2 (plugin-scanner, quality-checker) | 0 | 0 | 0 | yes |
| web-tdd | 0.1.0 | 1 (web-tdd) | 0 | 0 | 0 | 0 | 0 | no |
| cogapp-markdown | 0.1.0 | 1 (cogapp-markdown) | 0 | 0 | 0 | 0 | 0 | no |
| tui-design | 0.1.0 | 1 (tui-design) | 0 | 0 | 0 | 0 | 0 | yes |
| dimensional-modeling | 0.1.0 | 1 (dimensional-modeling) | 0 | 0 | 0 | 0 | 0 | yes |
| mece-decomposer | 0.2.0 | 1 (mece-decomposer) | 4 (decompose, interview, validate, export) | 0 | 1 (mece-decomposer) | 0 | 0 | yes |

### Per-plugin details

#### mcp-apps

- **Components**: 2 skills in `skills/` -- `create-mcp-app` and `migrate-oai-app`. Both have `references/` directories with upstream documentation.
- **Notable**: Carries backup copies of skills (`create-mcp-app.backup/`, `migrate-oai-app.backup/`), likely from skill-maintainer update cycles.
- **plugin.json**: Minimal -- name, version, description, author, repository. No component path overrides. Relies entirely on auto-discovery.

#### plugin-toolkit

- **Components**: 1 skill in `skills/plugin-toolkit/` with 4 reference files (analysis-template, command-template, hook-patterns, quality-checklist). 2 agents in `agents/` (plugin-scanner, quality-checker).
- **Notable**: The only plugin in this repo that uses agents. The agents are well-structured with purpose, process, input/output format, and usage sections. The quality-checker agent consumes output from plugin-scanner, forming a pipeline.
- **plugin.json**: Minimal. Auto-discovery handles both the skill and agents directories.

#### web-tdd

- **Components**: 1 skill. No references directory, no scripts.
- **Notable**: Simplest plugin in the repo (skill-only, no supporting files). Could benefit from reference material for framework-specific testing patterns.
- **plugin.json**: Minimal.

#### cogapp-markdown

- **Components**: 1 skill. No references or scripts.
- **Notable**: Attribution to Simon Willison in author field. Teaches the cogapp pattern for documentation generation.
- **plugin.json**: Minimal.

#### tui-design

- **Components**: 1 skill with `references/` directory. Backup copy present.
- **Notable**: Rich frontmatter description with trigger phrases. Good example of a reference-style skill.
- **plugin.json**: Minimal.

#### dimensional-modeling

- **Components**: 1 skill with 5 reference files (anti_patterns, dag_execution, key_generation, query_patterns, schema_patterns).
- **Notable**: Heaviest reference material of any plugin. The progressive disclosure pattern is well-applied: SKILL.md provides the overview, references provide depth.
- **plugin.json**: Minimal.

#### mece-decomposer

- **Components**: 1 skill, 4 commands (decompose, interview, validate, export), 1 MCP server, 1 bundled MCP app (React + Node).
- **Notable**: The most complex plugin in the repo. Uses all three of: skills, commands, and MCP servers. The MCP server runs a bundled Node.js application that serves an interactive tree visualizer. The `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` correctly for the server path. The commands directory provides structured workflows that reference the skill's methodology.
- **Backup copies**: Present for the skill directory.
- **plugin.json**: Version 0.2.0 (most advanced version in the repo).

### Observations across all plugins

1. **No plugin uses hooks or LSP servers.** The hook and LSP component types are available but unused in this repo.
2. **Only mece-decomposer uses MCP servers.** It bundles a full Node.js application with a build step.
3. **Only plugin-toolkit uses agents.** Its two agents form a scanner-then-evaluator pipeline.
4. **All plugin.json files are minimal.** None use component path overrides -- all rely on auto-discovery in default locations.
5. **Backup directories** (`.backup/`) appear in multiple plugins, suggesting the skill-maintainer creates backups during update cycles.
6. **Version uniformity**: 6 of 7 plugins are at 0.1.0. Only mece-decomposer has advanced to 0.2.0.
7. **All plugins share the same repository URL** in their manifests, pointing to the monorepo.

### Marketplace configuration

The root `.claude-plugin/marketplace.json` lists all 7 plugins with relative-path sources (e.g., `"source": "./mcp-apps"`). The marketplace name is `fb-claude-skills` and the owner is Fred Bliss. All version numbers in marketplace entries match the corresponding `plugin.json` versions.

---

## 10. Anti-Patterns

### Structural mistakes

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| Components inside `.claude-plugin/` | Not discovered. Only `plugin.json` belongs there. | Move to plugin root. |
| Absolute paths in hooks/MCP config | Breaks after installation (plugins are copied to cache). | Use `${CLAUDE_PLUGIN_ROOT}`. |
| Path traversal (`../shared-utils`) | External files not copied to cache. | Use symlinks or restructure. |
| No version in `plugin.json` | Cache cannot detect updates. Users never get new code. | Always set a version. |
| Version in both `plugin.json` and marketplace | `plugin.json` wins silently, marketplace version ignored. | Set in one place only. |

### Skill mistakes

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| No trigger phrases in description | Claude never auto-loads the skill because it cannot match user intent. | Add natural language phrases users would say. |
| Description over 1024 chars | Truncated, losing trigger phrases. | Keep under 1024 characters. |
| SKILL.md over 500 lines | Excessive context loading. | Extract to `references/` files. |
| Missing `disable-model-invocation` on side-effect skills | Claude may auto-trigger deploy, commit, or send actions. | Add `disable-model-invocation: true`. |

### Distribution mistakes

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| Relative paths in URL-based marketplace | URL marketplaces download only `marketplace.json`, not the files. | Use GitHub/git/npm sources, or distribute via git-based marketplace. |
| node_modules in plugin directory | Bloats cache copy. | Add build step, commit only dist output, or use `.gitignore` patterns. |
| No README | Users cannot understand what the plugin does. | Add README with installation, skills table, invocation examples. |
| Changing code without bumping version | Existing users never see updates due to caching. | Always bump version when changing plugin code. |

---

## 11. Readiness Checklist

Before distributing a plugin, verify each item:

### Manifest

- [ ] `.claude-plugin/plugin.json` exists with at least `name` and `version`
- [ ] `name` is kebab-case, no spaces
- [ ] `version` follows semantic versioning (MAJOR.MINOR.PATCH)
- [ ] `description` is present and under 200 characters
- [ ] `author` object has at least a `name` field

### Structure

- [ ] All component directories (`skills/`, `commands/`, `agents/`, `hooks/`) are at plugin root, not inside `.claude-plugin/`
- [ ] No path traversal (`../`) in any configuration
- [ ] All hook/MCP paths use `${CLAUDE_PLUGIN_ROOT}` instead of absolute paths
- [ ] Hook scripts are executable (`chmod +x`)

### Skills

- [ ] Every SKILL.md has `name` and `description` in frontmatter
- [ ] Descriptions include natural trigger phrases
- [ ] Descriptions are under 1024 characters
- [ ] SKILL.md files are under 500 lines (overflow in `references/`)
- [ ] Side-effect skills have `disable-model-invocation: true`

### Agents

- [ ] Every agent markdown file has `name` and `description` in frontmatter
- [ ] Descriptions clearly state when Claude should invoke the agent
- [ ] Agent system prompts define the role, expertise, input/output format

### Testing

- [ ] Plugin loads without errors via `claude --plugin-dir ./my-plugin`
- [ ] All skills appear in `/help` under the correct namespace
- [ ] Agents appear in `/agents`
- [ ] Hooks trigger on the expected events
- [ ] MCP servers start and their tools appear
- [ ] `claude plugin validate .` passes with no errors

### Documentation

- [ ] README.md includes: last updated date, installation commands, skills table, invocation examples
- [ ] CHANGELOG.md tracks changes with semantic versions
- [ ] Marketplace entry in `.claude-plugin/marketplace.json` matches `plugin.json` metadata

### Distribution

- [ ] Version in `plugin.json` is bumped from previous release
- [ ] Marketplace entry has correct `source` path
- [ ] No secrets, credentials, or `.env` files in plugin directory
- [ ] Plugin works when installed via marketplace (not just `--plugin-dir`)

---

## 12. Cross-References

This report focuses on plugin anatomy and the component model. Related topics are covered or planned in companion reports:

| Topic | Report | Coverage |
|-------|--------|----------|
| Marketplace distribution, source types, versioning, release channels | `marketplace_distribution_patterns.md` | How to structure and host marketplaces, version resolution, strict mode, private repos |
| Hook events, matchers, types, execution model | `hooks_system_patterns.md` | Deep dive on all 14 event types, hook type semantics (command/prompt/agent), execution ordering |
| Subagent types, delegation, preloaded skills, agent teams | `subagents_and_agent_teams.md` | Built-in vs custom agents, context forking, skill preloading, TeammateIdle patterns |
| Cross-surface compatibility (Claude Code, Claude Desktop, Claude.ai) | `cross_surface_compatibility.md` | Which plugin features work on which surfaces, MCP App patterns, host capability detection |
| Skills best practices, design patterns, progressive disclosure | `claude_skills_best_practices_guide_full_report.md` | Existing -- detailed guide on skill authoring |
| Self-updating skill maintenance pipeline | `self_updating_system_design.md` | Existing -- CDC pipeline, source monitoring, closed-loop updates |
| Data-centric agent state modeling | `data_centric_agent_state_research.md` | Existing -- dimensional modeling research for agent state |
| Abstraction analogies across the three-repo system | `abstraction_analogies.md` | Existing -- the database analogy (storage engine / stored procedures / client) |

---

## Appendix A: Environment Variables

| Variable | Available in | Description |
|----------|-------------|-------------|
| `${CLAUDE_PLUGIN_ROOT}` | hooks, MCP configs, LSP configs | Absolute path to the installed plugin directory. Required for any file reference after installation. |
| `$ARGUMENTS` | skill content | All arguments passed when invoking a skill |
| `$ARGUMENTS[N]` / `$N` | skill content | Positional argument access (0-indexed) |
| `${CLAUDE_SESSION_ID}` | skill content | Current session ID for logging or correlation |

## Appendix B: Installation Scopes

| Scope | Settings file | Use case |
|-------|--------------|----------|
| `user` | `~/.claude/settings.json` | Personal plugins, all projects (default) |
| `project` | `.claude/settings.json` | Team plugins shared via version control |
| `local` | `.claude/settings.local.json` | Project-specific, gitignored |
| `managed` | `managed-settings.json` | Organization-managed (read-only, update only) |

## Appendix C: CLI Commands Quick Reference

```bash
# Install and manage
claude plugin install <plugin>@<marketplace> [--scope user|project|local]
claude plugin uninstall <plugin>@<marketplace> [--scope ...]
claude plugin enable <plugin> [--scope ...]
claude plugin disable <plugin> [--scope ...]
claude plugin update <plugin> [--scope ...]

# Develop and debug
claude --plugin-dir ./my-plugin
claude --plugin-dir ./a --plugin-dir ./b
claude --debug
claude plugin validate .

# Marketplace
/plugin marketplace add <source>
/plugin marketplace update
/plugin install <name>@<marketplace>
```
