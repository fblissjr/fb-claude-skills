last updated: 2026-07-21

# documentation

Authoritative index for all documentation in this repository.

## guides

| Document | Description |
|----------|-------------|
| [mcp-ecosystem.md](mcp-ecosystem.md) | Field guide to the full MCP ecosystem: protocol, tools, resources, apps, connectors, extensions, and how they relate |

See also the root [README.md](../README.md) for plugin installation, surface compatibility, and usage instructions.

## internals (`internals/`)

Repo-specific operating reference. Spokes for the [root CLAUDE.md](../CLAUDE.md) hub.

| Document | Description |
|----------|-------------|
| [plugin-versioning.md](internals/plugin-versioning.md) | Full version cascade for plugin content changes; `sync-versions` coverage gaps; worked example |
| [plugin-patterns.md](internals/plugin-patterns.md) | Required plugin structure; hooks vs. skills; composable directives; agents; bash 3.2 portability |
| [maintenance.md](internals/maintenance.md) | Automatic checks, on-demand commands, state files, workspace members |
| [gotchas.md](internals/gotchas.md) | best_practices duality, security-hook disable, pre-commit re-install, path-privacy edges, CLAUDE.md size creep |
| [upstream_drift_backlog.md](internals/upstream_drift_backlog.md) | Unabsorbed upstream doc changes since the 2026-05-04 snapshot |
| [explainer_video_roadmap.md](internals/explainer_video_roadmap.md) | Queued explainer-video work: named-beats refactor and what it unblocks |

## package documentation

| Document | Description |
|----------|-------------|
| [agent-state README](../tools/agent-state/README.md) | Schema reference (v2), CLI, Python API, migration guide |
| [skill-maintainer README](../tools/skill-maintainer/README.md) | CLI reference, data flow, workflow, configuration |

## domain reports (`analysis/`)

Design documents and research created during development. Cover the full Claude extension ecosystem.

| Document | Description |
|----------|-------------|
| [plugin_system_architecture.md](analysis/plugin_system_architecture.md) | Plugin anatomy, schema, components, auto-discovery, audit |
| [marketplace_distribution_patterns.md](analysis/marketplace_distribution_patterns.md) | Marketplace schema, source types, monorepo, enterprise distribution |
| [mcp_protocol_and_servers.md](analysis/mcp_protocol_and_servers.md) | MCP protocol, primitives, transports, SDKs, registry |
| [mcp_apps_and_ui_development.md](analysis/mcp_apps_and_ui_development.md) | MCP Apps SDK, UI linkage, React hooks, framework templates |
| [hooks_system_patterns.md](analysis/hooks_system_patterns.md) | Hook events, types, matchers, security, automation patterns |
| [subagents_and_agent_teams.md](analysis/subagents_and_agent_teams.md) | Custom agents, tool control, teams, delegation patterns |
| [cross_surface_compatibility.md](analysis/cross_surface_compatibility.md) | Surface matrix, transports, permissions, headless mode |
| [data_centric_agent_state_research.md](analysis/data_centric_agent_state_research.md) | Research on data-centric LLM agent state management |
| [memory_and_rules_system.md](analysis/memory_and_rules_system.md) | Memory hierarchy, auto memory, CLAUDE.md imports, rules |

## synthesis (`reports/`)

| Document | Description |
|----------|-------------|
| [claude_ecosystem_synthesis.md](reports/claude_ecosystem_synthesis.md) | Full ecosystem overview, decision tree, maturity assessment |

## upstream Claude Code docs

Not stored in this repo. Frozen copies used to live in `docs/claude-docs/`; they
were deleted on 2026-07-21 after drifting five months out of date while carrying
no date header, so nothing signalled their staleness. Between the February
capture and July, the hooks page grew from 64KB to 235KB and `plugins-reference`
from 24KB to 88KB — the copies had become roughly a third of the real content,
and wrong in load-bearing ways (`allowed-tools` semantics, hook exit codes).

Fetch current snapshots instead:

```bash
skill-maintain upstream
```

That writes `.skill-maintainer/state/pages/*.md` (gitignored) and reports a
per-page line and character delta against the previous snapshot. Twelve pages
are tracked, listed in `.skill-maintainer/config.json`: skills, plugins,
plugins-reference, discover-plugins, plugin-marketplaces, hooks, hooks-guide,
sub-agents, memory, settings, permissions, mcp.

Anything not tracked there is a link away at
[code.claude.com/docs](https://code.claude.com/docs/en/overview) — read it live
rather than copying it here.

