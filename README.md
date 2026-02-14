last updated: 2026-02-14

# claude-skills

A random collection of utility / experimental / research / etc Claude Code skills and plugins -- some created by me, some from others, some remixed from both.

## skills

| Plugin | Skills | Description | Notes       |
|--------|--------|-------------|-------------|
| [mcp-apps](mcp-apps/) | `create-mcp-app`, `migrate-oai-app` | Build and migrate MCP Apps (interactive UIs for MCP-enabled hosts) |
| [plugin-toolkit](plugin-toolkit/) | `plugin-toolkit` | Analyze, polish, and manage Claude Code plugins |
| [web-tdd](web-tdd/) | `web-tdd` | TDD workflow for web applications (Vitest, Playwright, Vibium) |
| [cogapp-markdown](cogapp-markdown/) | `cogapp-markdown` | Auto-generate markdown sections using cogapp | from [simonw skills repo](https://github.com/simonw/skills/tree/main/cogapp-markdown)
| [skill-maintainer](skill-maintainer/) | `skill-maintainer` | Automated skill maintenance and upstream change monitoring |
| [heylook-monitor](heylook-monitor/) | MCP App | Live dashboard for heylookitsanllm local LLM server | based on my local LLM inference repo at [https://github.com/fblissjr/heylookitsanllm](https://github.com/fblissjr/heylookitsanllm)

### More fully built out skills:
- [mlx-skills](https://github.com/fblissjr/mlx-skills) - a fork of [awni](https://github.com/awni/mlx-skills)'s Apple MLX skills that tries to get more granular and more modular

## installation

### install from GitHub (recommended)

This repo is a plugin marketplace. Add it once, then install whichever plugins you want:

```bash
# from within Claude Code:
/plugin marketplace add fblissjr/fb-claude-skills

# install individual plugins
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install web-tdd@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
```

Or from the terminal:

```bash
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mcp-apps@fb-claude-skills
```

### install from local clone

If you prefer to clone first:

```bash
git clone https://github.com/fblissjr/fb-claude-skills.git
cd fb-claude-skills

# add as a local marketplace
/plugin marketplace add .

# install whichever plugins you want
/plugin install mcp-apps@fb-claude-skills
/plugin install plugin-toolkit@fb-claude-skills
/plugin install web-tdd@fb-claude-skills
/plugin install cogapp-markdown@fb-claude-skills
```

### development / testing

To load a plugin temporarily without installing (changes take effect for the current session only):

```bash
claude --plugin-dir ./mcp-apps
claude --plugin-dir ./plugin-toolkit --plugin-dir ./web-tdd
```

### project-scoped (skill-maintainer)

skill-maintainer is designed to run from within this repo since it depends on `config.yaml`, `state/`, and `scripts/` in the repo. It is not installable as a global plugin.

To use it, run Claude Code from the repo root:

```bash
cd fb-claude-skills
claude
# Then: /skill-maintainer check
```

### uninstall

```bash
claude plugin uninstall mcp-apps@fb-claude-skills
claude plugin uninstall plugin-toolkit@fb-claude-skills
claude plugin uninstall web-tdd@fb-claude-skills
claude plugin uninstall cogapp-markdown@fb-claude-skills
```

### verify

```bash
claude plugin list
```

## usage

Once installed, invoke skills as slash commands (plugin skills are namespaced):

```
/mcp-apps:create-mcp-app     # Build an MCP App from scratch
/mcp-apps:migrate-oai-app    # Migrate from OpenAI Apps SDK to MCP
/plugin-toolkit               # Analyze, polish, and manage plugins
/web-tdd                      # Set up TDD for a web project
/cogapp-markdown              # Auto-generate markdown docs
/skill-maintainer check       # Check for upstream changes (project-scoped)
```

Or just describe what you want -- skills trigger on relevant keywords.

## skill-maintainer

This repo includes a self-updating system that monitors upstream docs and source repos for changes that affect skills. See [skill-maintainer/](skill-maintainer/) and [docs/](docs/) for details.

```bash
# Check for upstream changes
uv run python skill-maintainer/scripts/docs_monitor.py
uv run python skill-maintainer/scripts/source_monitor.py

# Generate report and apply updates
uv run python skill-maintainer/scripts/update_report.py
uv run python skill-maintainer/scripts/apply_updates.py --skill <name>
```

## more skills

- [mlx-skills](https://github.com/fblissjr/mlx-skills) -- a fork of [awni](https://github.com/awni/mlx-skills)'s Apple MLX skills with more granular and modular structure

## credits

- [simonw](https://github.com/simonw) -- cogapp-markdown
- [modelcontextprotocol/ext-apps](https://github.com/modelcontextprotocol/ext-apps) -- mcp-apps upstream
