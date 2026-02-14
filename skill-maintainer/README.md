last updated: 2026-02-14

# skill-maintainer

Automated skill maintenance and upstream change monitoring for Claude Code skills. Detects when best practices, source code, or documentation changes, and produces updated skill content or reports for review.

This is a **project-scoped skill** -- it runs from within this repo and depends on `config.yaml`, `state/`, and `scripts/` in the repo tree. It cannot be installed as a global plugin.

## usage

Run Claude Code from the repo root:

```bash
cd fb-claude-skills
claude
```

Then invoke:

```
/skill-maintainer check           # run all monitors, produce change report
/skill-maintainer update <name>   # apply detected changes to a specific skill
/skill-maintainer status          # show freshness status of all tracked skills
/skill-maintainer add-source <url-or-repo>  # add a new monitored source
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `skill-maintainer` | "check for skill updates", "are my skills current", "update skills" | Monitors upstream docs and source repos for changes affecting skills |

## scripts

All scripts run via `uv run`:

| Script | Purpose |
|--------|---------|
| `scripts/docs_monitor.py` | CDC pipeline: detect/identify/classify documentation changes |
| `scripts/source_monitor.py` | Git-based upstream code change detection |
| `scripts/update_report.py` | Unified change report generation |
| `scripts/apply_updates.py` | Apply detected changes (report-only, apply-local, create-pr) |
| `scripts/validate_skill.py` | Extended validation wrapping skills-ref with best practice checks |
| `scripts/check_freshness.py` | Lightweight staleness check (<100ms) |

## monitored sources

Configured in `config.yaml`:

| Source | Type | What it watches |
|--------|------|-----------------|
| `anthropic-skills-docs` | docs | 8 pages from code.claude.com/docs (skills, plugins, hooks, sub-agents) |
| `agentskills-spec` | source | Agent Skills spec, skills-ref validator and parser |
| `anthropic-skills-guide` | docs | The Complete Guide to Building Skills PDF |
| `ext-apps` | source | MCP Apps SDK: skills, spec, docs |

## tracked skills

| Skill | Path | Sources |
|-------|------|---------|
| plugin-toolkit | `./plugin-toolkit/skills/plugin-toolkit` | anthropic-skills-docs, agentskills-spec |
| skill-maintainer | `./skill-maintainer` | anthropic-skills-docs, agentskills-spec |
| create-mcp-app | `./mcp-apps/skills/create-mcp-app` | ext-apps, anthropic-skills-docs, agentskills-spec |
| migrate-oai-app | `./mcp-apps/skills/migrate-oai-app` | ext-apps, anthropic-skills-docs, agentskills-spec |

## state

Versioned in `state/state.json` (not in `~/.claude/`):
- `docs.{source}._watermark` -- Last-Modified/ETag for the detect layer
- `docs.{source}._pages.{url}` -- per-page hash, content_preview, last_checked, last_changed
- `sources.{source}` -- last_commit, commits_since_last, last_checked
