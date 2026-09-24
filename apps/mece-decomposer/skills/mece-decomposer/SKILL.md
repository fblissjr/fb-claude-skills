---
name: mece-decomposer
description: MECE decomposition methodology, scoring rubrics, and Agent SDK mapping for process analysis. Loaded automatically when decomposing goals, tasks, processes, or workflows into Mutually Exclusive, Collectively Exhaustive components. Provides the domain knowledge used by /decompose, /interview, /validate, and /export commands. Use when user says "decompose", "break down this process", "MECE analysis", "interview me about a workflow", "map process to agents", "validate decomposition", or "export to Agent SDK".
metadata:
  mcp-server: mece-decomposer
allowed-tools: "Bash(uv run *)"
---

# MECE decomposer: domain knowledge

The house rules behind `/decompose`, `/interview`, `/validate` and `/export`. MECE itself is assumed knowledge; what follows is the part a model cannot derive: the atomicity test, the numeric limits and gates, the scoring formulas, and the mapping from tree to agent code.

A decomposition turns an SME's tacit process knowledge into a tree with two readers: a human validating it, and an orchestrator executing it from the JSON.

<method>
- **Scope first.** Every decomposition names its trigger, completion criteria and exclusions before any cut, because an unbounded scope has no exhaustiveness to test against.
- **Choose one dimension per level** (temporal, functional, stakeholder, state, input-output) by scoring the candidates; branches may cut along different dimensions from their parent. The rubric: [references/decomposition_methodology.md](references/decomposition_methodology.md).
- **A node is atomic when its sub-steps always co-occur in this context.** The co-occurrence test is primary; if one sub-step can run without the others, keep decomposing. An atom also has one responsibility, a stable interface, independent testability, bounded duration, and maps to exactly one agent, tool call, human action or external call.
- **Classify every atom** by `execution_type`: `agent` (judgment or language), `human` (decision, approval, physical action), `tool` (deterministic operation), `external` (system outside the agent runtime).
- **Cross-branch dependencies** (data, sequencing, resource, approval) live in the flat `cross_branch_dependencies` array, never inside tree nodes, so the tree cannot hold a cycle.
</method>

<limits>
Normative, enforced by `scripts/validate_mece.py` (its constants are the source): 2 to 7 children per branch, at most 7 parallel children, depth beyond 5 warns, and an atom with more than 5 tools or a prompt over 500 words is flagged. Validation rigor decreases with depth: L1 full pairwise ME and scenario CE, L2 pairwise, L3 spot-check, L4+ relies on the atomicity test.
</limits>

<scoring>
| Score | ME | CE |
|-------|----|----|
| 0.85 - 1.0 | Strong: no overlap | Strong: no gaps |
| 0.70 - 0.84 | Acceptable: minor boundary issues | Acceptable: minor gaps documented |
| 0.50 - 0.69 | Weak: redefine boundaries | Weak: add missing components |
| < 0.50 | Failed: re-cut this level | Failed: restructure |

Gate: overall >= 0.70 to export, >= 0.85 to call it confident. The test weights and the depth-weighted aggregation are in [references/validation_heuristics.md](references/validation_heuristics.md).
</scoring>

<sdk_mapping>
| Tree element | Maps to |
|---|---|
| `agent` atom | one agent definition, model tier `haiku` / `sonnet` / `opus` (default `sonnet`) |
| `human` atom | human-in-the-loop gate (ask-user tool or webhook) |
| `tool` atom | direct tool call, no agent wrapper |
| `external` atom | API call via MCP server or custom tool |
| sequential / parallel / conditional / loop branch | chained awaits / `asyncio.gather()` / routing / bounded loop |

Full rules and templates: [references/agent_sdk_mapping.md](references/agent_sdk_mapping.md).
</sdk_mapping>

<output>
The JSON shape is defined in [references/output_schema.md](references/output_schema.md): `metadata` (scope, trigger, completion criteria, dimension), `tree` (nodes with `children` or `atom_spec`), `cross_branch_dependencies`, and `validation_summary` (scores and issues). Check it structurally with:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/validate_mece.py <decomposition.json>
```
</output>

<visualizer>
The plugin's stdio MCP server (`mcp-app/dist/index.cjs`, self-contained, started with the plugin) exposes four tools:

| MCP tool | Purpose |
|----------|---------|
| `mece-decompose` | render the decomposition as a collapsible tree with score gauges |
| `mece-validate` | render the validation report with clickable issue locations |
| `mece-refine-node` | edit a node from the UI (app-only, not model-invoked) |
| `mece-export-sdk` | preview generated agent code with a copy button |

Cowork renders the React UI. CLI, Desktop, VS Code, the Agent SDK and Claude.ai (which needs HTTP transport for the UI) get the text fallback, and all four tools remain callable.
</visualizer>

<references>
| Reference | Holds |
|-----------|-------|
| `references/output_schema.md` | the JSON schema |
| `references/decomposition_methodology.md` | dimension scoring, cut and atomicity judgment calls |
| `references/sme_interview_protocol.md` | extraction modes, confirmation points, interview gotchas |
| `references/validation_heuristics.md` | ME/CE tests, weights, aggregation |
| `references/agent_sdk_mapping.md` | tree-to-code templates and model tiers |
| `scripts/validate_mece.py` | deterministic structural validation |
</references>

Concept by [Ron Zika](https://www.linkedin.com/in/ronzika/).
