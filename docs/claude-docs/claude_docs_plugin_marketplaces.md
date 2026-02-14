<!-- source: https://code.claude.com/docs/en/plugin-marketplaces -->
<!-- fetched: 2026-02-14 -->

# Create and distribute a plugin marketplace

> Build and host plugin marketplaces to distribute Claude Code extensions across teams and communities.

A plugin marketplace is a catalog that lets you distribute plugins to others. Marketplaces provide centralized discovery, version tracking, automatic updates, and support for multiple source types.

## Overview

Creating and distributing a marketplace involves:

1. **Creating plugins**: build one or more plugins with commands, agents, hooks, MCP servers, or LSP servers
2. **Creating a marketplace file**: define a `marketplace.json` that lists your plugins and where to find them
3. **Host the marketplace**: push to GitHub, GitLab, or another git host
4. **Share with users**: users add your marketplace with `/plugin marketplace add` and install individual plugins

## Create the marketplace file

Create `.claude-plugin/marketplace.json` in your repository root.

```json
{
  "name": "company-tools",
  "owner": {
    "name": "DevTools Team",
    "email": "devtools@example.com"
  },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting on save",
      "version": "2.1.0",
      "author": {
        "name": "DevTools Team"
      }
    },
    {
      "name": "deployment-tools",
      "source": {
        "source": "github",
        "repo": "company/deploy-plugin"
      },
      "description": "Deployment automation tools"
    }
  ]
}
```

## Marketplace schema

### Required fields

| Field     | Type   | Description                                | Example        |
| :-------- | :----- | :----------------------------------------- | :------------- |
| `name`    | string | Marketplace identifier (kebab-case)        | `"acme-tools"` |
| `owner`   | object | Marketplace maintainer information         |                |
| `plugins` | array  | List of available plugins                  |                |

### Owner fields

| Field   | Type   | Required | Description                      |
| :------ | :----- | :------- | :------------------------------- |
| `name`  | string | Yes      | Name of the maintainer or team   |
| `email` | string | No       | Contact email for the maintainer |

### Optional metadata

| Field                  | Type   | Description                           |
| :--------------------- | :----- | :------------------------------------ |
| `metadata.description` | string | Brief marketplace description         |
| `metadata.version`     | string | Marketplace version                   |
| `metadata.pluginRoot`  | string | Base directory for relative source paths |

## Plugin entries

Each plugin entry needs at minimum a `name` and `source`.

### Required fields

| Field    | Type           | Description                     |
| :------- | :------------- | :------------------------------ |
| `name`   | string         | Plugin identifier (kebab-case)  |
| `source` | string/object  | Where to fetch the plugin from  |

### Optional plugin fields

| Field         | Type    | Description                                          |
| :------------ | :------ | :--------------------------------------------------- |
| `description` | string  | Brief plugin description                             |
| `version`     | string  | Plugin version                                       |
| `author`      | object  | Plugin author information                            |
| `homepage`    | string  | Plugin homepage or documentation URL                 |
| `repository`  | string  | Source code repository URL                           |
| `license`     | string  | SPDX license identifier                              |
| `keywords`    | array   | Tags for plugin discovery                            |
| `category`    | string  | Plugin category for organization                     |
| `tags`        | array   | Tags for searchability                               |
| `strict`      | boolean | When false, marketplace entry defines plugin entirely |

## Plugin sources

### Relative paths

For plugins in the same repository:

```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin"
}
```

> **Note:** Relative paths only work when users add your marketplace via Git (GitHub, GitLab, or git URL).

### GitHub repositories

```json
{
  "name": "github-plugin",
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo"
  }
}
```

Pin to a specific branch, tag, or commit:

```json
{
  "name": "github-plugin",
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo",
    "ref": "v2.0.0",
    "sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
  }
}
```

### Git repositories

```json
{
  "name": "git-plugin",
  "source": {
    "source": "url",
    "url": "https://gitlab.com/team/plugin.git"
  }
}
```

## Host and distribute marketplaces

### Host on GitHub (recommended)

1. Create a repository for your marketplace
2. Add `.claude-plugin/marketplace.json` with your plugin definitions
3. Users add with `/plugin marketplace add owner/repo`

### Host on other git services

Any git hosting service works:

```
/plugin marketplace add https://gitlab.com/company/plugins.git
```

### Private repositories

Claude Code supports installing from private repositories using existing git credential helpers. For background auto-updates, set authentication tokens:

| Provider  | Environment variables        |
| :-------- | :--------------------------- |
| GitHub    | `GITHUB_TOKEN` or `GH_TOKEN` |
| GitLab    | `GITLAB_TOKEN` or `GL_TOKEN` |
| Bitbucket | `BITBUCKET_TOKEN`            |

## Validation and testing

Validate your marketplace JSON syntax:

```bash
claude plugin validate .
```

Or from within Claude Code:

```
/plugin validate .
```

## Troubleshooting

### Marketplace not loading

- Verify the marketplace URL is accessible
- Check that `.claude-plugin/marketplace.json` exists at the specified path
- Ensure JSON syntax is valid using `claude plugin validate`

### Common validation errors

| Error                                             | Solution                                                      |
| :------------------------------------------------ | :------------------------------------------------------------ |
| `File not found: .claude-plugin/marketplace.json` | Create the file with required fields                          |
| `Invalid JSON syntax`                             | Check for missing commas, extra commas, unquoted strings      |
| `Duplicate plugin name`                           | Give each plugin a unique `name` value                        |
| `Path traversal not allowed`                      | Use paths relative to marketplace root without `..`           |

### Files not found after installation

Plugins are copied to a cache directory. Paths referencing files outside the plugin directory won't work. Use symlinks or restructure your marketplace.
