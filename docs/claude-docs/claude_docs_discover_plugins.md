<!-- source: https://code.claude.com/docs/en/discover-plugins -->
<!-- fetched: 2026-02-14 -->

# Discover and install prebuilt plugins through marketplaces

> Find and install plugins from marketplaces to extend Claude Code with new commands, agents, and capabilities.

Plugins extend Claude Code with skills, agents, hooks, and MCP servers. Plugin marketplaces are catalogs that help you discover and install these extensions without building them yourself.

Looking to create and distribute your own marketplace? See [Create and distribute a plugin marketplace](/en/plugin-marketplaces).

## How marketplaces work

A marketplace is a catalog of plugins that someone else has created and shared. Using a marketplace is a two-step process:

1. **Add the marketplace**: This registers the catalog with Claude Code so you can browse what's available. No plugins are installed yet.
2. **Install individual plugins**: Browse the catalog and install the plugins you want.

Think of it like adding an app store: adding the store gives you access to browse its collection, but you still choose which apps to download individually.

## Official Anthropic marketplace

The official Anthropic marketplace (`claude-plugins-official`) is automatically available when you start Claude Code. Run `/plugin` and go to the **Discover** tab to browse what's available.

To install a plugin from the official marketplace:

```
/plugin install plugin-name@claude-plugins-official
```

## Add marketplaces

Use the `/plugin marketplace add` command to add marketplaces from different sources.

> **Tip:** You can use `/plugin market` instead of `/plugin marketplace`, and `rm` instead of `remove`.

- **GitHub repositories**: `owner/repo` format (for example, `anthropics/claude-code`)
- **Git URLs**: any git repository URL (GitLab, Bitbucket, self-hosted)
- **Local paths**: directories or direct paths to `marketplace.json` files
- **Remote URLs**: direct URLs to hosted `marketplace.json` files

### Add from GitHub

```
/plugin marketplace add anthropics/claude-code
```

### Add from other Git hosts

```
/plugin marketplace add https://gitlab.com/company/plugins.git
/plugin marketplace add git@gitlab.com:company/plugins.git
```

To add a specific branch or tag, append `#` followed by the ref:

```
/plugin marketplace add https://gitlab.com/company/plugins.git#v1.0.0
```

### Add from local paths

```
/plugin marketplace add ./my-marketplace
/plugin marketplace add ./path/to/marketplace.json
```

### Add from remote URLs

```
/plugin marketplace add https://example.com/marketplace.json
```

> **Note:** URL-based marketplaces have limitations compared to Git-based marketplaces. Relative paths in plugin entries won't resolve.

## Install plugins

Once you've added marketplaces, install plugins directly (installs to user scope by default):

```
/plugin install plugin-name@marketplace-name
```

To choose a different installation scope, use the interactive UI: run `/plugin`, go to the **Discover** tab, and press **Enter** on a plugin. You'll see options for:

- **User scope** (default): install for yourself across all projects
- **Project scope**: install for all collaborators on this repository (adds to `.claude/settings.json`)
- **Local scope**: install for yourself in this repository only (not shared with collaborators)

The `--scope` option lets you target a specific scope with CLI commands:

```bash
claude plugin install formatter@your-org --scope project
claude plugin uninstall formatter@your-org --scope project
```

## Manage installed plugins

Run `/plugin` and go to the **Installed** tab to view, enable, disable, or uninstall your plugins.

Disable a plugin without uninstalling:

```
/plugin disable plugin-name@marketplace-name
```

Re-enable a disabled plugin:

```
/plugin enable plugin-name@marketplace-name
```

Completely remove a plugin:

```
/plugin uninstall plugin-name@marketplace-name
```

## Manage marketplaces

List all configured marketplaces:

```
/plugin marketplace list
```

Refresh plugin listings from a marketplace:

```
/plugin marketplace update marketplace-name
```

Remove a marketplace:

```
/plugin marketplace remove marketplace-name
```

> **Warning:** Removing a marketplace will uninstall any plugins you installed from it.

### Configure auto-updates

Claude Code can automatically update marketplaces and their installed plugins at startup. Toggle auto-update for individual marketplaces through the UI:

1. Run `/plugin` to open the plugin manager
2. Select **Marketplaces**
3. Choose a marketplace from the list
4. Select **Enable auto-update** or **Disable auto-update**

Official Anthropic marketplaces have auto-update enabled by default. Third-party and local development marketplaces have auto-update disabled by default.

## Configure team marketplaces

Team admins can set up automatic marketplace installation for projects by adding marketplace configuration to `.claude/settings.json`. When team members trust the repository folder, Claude Code prompts them to install these marketplaces and plugins.

For full configuration options including `extraKnownMarketplaces` and `enabledPlugins`, see Plugin settings.

## Troubleshooting

### /plugin command not recognized

1. **Check your version**: Run `claude --version`. Plugins require version 1.0.33 or later.
2. **Update Claude Code**
3. **Restart Claude Code**: After updating, restart your terminal and run `claude` again.

### Common issues

- **Marketplace not loading**: Verify the URL is accessible and that `.claude-plugin/marketplace.json` exists at the path
- **Plugin installation failures**: Check that plugin source URLs are accessible and repositories are public (or you have access)
- **Files not found after installation**: Plugins are copied to a cache, so paths referencing files outside the plugin directory won't work
- **Plugin skills not appearing**: Clear the cache with `rm -rf ~/.claude/plugins/cache`, restart Claude Code, and reinstall the plugin
