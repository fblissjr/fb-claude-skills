last updated: 2026-02-14

# documentation index

## internals

Technical documentation for the skill-maintainer system.

| Document | Description |
|----------|-------------|
| [api_reference.md](internals/api_reference.md) | Function signatures, parameters, return types, and side effects for all Python scripts |
| [schema.md](internals/schema.md) | Formal schemas for state.json and config.yaml |
| [troubleshooting.md](internals/troubleshooting.md) | Common issues, error messages, and recovery procedures |

## analysis

Research and design documentation created during initial development.

| Document | Description |
|----------|-------------|
| [skills_guide_structured.md](analysis/skills_guide_structured.md) | Full structured extraction from the 30-page Anthropic skills guide PDF |
| [skills_guide_analysis.md](analysis/skills_guide_analysis.md) | Gap analysis comparing guide recommendations against repo skills |
| [self_updating_system_design.md](analysis/self_updating_system_design.md) | Cross-reference of all source materials with architecture decisions |

## captured external docs

| Directory | Description |
|-----------|-------------|
| [blogs/](blogs/) | Captured blog posts (Anthropic complete guide to building skills) |
| [claude-docs/](claude-docs/) | Captured Claude Code official docs (plugins, skills, marketplace, reference) |
| [guides/](guides/) | PDF guide source (The Complete Guide to Building Skills for Claude) |

### claude-docs contents

| Document | Source |
|----------|--------|
| [claude_docs_plugins.md](claude-docs/claude_docs_plugins.md) | Plugins quickstart, structure, migration |
| [claude_docs_skills.md](claude-docs/claude_docs_skills.md) | Skills frontmatter, substitutions, invocation, advanced patterns |
| [claude_docs_plugin_reference.md](claude-docs/claude_docs_plugin_reference.md) | CLI commands, manifest schema, directory structure, debugging |
| [claude_docs_discover_plugins.md](claude-docs/claude_docs_discover_plugins.md) | Marketplace management, plugin install/uninstall, scope options |
| [claude_docs_plugin_marketplaces.md](claude-docs/claude_docs_plugin_marketplaces.md) | Marketplace schema, plugin sources, distribution |
