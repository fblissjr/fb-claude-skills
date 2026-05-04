last updated: 2026-05-04

# analysis index

Wiki-style index of `docs/analysis/`. Reports are tagged by kind so retrieval is by intent (looking for an entity description vs. a pattern catalog vs. a snapshot audit) rather than alphabetic order.

For the umbrella documentation index across `docs/` (guides, internals, package docs, captured external docs), see [../README.md](../README.md).

## entity

Describe a thing the wider Claude/MCP ecosystem defines. Stable when the upstream spec is stable.

| Document | Topic |
|----------|-------|
| [plugin_system_architecture.md](plugin_system_architecture.md) | Claude Code plugin anatomy, schema, components, auto-discovery |
| [mcp_protocol_and_servers.md](mcp_protocol_and_servers.md) | MCP protocol, primitives, transports, SDKs, registry |
| [memory_and_rules_system.md](memory_and_rules_system.md) | Memory hierarchy, auto memory, CLAUDE.md imports, rules |
| [subagents_and_agent_teams.md](subagents_and_agent_teams.md) | Custom agents, tool control, teams, delegation |
| [skills_guide_structured.md](skills_guide_structured.md) | Structured extraction from the Anthropic skills guide |

## concept

Pattern, strategy, or principle this repo applies. Updated when our practice evolves.

| Document | Topic |
|----------|-------|
| [hooks_system_patterns.md](hooks_system_patterns.md) | Hook events, types, matchers, security, automation patterns |
| [marketplace_distribution_patterns.md](marketplace_distribution_patterns.md) | Marketplace schema, source types, monorepo, enterprise distribution |
| [mcp_apps_and_ui_development.md](mcp_apps_and_ui_development.md) | MCP Apps SDK, UI linkage, React hooks, framework templates |
| [cross_surface_compatibility.md](cross_surface_compatibility.md) | Surface matrix, transports, permissions, headless mode |
| [claude_skills_best_practices_guide_full_report.md](claude_skills_best_practices_guide_full_report.md) | Skills best practices from Anthropic guide |
| [self_updating_system_design.md](self_updating_system_design.md) | CDC architecture decisions and source inventory |
| [duckdb_dimensional_model_strategy.md](duckdb_dimensional_model_strategy.md) | DuckDB star schema strategy for agent state |
| [data_centric_agent_state_research.md](data_centric_agent_state_research.md) | Research on data-centric LLM agent state management |

## audit

Time-bound assessment. Useful as a snapshot; superseded as the ecosystem evolves.

| Document | Topic |
|----------|-------|
| [mcp_ecosystem_audit_2026-02-19.md](mcp_ecosystem_audit_2026-02-19.md) | MCP ecosystem audit: tools, registries, hosting (Feb 2026) |
| [skills_guide_analysis.md](skills_guide_analysis.md) | Gap analysis: Anthropic guide recommendations vs. this repo |

## synthesis

Cross-cutting integrative work that pulls from multiple of the above. (None today; the closest equivalent is [../reports/claude_ecosystem_synthesis.md](../reports/claude_ecosystem_synthesis.md), which lives one level up.)

## maintenance notes

- Each report's `last updated` line at the top is the freshness signal. `skill-maintain freshness` doesn't yet read `docs/analysis/` — staleness here is checked by the upstream change detector (`skill-maintain upstream`) when an external source page changes.
- `skill-maintain lint` flags any `*.md` in this directory not linked from `docs/README.md` or this index. Add new reports to both.
- See [log.md](log.md) for the narrative ingest/update history.
