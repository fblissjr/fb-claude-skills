last updated: 2026-02-19

# marketplace distribution patterns

Domain report on Claude Code plugin marketplace architecture, distribution strategies, and operational patterns. Uses fb-claude-skills as a primary case study.

---

## 1. overview

A plugin marketplace is a catalog that distributes Claude Code plugins. Marketplaces solve three problems: **discovery** (users browse a curated collection), **version tracking** (the catalog knows each plugin's version and detects updates), and **centralized governance** (organizations allowlist marketplaces, enforce update policies, and audit plugin usage).

The lifecycle is two-step: users first *add* a marketplace (registering the catalog -- zero plugins downloaded), then *install* individual plugins from it. Marketplaces are defined by `.claude-plugin/marketplace.json` at the root of a git repository or served at a URL.

The official Anthropic marketplace (`claude-plugins-official`) ships built-in with Claude Code and provides LSP integrations, external service connectors, development workflow commands, and output styles. Third-party marketplaces like fb-claude-skills extend this with domain-specific skills.

---

## 2. marketplace.json schema

Lives at `.claude-plugin/marketplace.json` relative to the repository root.

### 2.1 top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Kebab-case identifier. Appears in install commands (`plugin@marketplace-name`). |
| `owner` | object | yes | `name` (required string), `email` (optional string). |
| `metadata.description` | string | no | Brief marketplace description. |
| `metadata.version` | string | no | Catalog version (distinct from plugin versions). |
| `metadata.pluginRoot` | string | no | Base directory prepended to relative source paths. |
| `plugins` | array | yes | Plugin entries (see 2.2). |

**Reserved names**: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `life-sciences`. Names impersonating official marketplaces are also blocked.

Example from fb-claude-skills (abbreviated):

```json
{
  "name": "fb-claude-skills",
  "owner": { "name": "Fred Bliss" },
  "metadata": { "description": "A collection of Claude Code plugins and skills" },
  "plugins": [
    { "name": "mcp-apps", "source": "./mcp-apps", "description": "...", "version": "0.1.0" },
    { "name": "mece-decomposer", "source": "./mece-decomposer", "description": "...", "version": "0.2.0" }
  ]
}
```

### 2.2 plugin entry fields

Required: `name` (string, kebab-case) and `source` (string or object -- see section 3).

Optional standard metadata: `description`, `version`, `author` (object with `name`/`email`), `homepage`, `repository`, `license` (SPDX), `keywords` (array), `category` (string), `tags` (array), `strict` (boolean, default `true`).

Optional component configuration: `commands`, `agents`, `hooks`, `mcpServers`, `lspServers` -- each a string, array, or object pointing to component files within the plugin.

### 2.3 strict mode

| `strict` value | Behavior |
|----------------|----------|
| `true` (default) | `plugin.json` is authoritative. Marketplace supplements; both merge. |
| `false` | Marketplace entry is the entire definition. A conflicting `plugin.json` causes load failure. |

Use `strict: true` when plugins manage their own manifests. Use `strict: false` when the marketplace operator curates components differently than the author intended.

---

## 3. source types

Five source types control where Claude Code fetches each plugin.

**Relative path** -- `"source": "./plugins/my-plugin"`. Must start with `./`. Resolves within the marketplace repo. Only works when marketplace is added via git, not URL. Best for monorepo patterns.

**GitHub** -- `"source": { "source": "github", "repo": "owner/repo", "ref": "v2.0.0", "sha": "..." }`. Fields: `repo` (required), `ref` (optional branch/tag), `sha` (optional 40-char commit). Best for plugins in separate GitHub repos with tag-based pinning.

**Git URL** -- `"source": { "source": "url", "url": "https://gitlab.com/team/plugin.git", "ref": "main" }`. URL must end with `.git`. Same `ref`/`sha` options as GitHub. Best for GitLab, Bitbucket, or self-hosted git.

**npm** -- `"source": { "source": "npm", "package": "@company/plugin", "version": "^1.0.0", "registry": "..." }`. Installed via `npm install`. Note: docs warn this is "not yet fully implemented."

**pip** -- `"source": { "source": "pip", "package": "company-plugin", "version": ">=1.0", "registry": "..." }`. Best for Python-centric organizations with existing PyPI infrastructure.

**Selection guide:**

| Scenario | Source |
|----------|--------|
| Same repo as marketplace | Relative path |
| Public GitHub repo | `github` |
| GitLab / Bitbucket / self-hosted | `url` |
| Existing npm package | `npm` |
| Existing PyPI package | `pip` |
| Maximum reproducibility | Any git source with `sha` |

---

## 4. multi-plugin monorepo patterns

### 4.1 fb-claude-skills case study

This repository contains both the marketplace catalog and all plugin directories:

```
fb-claude-skills/
  .claude-plugin/marketplace.json   # Root catalog -- lists 7 installable plugins
  mcp-apps/
    .claude-plugin/plugin.json      # name, version, description, author, repository
    skills/create-mcp-app/          # SKILL.md
    skills/migrate-oai-app/         # SKILL.md
    references/                     # Upstream docs (offline copies)
  plugin-toolkit/
    .claude-plugin/plugin.json
    skills/plugin-toolkit/          # SKILL.md + references/
    agents/                         # plugin-scanner, quality-checker
  web-tdd/
    .claude-plugin/plugin.json
    skills/web-tdd/                 # SKILL.md
  cogapp-markdown/
    .claude-plugin/plugin.json
    skills/cogapp-markdown/         # SKILL.md
  tui-design/
    .claude-plugin/plugin.json
    skills/tui-design/              # SKILL.md + references/
  dimensional-modeling/
    .claude-plugin/plugin.json
    skills/dimensional-modeling/    # SKILL.md
  mece-decomposer/
    .claude-plugin/plugin.json
    skills/mece-decomposer/         # SKILL.md + references/ + scripts/
    commands/                       # Slash commands: decompose, interview, validate, export
    mcp-app/                        # MCP App: interactive tree visualizer (React)
    .mcp.json                       # MCP server auto-configuration (stdio)
  skill-maintainer/                 # NOT in marketplace (project-scoped only)
    config.yaml, state/, scripts/   # Depends on repo-internal state
```

Key observations:

- Every installable plugin has its own `.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, and `repository`.
- The marketplace references all plugins via relative paths (`"source": "./mcp-apps"`), which works because users add the marketplace from git.
- Not all modules appear in the marketplace. `skill-maintainer` depends on repo-internal state (`config.yaml`, `state/`) and cannot be installed globally.
- All plugins share the same `repository` URL in their `plugin.json`, pointing to the monorepo root. The `repository` field identifies the monorepo, not individual plugin directories.
- Plugin complexity varies: some are a single SKILL.md (web-tdd, cogapp-markdown), others include agents (plugin-toolkit), MCP servers (mece-decomposer), or both skills and references (tui-design).

### 4.2 advantages and constraints

Advantages: atomic multi-plugin releases in a single commit, shared CI/CD pipeline, co-located catalog and plugins so relative paths always resolve.

Constraints: **plugin isolation at install time** -- Claude Code copies only the plugin directory to `~/.claude/plugins/cache`, so `../shared-utils` paths break (workaround: symlinks, which are followed during copying). **No shared runtime dependencies** -- each plugin must be self-contained. **Version coupling risk** -- a breaking change in a shared external dependency requires coordinated updates.

### 4.3 hybrid patterns

A marketplace can mix relative-path plugins with external sources: `"source": "./internal-tool"` alongside `"source": { "source": "github", "repo": "other-org/tool" }`.

---

## 5. versioning strategy

**Version flow**: versions appear in `plugin.json` and `marketplace.json`. The plugin manifest always wins silently. For relative-path plugins, prefer setting version in the marketplace entry to reduce duplication. For external plugins, use the plugin's own `plugin.json`. In fb-claude-skills, both locations are kept in sync manually.

**Semver**: most plugins are at `0.1.0` (pre-1.0, active development). mece-decomposer is at `0.2.0`. Version changes drive update detection -- same version at two refs means Claude Code skips the update.

**Release channels**: create separate marketplaces pointing to different refs of the same plugin repo. Example: a `stable-tools` marketplace pins to the `stable` branch, a `latest-tools` marketplace pins to the `latest` branch. Each ref must declare a distinct version in its `plugin.json` -- if two refs share the same version, Claude Code treats them as identical and skips the update. Assign channels to user groups via managed settings (`extraKnownMarketplaces`).

**Important distinction**: marketplace source (where to fetch the catalog itself, set via `/plugin marketplace add` or `extraKnownMarketplaces`) and plugin source (where to fetch an individual plugin, set in the `source` field of each marketplace entry) are independent. A marketplace hosted at `acme-corp/plugin-catalog` can list a plugin fetched from `acme-corp/code-formatter`. They point to different repositories and are pinned independently.

---

## 6. update lifecycle

**Manual**: `/plugin marketplace update marketplace-name` fetches latest catalog and updates installed plugins.

**Auto-update**: when enabled per-marketplace, Claude Code refreshes at startup. Official marketplaces auto-update by default; third-party do not. Toggle via `/plugin` UI Marketplaces tab.

**Environment overrides**: `DISABLE_AUTOUPDATER` disables all auto-updates. `FORCE_AUTOUPDATE_PLUGINS=true` re-enables plugin updates while keeping Claude Code updates manual.

**Private repo tokens for auto-update** (background updates cannot use interactive credential helpers):

| Provider | Variable |
|----------|----------|
| GitHub | `GITHUB_TOKEN` or `GH_TOKEN` |
| GitLab | `GITLAB_TOKEN` or `GL_TOKEN` |
| Bitbucket | `BITBUCKET_TOKEN` |

**Rollback**: no built-in command. Pin `source` to a specific `sha` or `ref`, then run marketplace update. Or uninstall and reinstall from a local clone at the desired commit.

---

## 7. private and enterprise distribution

**Private repos**: Claude Code uses system git credential helpers. If `git clone` works in your terminal, it works in Claude Code.

**Team injection**: commit to `.claude/settings.json` in your project:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": { "source": { "source": "github", "repo": "your-org/claude-plugins" } }
  },
  "enabledPlugins": { "code-formatter@company-tools": true }
}
```

**Managed restrictions** (`strictKnownMarketplaces`): deployed via `managed-settings.json` in system directories (macOS: `/Library/Application Support/ClaudeCode/`, Linux: `/etc/claude-code/`, Windows: `C:\Program Files\ClaudeCode\`). Cannot be overridden by user/project settings.

| Value | Behavior |
|-------|----------|
| Undefined | No restrictions |
| `[]` | Complete lockdown |
| List of sources | Allowlist only |

Allowlist entries support exact repo matching, full URL matching, and `hostPattern` regex:

```json
{
  "strictKnownMarketplaces": [
    { "source": "github", "repo": "acme-corp/approved-plugins" },
    { "source": "github", "repo": "acme-corp/security-tools", "ref": "v2.0" },
    { "source": "url", "url": "https://plugins.example.com/marketplace.json" },
    { "source": "hostPattern", "hostPattern": "^github\\.example\\.com$" }
  ]
}
```

Restrictions are validated before any network requests or filesystem operations. For GitHub sources, `repo` is required; `ref` and `path` must also match if specified in the allowlist. For URL sources, the full URL must match exactly.

Related managed-only settings: `allowManagedPermissionRulesOnly` (restricts permission rules to managed config) and `allowManagedHooksOnly` (blocks user/project/plugin hooks).

---

## 8. discovery UX

**The /plugin interface** has four tabs: Discover (browse available plugins), Installed (manage by scope), Marketplaces (add/remove/update catalogs), Errors (loading issues). Type to filter; select a plugin to choose scope.

**Installation scopes**: User (all projects, `~/.claude/settings.json`), Project (this repo, shared, `.claude/settings.json`), Local (this repo, personal, `.claude/settings.local.json`), Managed (org-wide, system managed-settings.json).

**CLI**: `/plugin install name@marketplace` (interactive) or `claude plugin install name@marketplace --scope project` (terminal).

**Trust model**: no automated verification for third-party plugins. Official docs warn users to trust plugins before installing. Users evaluate: name, description, version, author, category/tags, homepage/repository links.

---

## 9. plugin metadata best practices

**Naming**: kebab-case, no spaces. Public-facing in install commands. Avoid confusion with official Anthropic plugins.

**Descriptions**: one sentence, concise. Include natural-language trigger phrases for skill auto-loading. Under 1024 characters.

**Author/repository**: always set `author.name` in `plugin.json`. Set `repository` URL for source inspection. Monorepo plugins point to the monorepo root.

**Keywords/categories**: use `keywords` array for searchability. Use `category` string for high-level organization.

**Version consistency**: sync `plugin.json` and `marketplace.json` for relative-path plugins. Never reuse a version number for different content.

**Component paths**: use `${CLAUDE_PLUGIN_ROOT}` in hooks and MCP configs. Skills/agents in default directories (`skills/`, `agents/`) auto-discover -- only declare non-standard locations in `plugin.json`.

---

## 10. readiness checklist

**Marketplace structure**: `.claude-plugin/marketplace.json` exists at root; `name` is valid kebab-case (not reserved); `owner.name` set; at least one plugin in `plugins`; JSON validates (`claude plugin validate .`).

**Each plugin entry**: unique `name`; `source` resolves correctly; `description` present; `version` set (marketplace entry for relative-path, plugin.json for external).

**Each plugin directory**: `.claude-plugin/plugin.json` has name/version/description; skills have valid SKILL.md with frontmatter; SKILL.md under 500 lines; no `../` paths (use symlinks); hooks/MCP use `${CLAUDE_PLUGIN_ROOT}`.

**Distribution**: repo accessible to target users; private repo tokens documented; local testing passes (`marketplace add .` then install each plugin); team config in `.claude/settings.json` if needed; enterprise restrictions in managed settings if needed.

**Metadata quality**: `author` set; `repository` URL set; descriptions include trigger phrases; keywords/tags populated; license specified for public marketplaces.

**Validation commands:**

```bash
# Validate marketplace JSON structure
claude plugin validate .
# or from within Claude Code:
/plugin validate .

# Test the full install flow locally
/plugin marketplace add ./path/to/marketplace
/plugin install test-plugin@marketplace-name
```

---

## 11. cross-references

- `docs/analysis/abstraction_analogies.md` -- unified framework: skills as stored procedures, marketplace as system catalog.
- `docs/analysis/claude_skills_best_practices_guide_full_report.md` -- skill authoring best practices.
- `docs/claude-docs/claude_docs_plugin-marketplaces.md` -- upstream marketplace creation docs.
- `docs/claude-docs/claude_docs_discover-plugins.md` -- upstream plugin discovery docs.
- `docs/claude-docs/claude_docs_permissions.md` -- permission system and managed settings.
- `skill-maintainer/config.yaml` -- source registry tracking upstream doc pages for CDC.
