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
| [upstream_drift_backlog.md](internals/upstream_drift_backlog.md) | Unabsorbed upstream doc changes since the 2026-05-04 snapshot |
| [explainer_video_roadmap.md](internals/explainer_video_roadmap.md) | explainer-video per-item ledger: what shipped, what was refuted, what is still open |
| [explainer_video_generalization_plan.md](internals/explainer_video_generalization_plan.md) | The arc that took explainer-video from one visual language to two backends, shot language and style bibles — with the run's postmortem |
| [explainer_video_test_cases.md](internals/explainer_video_test_cases.md) | The test suite: cases as falsifiable hypotheses, with outcomes filled in |
| [explainer_video_hardening_plan.md](internals/explainer_video_hardening_plan.md) | The remediation: ~51 findings grouped by root cause, structural fixes separated from deliberate bandaids |
| [screenwright_plan.md](internals/screenwright_plan.md) | Founding plan for the WebGPU/TSL successor skill: layer split, character scaffold, test-case portfolio, phase gates — explainer-video freezes |
| [physics_bake_proposal.md](internals/physics_bake_proposal.md) | Owner-prioritized Phase 4 direction: bake-time simulation with runtime determinism intact — red lines against tier drift, eval criteria, spike list |

## package documentation

| Document | Description |
|----------|-------------|
| [agent-state README](../tools/agent-state/README.md) | Schema reference (v2), CLI, Python API, migration guide |
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

