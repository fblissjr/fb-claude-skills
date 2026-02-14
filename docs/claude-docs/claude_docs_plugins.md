<!-- source: https://code.claude.com/docs/en/plugins -->
<!-- fetched: 2026-02-14 -->

# Create plugins

> Create custom plugins to extend Claude Code with skills, agents, hooks, and MCP servers.

Plugins let you extend Claude Code with custom functionality that can be shared across projects and teams.

Looking to install existing plugins? See [Discover and install plugins](/en/discover-plugins). For complete technical specifications, see [Plugins reference](/en/plugins-reference).

## When to use plugins vs standalone configuration

| Approach                                  | Skill names          | Best for                                                                             |
| :---------------------------------------- | :------------------- | :----------------------------------------------------------------------------------- |
| **Standalone** (`.claude/` directory)     | `/hello`             | Personal workflows, project-specific customizations, quick experiments               |
| **Plugins** (`.claude-plugin/plugin.json`)| `/plugin-name:hello` | Sharing with teammates, distributing to community, versioned releases, reusable      |

## Quickstart

### Prerequisites

- Claude Code installed and authenticated
- Claude Code version 1.0.33 or later (`claude --version`)

### Create your first plugin

**1. Create the plugin directory**

```bash
mkdir my-first-plugin
```

**2. Create the plugin manifest**

The manifest file at `.claude-plugin/plugin.json` defines your plugin's identity.

```bash
mkdir my-first-plugin/.claude-plugin
```

Create `my-first-plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "my-first-plugin",
  "description": "A greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

| Field         | Purpose                                                                                |
| :------------ | :------------------------------------------------------------------------------------- |
| `name`        | Unique identifier and skill namespace. Skills prefixed with this (e.g., `/my-first-plugin:hello`). |
| `description` | Shown in the plugin manager when browsing or installing plugins.                       |
| `version`     | Track releases using semantic versioning.                                              |
| `author`      | Optional. Helpful for attribution.                                                     |

**3. Add a skill**

Skills live in the `skills/` directory at plugin root. Each skill is a folder containing a `SKILL.md` file.

```bash
mkdir -p my-first-plugin/skills/hello
```

Create `my-first-plugin/skills/hello/SKILL.md`:

```yaml
---
description: Greet the user with a friendly message
disable-model-invocation: true
---

Greet the user warmly and ask how you can help them today.
```

**4. Test your plugin**

```bash
claude --plugin-dir ./my-first-plugin
```

Then try: `/my-first-plugin:hello`

## Plugin structure overview

> **Important:** Don't put `commands/`, `agents/`, `skills/`, or `hooks/` inside `.claude-plugin/`. Only `plugin.json` goes inside `.claude-plugin/`. All other directories must be at the plugin root level.

| Directory         | Location    | Purpose                                                                        |
| :---------------- | :---------- | :----------------------------------------------------------------------------- |
| `.claude-plugin/` | Plugin root | Contains `plugin.json` manifest (optional if components use default locations) |
| `commands/`       | Plugin root | Skills as Markdown files                                                       |
| `agents/`         | Plugin root | Custom agent definitions                                                       |
| `skills/`         | Plugin root | Agent Skills with `SKILL.md` files                                             |
| `hooks/`          | Plugin root | Event handlers in `hooks.json`                                                 |
| `.mcp.json`       | Plugin root | MCP server configurations                                                      |
| `.lsp.json`       | Plugin root | LSP server configurations for code intelligence                                |

## Develop more complex plugins

### Add Skills to your plugin

```
my-plugin/
+-- .claude-plugin/
|   +-- plugin.json
+-- skills/
    +-- code-review/
        +-- SKILL.md
```

Each `SKILL.md` needs frontmatter with `name` and `description` fields.

### Add LSP servers to your plugin

Add an `.lsp.json` file to your plugin:

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

### Test your plugins locally

```bash
claude --plugin-dir ./my-plugin
```

Load multiple plugins:

```bash
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

### Share your plugins

1. Add documentation: include a `README.md`
2. Version your plugin: use semantic versioning in `plugin.json`
3. Create or use a marketplace: distribute through plugin marketplaces
4. Test with others

## Convert existing configurations to plugins

### Migration steps

**1. Create the plugin structure**

```bash
mkdir -p my-plugin/.claude-plugin
```

Create `my-plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "description": "Migrated from standalone configuration",
  "version": "1.0.0"
}
```

**2. Copy your existing files**

```bash
cp -r .claude/commands my-plugin/
cp -r .claude/agents my-plugin/
cp -r .claude/skills my-plugin/
```

**3. Test your migrated plugin**

```bash
claude --plugin-dir ./my-plugin
```

| Standalone (`.claude/`)       | Plugin                           |
| :---------------------------- | :------------------------------- |
| Only available in one project | Can be shared via marketplaces   |
| Files in `.claude/commands/`  | Files in `plugin-name/commands/` |
| Hooks in `settings.json`      | Hooks in `hooks/hooks.json`      |
| Must manually copy to share   | Install with `/plugin install`   |
