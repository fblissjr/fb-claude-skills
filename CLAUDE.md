# fb-claude-skills

Self-updating skills system for Claude Code. Skills rot as best practices evolve, upstream APIs change, and external data sources drift. This repo closes the loop: detect changes, produce updated content, validate against the Agent Skills spec, and let the user review before committing.

## Repo structure

```
fb-claude-skills/
  .claude-plugin/
    marketplace.json         # Root marketplace catalog (lists all installable plugins)
  mcp-apps/                  # Plugin: MCP Apps creation and migration
    .claude-plugin/
      plugin.json
    skills/                  # create-mcp-app, migrate-oai-app
    references/              # Upstream docs (offline copies)
  plugin-toolkit/            # Plugin: plugin analysis and management
    .claude-plugin/
      plugin.json
    skills/plugin-toolkit/   # The skill itself (SKILL.md + references/)
    agents/                  # plugin-scanner, quality-checker
  web-tdd/                   # Plugin: TDD workflow for web apps
    .claude-plugin/
      plugin.json
    skills/web-tdd/          # SKILL.md
  cogapp-markdown/           # Plugin: auto-generate markdown sections
    .claude-plugin/
      plugin.json
    skills/cogapp-markdown/  # SKILL.md
  skill-maintainer/          # Project-scoped: maintains other skills (and itself)
    SKILL.md                 # Orchestrator with 4 commands: check, update, status, add-source
    config.yaml              # Source registry: what docs/repos to monitor, which skills they affect
    scripts/                 # Python automation (all run via uv run)
    references/              # Best practices, monitored sources, update patterns
    state/                   # Versioned state: watermarks, page hashes, timestamps
  docs/
    analysis/                # Structured extraction from Anthropic skills guide, gap analysis, system design
    internals/               # API reference, schemas, troubleshooting
    blogs/                   # Captured blog posts
    claude-docs/             # Captured Claude Code official docs (skills page)
    guides/                  # PDF guide source
  coderef/
    agentskills/             # Symlink -> ~/claude/agentskills (Agent Skills spec + skills-ref validator)
    ext-apps/                # External apps reference
  internal/log/              # Session logs (log_YYYY-MM-DD.md)
```

## Installation

### Installable plugins

This repo is a plugin marketplace. Add it and install plugins:

```bash
# from GitHub
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install web-tdd@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
```

After installing, skills are available as namespaced slash commands (e.g., `/mcp-apps:create-mcp-app`, `/web-tdd`).

To remove: `claude plugin uninstall <name>@fb-claude-skills`

### Project-scoped skill (skill-maintainer)

skill-maintainer runs from within this repo. It depends on `config.yaml`, `state/`, and `scripts/` in the repo tree, so it cannot be installed as a global plugin. It is discoverable when Claude Code is run from the repo root.

## Key patterns

### Docs CDC (Change Data Capture)

Three-layer pipeline in `docs_monitor.py`:

1. **DETECT** -- HEAD request on `llms-full.txt`, compare `Last-Modified` header. Zero bytes if unchanged.
2. **IDENTIFY** -- fetch `llms-full.txt` (Mintlify's clean markdown export), split by `Source:` delimiters, hash each watched page, compare to stored hashes.
3. **CLASSIFY** -- keyword heuristic on diff text (breaking/additive/cosmetic).

Sources expose `llms_full_url` in config.yaml. Each source tracks a watermark (Last-Modified/ETag) and per-page hashes with `last_checked` and `last_changed` timestamps independently.

### Source CDC

Git-based monitoring of upstream repos. `source_monitor.py` shallow-clones configured repos, checks commits since last run, extracts Python APIs via AST, scans commit messages for deprecation keywords.

### Closed-loop updates

detect -> classify -> apply -> validate -> user reviews diff. `apply_updates.py` supports three modes: `report-only`, `apply-local` (default), and `create-pr`. Always validates with skills-ref before any write. Creates backups. Never auto-commits.

### Freshness hooks

`check_freshness.py` reads state.json timestamps and warns if a skill hasn't been checked in N days. Runs in <100ms. Never blocks skill invocation.

### Progressive disclosure

SKILL.md stays under 500 lines with the heavy logic in `scripts/`. References in `references/` provide detailed documentation loaded on demand. Three levels: frontmatter (always loaded) -> SKILL.md body (loaded when relevant) -> linked files (on demand).

### Self-referential maintenance

skill-maintainer monitors and maintains itself. Its own sources (Anthropic docs, Agent Skills spec) are tracked in config.yaml.

## How to keep things fresh

Check for documentation changes:
```bash
uv run python skill-maintainer/scripts/docs_monitor.py
```

Check for upstream code changes:
```bash
uv run python skill-maintainer/scripts/source_monitor.py
```

Generate unified report of all changes:
```bash
uv run python skill-maintainer/scripts/update_report.py
```

Apply detected changes to a skill (default: local apply + validate):
```bash
uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit
uv run python skill-maintainer/scripts/apply_updates.py --skill plugin-toolkit --mode report-only
```

Validate any skill against the spec + best practices:
```bash
uv run skills-ref validate path/to/SKILL.md           # quick spec validation only
uv run python skill-maintainer/scripts/validate_skill.py ./skill-maintainer
uv run python skill-maintainer/scripts/validate_skill.py --all
```

Check staleness of tracked skills:
```bash
uv run python skill-maintainer/scripts/check_freshness.py
uv run python skill-maintainer/scripts/check_freshness.py plugin-toolkit
```

## Configuration

**Source registry**: `skill-maintainer/config.yaml`
- `sources`: each has a `type` (docs or source), detection method (`llms_full_url` for docs, `repo` for git), and list of watched pages/files
- `skills`: tracked skills with paths, source dependencies, and auto_update flag

**State**: `skill-maintainer/state/state.json`
- `docs.{source}._watermark` -- Last-Modified/ETag for the detect layer
- `docs.{source}._pages.{url}` -- per-page hash, content_preview, last_checked, last_changed
- `sources.{source}` -- last_commit, commits_since_last, last_checked

## Cross-repo references

- **agentskills** (`coderef/agentskills/` -> `~/claude/agentskills`): Agent Skills open standard. Provides `skills-ref` validator used for all skill validation.
- **mlx-skills** (`~/claude/mlx-skills`): Semi-automated skill maintenance for MLX-related skills. `source_monitor.py` was generalized from its `scripts/check_updates.py`.

## Conventions

### Adding a new skill module

Required structure:
```
module-name/
  .claude-plugin/
    plugin.json            # name, version, description, author, repository
  README.md                # last updated date, installation, skill table, invocation
  skills/
    skill-name/
      SKILL.md             # frontmatter: name, description, metadata.author, metadata.version
  references/              # optional: supporting docs loaded on demand
```

Skills and agents in default directories (`skills/`, `agents/`) are auto-discovered. Do not list them in plugin.json -- only use component path fields for non-default locations.

After creating:
1. `uv run skills-ref validate module-name/skills/skill-name/SKILL.md` -- validate each skill
2. Add plugin entry to root `.claude-plugin/marketplace.json` (name, source path, description, version)
3. Add skills to `skill-maintainer/config.yaml` under both `sources:` and `skills:`
4. Add to `skill-maintainer/references/monitored_sources.md` if watching upstream
5. Bump version in both `pyproject.toml` and `CHANGELOG.md` (must stay in sync)
6. Update root `README.md` skills table and installation section
7. Append session to `internal/log/log_YYYY-MM-DD.md`

- **Package manager**: Always `uv`. No pip.
- **JSON**: `orjson` for all serialization/deserialization.
- **Skills standard**: All skills follow the [Agent Skills](https://agentskills.io) spec.
- **State in repo**: `skill-maintainer/state/` is versioned and portable, not in `~/.claude/`.
- **Non-destructive**: Always validate before writing, create backups, never auto-commit.
- **Logs**: Session logs go in `internal/log/log_YYYY-MM-DD.md`.
- **READMEs**: Every plugin README includes: last updated date, installation commands, skills table, invocation examples.

## Dependencies

Managed via `pyproject.toml` with uv:
- `orjson` - fast JSON
- `httpx` - HTTP client for CDC detect/identify layers
- `pyyaml` - config parsing
- `skills-ref` - Agent Skills validator (editable install from `coderef/agentskills/skills-ref`)
