last updated: 2026-09-24

# documentation

Authoritative index for all documentation in this repository.

See the root [README.md](../README.md) for plugin installation, surface compatibility, and usage instructions.

## internals (`internals/`)

Repo-specific operating reference. Spokes for the root [AGENTS.md](../AGENTS.md) hub, which `CLAUDE.md` imports.

| Document | Description |
|----------|-------------|
| [architecture.md](internals/architecture.md) | The worldview `VISION.md` retrieval serves: trees not workflows, model tiering, harness coupling, context isolation, use-before-prepare, structured outputs as state, verify by construction, compound feedback. Split out of `VISION.md` 2026-08-13 |
| [plugin-versioning.md](internals/plugin-versioning.md) | Full version cascade for plugin content changes; `sync-versions` coverage gaps; worked example |
| [plugin-patterns.md](internals/plugin-patterns.md) | Required plugin structure; hooks vs. skills; composable directives; scaffolder-not-broadcaster; bracket-the-hook; agents; bash 3.2 portability |
| [maintenance.md](internals/maintenance.md) | Automatic checks, on-demand commands, state files, workspace members |
| [phase_boundaries.md](internals/phase_boundaries.md) | The ordered tree at a phase boundary: continue, clear, hand off, subagent, compact. Why continue is ruled out first and compact is the default rather than the first reach. Adopted from mattpocock/skills 2026-08-13 |
| [gotchas.md](internals/gotchas.md) | security-hook disable, pre-commit re-install, path-privacy edges, CLAUDE.md size creep |
| [gemini_bridge_design.md](internals/gemini_bridge_design.md) | **Frozen record** (2026-08-02) of the gemini-bridge design session and the live probing that corrected it. History, not documentation |
| [foreign_capability_bridge.md](internals/foreign_capability_bridge.md) | The seven invariants a second bridge should follow; the capability/opinion/agent split and why mutation is the boundary; why it is a contract rather than a library at N=1 |
| [tiered_authorization.md](internals/tiered_authorization.md) | Gating expensive or external calls by tier: UserPromptExpansion provenance, PreToolUse policy, PermissionRequest subagent default-deny |
| [model_routing_flywheel.md](internals/model_routing_flywheel.md) | Why the delegation feedback layer was a report rather than a loop; schema, grain and cost fixes |
| [upstream_drift_backlog.md](internals/upstream_drift_backlog.md) | Unabsorbed upstream doc changes since the 2026-05-04 snapshot |
| [claim_audit_design.md](internals/claim_audit_design.md) | Design record for the claim-audit skill (diff prose audited by execution, instrument-yield routing); shipped as `skills/claim-audit/` |
| [audit_family_holds.md](internals/audit_family_holds.md) | What the audit family specified and deliberately did not build, the trigger that reopens each, and the tripwire for new proposals |
| [best_practices_maintenance.md](internals/best_practices_maintenance.md) | Why `best_practices.md` drifts: three kinds of knowledge (harness / model / craft) on one calendar clock. Source keep-add-remove verdicts, the hash-join proposal, ordered build list — analysed 2026-08-07, NOT started |
| [mcp_spec_2026_07_28.md](internals/mcp_spec_2026_07_28.md) | What MCP's 2026-07-28 spec breaks (stateless, no handshake, mandatory `server/discover`), where this repo's two MCP units actually stand, and why moving is a migration rather than a bump — filed 2026-08-07, NOT started |
| [context-cost.md](internals/context-cost.md) | Where context cost actually goes; the tier test for a rule; built-in introspection not to rebuild; transcript-mining traps |
| [control_audit_design.md](internals/control_audit_design.md) | Design record for control-audit: census plus live-fire over hooks, validators, reminders; why the adversarial primitive shipped first |
| [agent_state_population.md](internals/agent_state_population.md) | Why `agent-state` was retired rather than populated: every candidate duplicated a file, and effectiveness needs a controlled A/B |
| [postmortem_output_formats.md](internals/postmortem_output_formats.md) | Postmortem multi-format output (markdown + HTML, pluggable styling) — designed, NOT started |

## postmortems (`postmortems/`)

Dated retrospectives on finished work. [postmortems/README.md](postmortems/README.md)
states the frame and evidence standard; `.postmortem.json` resolves the directory,
and `/postmortem:postmortem-index` builds the browsable listing.

## evals

[evals/README.md](../evals/README.md): the committed `claude plugin eval` suites, how to run them, and the offline grader check.

## standing prompts

The improvement and optimizer loops live in the
[improvement-loops](../skills/improvement-loops/README.md) plugin as `/improve`
and `/optimize`. Their full text is in each skill's `references/`, where it can
also be copied into a session without installing.

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
The tracked pages are the `upstream_urls` in `.skill-maintainer/config.json`;
`watch_only_urls` are fetched and reported the same way but kept out of the
provenance join unless a section cites one.

Anything not tracked there is a link away at
[code.claude.com/docs](https://code.claude.com/docs/en/overview) — read it live
rather than copying it here.

