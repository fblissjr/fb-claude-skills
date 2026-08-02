last updated: 2026-07-23

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
| [gemini_bridge_design.md](internals/gemini_bridge_design.md) | Gemini Interactions API facts established by live probing; why every static source was wrong; what is deliberately not built |
| [foreign_capability_bridge.md](internals/foreign_capability_bridge.md) | The seven invariants a second bridge should follow; the capability/opinion/agent split and why mutation is the boundary; why it is a contract rather than a library at N=1 |
| [tiered_authorization.md](internals/tiered_authorization.md) | Gating expensive or external calls by tier: UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny |
| [model_routing_flywheel.md](internals/model_routing_flywheel.md) | Why the delegation feedback layer was a report rather than a loop; schema, grain and cost fixes |
| [upstream_drift_backlog.md](internals/upstream_drift_backlog.md) | Unabsorbed upstream doc changes since the 2026-05-04 snapshot |

## package documentation

| Document | Description |
|----------|-------------|
| [skill-maintainer README](../tools/skill-maintainer/README.md) | CLI reference, data flow, workflow, configuration |

## domain reports (`analysis/`)

Design documents and research created during development. Cover the full Claude extension ecosystem.

| Document | Description |
|----------|-------------|
| [mcp_protocol_and_servers.md](analysis/mcp_protocol_and_servers.md) | MCP protocol, primitives, transports, SDKs, registry |
| [data_centric_agent_state_research.md](analysis/data_centric_agent_state_research.md) | Research on data-centric LLM agent state management |

## synthesis (`reports/`)

| Document | Description |
|----------|-------------|

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

