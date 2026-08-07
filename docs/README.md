last updated: 2026-08-07

# documentation

Authoritative index for all documentation in this repository.

See the root [README.md](../README.md) for plugin installation, surface compatibility, and usage instructions.

## internals (`internals/`)

Repo-specific operating reference. Spokes for the [root CLAUDE.md](../CLAUDE.md) hub.

| Document | Description |
|----------|-------------|
| [plugin-versioning.md](internals/plugin-versioning.md) | Full version cascade for plugin content changes; `sync-versions` coverage gaps; worked example |
| [plugin-patterns.md](internals/plugin-patterns.md) | Required plugin structure; hooks vs. skills; composable directives; scaffolder-not-broadcaster; bracket-the-hook; agents; bash 3.2 portability |
| [maintenance.md](internals/maintenance.md) | Automatic checks, on-demand commands, state files, workspace members |
| [gotchas.md](internals/gotchas.md) | best_practices duality, security-hook disable, pre-commit re-install, path-privacy edges, CLAUDE.md size creep |
| [gemini_bridge_design.md](internals/gemini_bridge_design.md) | **Frozen record** (2026-08-02) of the gemini-bridge design session and the live probing that corrected it. History, not documentation |
| [foreign_capability_bridge.md](internals/foreign_capability_bridge.md) | The seven invariants a second bridge should follow; the capability/opinion/agent split and why mutation is the boundary; why it is a contract rather than a library at N=1 |
| [tiered_authorization.md](internals/tiered_authorization.md) | Gating expensive or external calls by tier: UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny |
| [model_routing_flywheel.md](internals/model_routing_flywheel.md) | Why the delegation feedback layer was a report rather than a loop; schema, grain and cost fixes |
| [upstream_drift_backlog.md](internals/upstream_drift_backlog.md) | Unabsorbed upstream doc changes since the 2026-05-04 snapshot |
| [claim_audit_design.md](internals/claim_audit_design.md) | Spec for the claim-audit skill (diff prose audited by execution, instrument-yield routing) — designed 2026-08-03, NOT started |
| [best_practices_maintenance.md](internals/best_practices_maintenance.md) | Why `best_practices.md` drifts: three kinds of knowledge (harness / model / craft) on one calendar clock. Source keep-add-remove verdicts, the hash-join proposal, ordered build list — analysed 2026-08-07, NOT started |
| [mcp_spec_2026_07_28.md](internals/mcp_spec_2026_07_28.md) | What MCP's 2026-07-28 spec breaks (stateless, no handshake, mandatory `server/discover`), where this repo's two MCP units actually stand, and why moving is a migration rather than a bump — filed 2026-08-07, NOT started |
| [context-cost.md](internals/context-cost.md) | Where context cost actually goes; the tier test for a rule; built-in introspection not to rebuild; transcript-mining traps |
| [control_audit_design.md](internals/control_audit_design.md) | Design record for control-audit: census plus live-fire over hooks, validators, reminders; why the adversarial primitive shipped first |
| [agent_state_population.md](internals/agent_state_population.md) | Why `agent-state` was retired rather than populated: every candidate duplicated a file, and effectiveness needs a controlled A/B |
| [postmortem_output_formats.md](internals/postmortem_output_formats.md) | Postmortem multi-format output (markdown + HTML, pluggable styling) — designed, NOT started |

## package documentation

| Document | Description |
|----------|-------------|
| [skill-maintainer README](../tools/skill-maintainer/README.md) | CLI reference, data flow, workflow, configuration |

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

That writes `.skill-maintainer/state/pages/*.md` (gitignored), reports a
per-page line and character delta against the previous snapshot, and then runs
the provenance join described in [maintenance.md](internals/maintenance.md).
Eleven pages are tracked, listed in `.skill-maintainer/config.json`: skills,
plugins, plugins-reference, plugin-marketplaces, hooks, hooks-guide,
sub-agents, memory, settings, permissions, mcp. `discover-plugins` was dropped
on 2026-08-07 — no section of `best_practices.md` derived from it, which the
join's `unattributed` bucket surfaced.

Anything not tracked there is a link away at
[code.claude.com/docs](https://code.claude.com/docs/en/overview) — read it live
rather than copying it here.

