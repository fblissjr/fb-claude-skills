last updated: 2026-02-13

# claude-skills

A collection of Claude Code skills and plugins -- some created by me, some from others, some remixed from both.

## skills

| Plugin | Skills | Description |
|--------|--------|-------------|
| [mcp-apps](mcp-apps/) | `create-mcp-app`, `migrate-oai-app` | Build and migrate MCP Apps (interactive UIs for MCP-enabled hosts) |
| [plugin-toolkit](plugin-toolkit/) | `plugin-toolkit` | Analyze, polish, and manage Claude Code plugins |
| [web-tdd](web-tdd/) | `web-tdd` | TDD workflow for web applications (Vitest, Playwright, Vibium) |
| [cogapp-markdown](cogapp-markdown/) | `cogapp-markdown` | Auto-generate markdown sections using cogapp |
| [skill-maintainer](skill-maintainer/) | `skill-maintainer` | Automated skill maintenance and upstream change monitoring |
| [heylook-monitor](heylook-monitor/) | MCP App | Live dashboard for heylookitsanllm local LLM server |

## installation

### install a plugin (recommended)

Each plugin directory in this repo can be installed directly into Claude Code:

```bash
# Clone the repo
git clone https://github.com/fblissjr/fb-claude-skills.git
cd fb-claude-skills

# Install whichever plugins you want
claude plugin add ./mcp-apps
claude plugin add ./plugin-toolkit
claude plugin add ./web-tdd
claude plugin add ./cogapp-markdown
```

After installing, skills are available globally in all Claude Code sessions. Verify with:

```bash
claude plugin list
```

### install from GitHub (without cloning)

```bash
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin mcp-apps
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin plugin-toolkit
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin web-tdd
claude plugin add https://github.com/fblissjr/fb-claude-skills --plugin cogapp-markdown
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
claude plugin remove mcp-apps
claude plugin remove plugin-toolkit
claude plugin remove web-tdd
claude plugin remove cogapp-markdown
```

## usage

Once installed, invoke skills as slash commands:

```
/create-mcp-app              # Build an MCP App from scratch
/migrate-oai-app             # Migrate from OpenAI Apps SDK to MCP
/plugin-toolkit:analyze .    # Analyze a plugin's structure
/plugin-toolkit:polish .     # Add standard utility commands
/web-tdd                     # Set up TDD for a web project
/cogapp-markdown             # Auto-generate markdown docs
/skill-maintainer check      # Check for upstream changes (project-scoped)
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
