<!-- source: https://code.claude.com/docs/en/plugins-reference -->
<!-- fetched: 2026-02-14 -->

# Plugins reference

> Complete technical reference for Claude Code plugin system, including schemas, CLI commands, and component specifications.

## Plugin components reference

### Skills

**Location**: `skills/` or `commands/` directory in plugin root

**File format**: Skills are directories with `SKILL.md`; commands are simple markdown files

```
skills/
+-- pdf-processor/
|   +-- SKILL.md
|   +-- reference.md (optional)
|   +-- scripts/ (optional)
+-- code-reviewer/
    +-- SKILL.md
```

Skills and commands are auto-discovered when the plugin is installed. Claude can invoke them based on task context.

### Agents

**Location**: `agents/` directory in plugin root

**File format**: Markdown files with frontmatter describing agent capabilities

```yaml
---
name: agent-name
description: What this agent specializes in and when Claude should invoke it
---

Detailed system prompt for the agent.
```

### Hooks

**Location**: `hooks/hooks.json` in plugin root, or inline in plugin.json

**Available events**: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `UserPromptSubmit`, `Notification`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionStart`, `SessionEnd`, `TeammateIdle`, `TaskCompleted`, `PreCompact`

**Hook types**: `command` (shell), `prompt` (LLM evaluation), `agent` (agentic verifier)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

### MCP servers

**Location**: `.mcp.json` in plugin root, or inline in plugin.json

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    }
  }
}
```

### LSP servers

**Location**: `.lsp.json` in plugin root, or inline in plugin.json

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

**Required fields**: `command`, `extensionToLanguage`

**Optional fields**: `args`, `transport` (`stdio`/`socket`), `env`, `initializationOptions`, `settings`, `workspaceFolder`, `startupTimeout`, `shutdownTimeout`, `restartOnCrash`, `maxRestarts`

## Plugin installation scopes

| Scope     | Settings file                 | Use case                                                 |
| :-------- | :---------------------------- | :------------------------------------------------------- |
| `user`    | `~/.claude/settings.json`     | Personal plugins across all projects (default)           |
| `project` | `.claude/settings.json`       | Team plugins shared via version control                  |
| `local`   | `.claude/settings.local.json` | Project-specific plugins, gitignored                     |
| `managed` | `managed-settings.json`       | Managed plugins (read-only, update only)                 |

## Plugin manifest schema

The `.claude-plugin/plugin.json` file defines your plugin's metadata. The manifest is optional -- if omitted, Claude Code auto-discovers components in default locations and derives the plugin name from the directory name.

### Complete schema

```json
{
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

### Required fields

If you include a manifest, `name` is the only required field.

| Field  | Type   | Description                               |
| :----- | :----- | :---------------------------------------- |
| `name` | string | Unique identifier (kebab-case, no spaces) |

### Metadata fields

| Field         | Type   | Description                  |
| :------------ | :----- | :--------------------------- |
| `version`     | string | Semantic version             |
| `description` | string | Brief explanation             |
| `author`      | object | Author information           |
| `homepage`    | string | Documentation URL            |
| `repository`  | string | Source code URL              |
| `license`     | string | License identifier           |
| `keywords`    | array  | Discovery tags               |

### Component path fields

| Field          | Type          | Description                          |
| :------------- | :------------ | :----------------------------------- |
| `commands`     | string/array  | Additional command files/directories |
| `agents`       | string/array  | Additional agent files               |
| `skills`       | string/array  | Additional skill directories         |
| `hooks`        | string/object | Hook config paths or inline config   |
| `mcpServers`   | string/object | MCP config paths or inline config    |
| `outputStyles` | string/array  | Additional output style files        |
| `lspServers`   | string/object | LSP server configs                   |

Custom paths supplement default directories -- they don't replace them. All paths must be relative and start with `./`.

### Environment variables

`${CLAUDE_PLUGIN_ROOT}`: absolute path to your plugin directory. Use in hooks, MCP servers, and scripts.

## Plugin directory structure

### Standard plugin layout

```
enterprise-plugin/
+-- .claude-plugin/           # Metadata directory (optional)
|   +-- plugin.json
+-- commands/                 # Default command location
+-- agents/                   # Default agent location
+-- skills/                   # Agent Skills
|   +-- code-reviewer/
|   |   +-- SKILL.md
|   +-- pdf-processor/
|       +-- SKILL.md
|       +-- scripts/
+-- hooks/                    # Hook configurations
|   +-- hooks.json
+-- .mcp.json                 # MCP server definitions
+-- .lsp.json                 # LSP server configurations
+-- scripts/                  # Hook and utility scripts
+-- LICENSE
+-- CHANGELOG.md
```

> **Warning:** `.claude-plugin/` contains only `plugin.json`. All other directories must be at the plugin root, not inside `.claude-plugin/`.

### File locations reference

| Component       | Default Location             | Purpose                                    |
| :-------------- | :--------------------------- | :----------------------------------------- |
| **Manifest**    | `.claude-plugin/plugin.json` | Plugin metadata and configuration          |
| **Commands**    | `commands/`                  | Skill Markdown files (legacy)              |
| **Agents**      | `agents/`                    | Subagent Markdown files                    |
| **Skills**      | `skills/`                    | Skills with `<name>/SKILL.md` structure    |
| **Hooks**       | `hooks/hooks.json`           | Hook configuration                         |
| **MCP servers** | `.mcp.json`                  | MCP server definitions                     |
| **LSP servers** | `.lsp.json`                  | Language server configurations             |

## CLI commands reference

### plugin install

```bash
claude plugin install <plugin> [options]
```

- `<plugin>`: Plugin name or `plugin-name@marketplace-name`
- `-s, --scope <scope>`: `user` (default), `project`, or `local`

### plugin uninstall

```bash
claude plugin uninstall <plugin> [options]
```

**Aliases:** `remove`, `rm`

### plugin enable

```bash
claude plugin enable <plugin> [options]
```

### plugin disable

```bash
claude plugin disable <plugin> [options]
```

### plugin update

```bash
claude plugin update <plugin> [options]
```

- `-s, --scope <scope>`: `user` (default), `project`, `local`, or `managed`

## Debugging and development tools

Use `claude --debug` (or `/debug` within the TUI) to see plugin loading details.

### Common issues

| Issue                               | Cause                           | Solution                                                  |
| :---------------------------------- | :------------------------------ | :-------------------------------------------------------- |
| Plugin not loading                  | Invalid `plugin.json`           | Validate with `claude plugin validate`                    |
| Commands not appearing              | Wrong directory structure       | Ensure `commands/` at root, not in `.claude-plugin/`      |
| Hooks not firing                    | Script not executable           | `chmod +x script.sh`                                      |
| MCP server fails                    | Missing `${CLAUDE_PLUGIN_ROOT}` | Use variable for all plugin paths                         |
| Path errors                         | Absolute paths used             | All paths must be relative, start with `./`               |
| LSP executable not found            | Language server not installed   | Install the required binary                               |

## Version management

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

Start at `1.0.0` for first stable release. Document changes in `CHANGELOG.md`.
