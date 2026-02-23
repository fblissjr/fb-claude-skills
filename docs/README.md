last updated: 2026-02-23

# documentation

Authoritative index for all documentation in this repository.

## guides

| Document | Description |
|----------|-------------|
| [mcp-ecosystem.md](mcp-ecosystem.md) | Field guide to the full MCP ecosystem: protocol, tools, resources, apps, connectors, extensions, and how they relate |

See also the root [README.md](../README.md) for plugin installation, surface compatibility, and usage instructions.

## domain reports (`analysis/`)

Design documents and research created during development. 16 reports covering the full Claude extension ecosystem.

| Document | Description |
|----------|-------------|
| [plugin_system_architecture.md](analysis/plugin_system_architecture.md) | Plugin anatomy, schema, components, auto-discovery, audit |
| [marketplace_distribution_patterns.md](analysis/marketplace_distribution_patterns.md) | Marketplace schema, source types, monorepo, enterprise distribution |
| [mcp_protocol_and_servers.md](analysis/mcp_protocol_and_servers.md) | MCP protocol, primitives, transports, SDKs, registry |
| [mcp_apps_and_ui_development.md](analysis/mcp_apps_and_ui_development.md) | MCP Apps SDK, UI linkage, React hooks, framework templates |
| [hooks_system_patterns.md](analysis/hooks_system_patterns.md) | Hook events, types, matchers, security, automation patterns |
| [subagents_and_agent_teams.md](analysis/subagents_and_agent_teams.md) | Custom agents, tool control, teams, delegation patterns |
| [cross_surface_compatibility.md](analysis/cross_surface_compatibility.md) | Surface matrix, transports, permissions, headless mode |
| [claude_skills_best_practices_guide_full_report.md](analysis/claude_skills_best_practices_guide_full_report.md) | Skills best practices from Anthropic guide |
| [skills_guide_structured.md](analysis/skills_guide_structured.md) | Structured extraction from skills guide (for CDC) |
| [skills_guide_analysis.md](analysis/skills_guide_analysis.md) | Gap analysis: guide recommendations vs this repo |
| [self_updating_system_design.md](analysis/self_updating_system_design.md) | CDC architecture decisions and source inventory |
| [abstraction_analogies.md](analysis/abstraction_analogies.md) | Unifying design principle: selection under constraint |
| [duckdb_dimensional_model_strategy.md](analysis/duckdb_dimensional_model_strategy.md) | DuckDB star schema strategy for agent state |
| [data_centric_agent_state_research.md](analysis/data_centric_agent_state_research.md) | Research on data-centric LLM agent state management |
| [memory_and_rules_system.md](analysis/memory_and_rules_system.md) | Memory hierarchy, auto memory, CLAUDE.md imports, rules |
| [mcp_ecosystem_audit_2026-02-19.md](analysis/mcp_ecosystem_audit_2026-02-19.md) | MCP ecosystem audit: tools, registries, hosting |

## synthesis (`reports/`)

| Document | Description |
|----------|-------------|
| [claude_ecosystem_synthesis.md](reports/claude_ecosystem_synthesis.md) | Full ecosystem overview, decision tree, maturity assessment |

## skill-maintainer internals (`internals/`)

Technical documentation for the automated skill maintenance system.

| Document | Description |
|----------|-------------|
| [api_reference.md](internals/api_reference.md) | Function signatures, parameters, return types for all Python scripts |
| [schema.md](internals/schema.md) | Formal schemas for state.json and config.yaml |
| [duckdb_schema.md](internals/duckdb_schema.md) | DuckDB star schema tables, views, and dimensional model |
| [troubleshooting.md](internals/troubleshooting.md) | Common issues, error messages, and recovery procedures |

## captured external docs (`claude-docs/`)

Offline copies of upstream Claude Code documentation for reference and CDC comparison.

| Document | Topic |
|----------|-------|
| [claude_docs_plugins.md](claude-docs/claude_docs_plugins.md) | Plugin system overview |
| [claude_docs_plugins-reference.md](claude-docs/claude_docs_plugins-reference.md) | Plugin reference (schemas, fields) |
| [claude_docs_discover-plugins.md](claude-docs/claude_docs_discover-plugins.md) | Discovering and browsing plugins |
| [claude_docs_plugin-marketplaces.md](claude-docs/claude_docs_plugin-marketplaces.md) | Plugin marketplace setup |
| [claude_docs_skills.md](claude-docs/claude_docs_skills.md) | Skills system |
| [claude_docs_sub-agents.md](claude-docs/claude_docs_sub-agents.md) | Custom subagents |
| [claude_docs_hooks-guide.md](claude-docs/claude_docs_hooks-guide.md) | Hooks usage guide |
| [claude_docs_hooks_reference.md](claude-docs/claude_docs_hooks_reference.md) | Hooks reference (events, schemas) |
| [claude_docs_mcp.md](claude-docs/claude_docs_mcp.md) | MCP integration |
| [claude_docs_settings.md](claude-docs/claude_docs_settings.md) | Settings and configuration |
| [claude_docs_permissions.md](claude-docs/claude_docs_permissions.md) | Permission model |
| [claude_docs_sandboxing.md](claude-docs/claude_docs_sandboxing.md) | Sandboxing and security |
| [claude_docs_headless.md](claude-docs/claude_docs_headless.md) | Headless mode |
| [claude_docs_output-styles.md](claude-docs/claude_docs_output-styles.md) | Output styles |
| [claude_docs_troubleshooting.md](claude-docs/claude_docs_troubleshooting.md) | Troubleshooting |
| [claude_docs_cli-reference_reference.md](claude-docs/claude_docs_cli-reference_reference.md) | CLI reference |
| [interactive-mode.md](claude-docs/interactive-mode.md) | Interactive mode |
| [claude_generated_docs_dot_claude_folder.md](claude-docs/claude_generated_docs_dot_claude_folder.md) | .claude folder structure |
