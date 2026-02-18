---
name: mece-decomposer
description: MECE decomposition methodology, scoring rubrics, and Agent SDK mapping for process analysis. Loaded automatically when decomposing goals, tasks, processes, or workflows into Mutually Exclusive, Collectively Exhaustive components. Provides the domain knowledge used by /decompose, /interview, /validate, and /export commands. Use when user says "decompose", "break down this process", "MECE analysis", "interview me about a workflow", "map process to agents", "validate decomposition", or "export to Agent SDK".
metadata:
  author: Fred Bliss
  version: 0.2.0
  mcp-server: mece-decomposer
---

# MECE Decomposer -- Domain Knowledge

This skill provides the methodology, scoring rubrics, and mapping rules that power the `/decompose`, `/interview`, `/validate`, and `/export` commands. Claude loads this automatically when those commands are invoked or when the conversation involves process decomposition.

## Core Concept

Business subject matter experts carry tacit knowledge about processes that lives as assumptions in their heads. MECE decomposition extracts and structures that knowledge into components that are:

- **Mutually Exclusive**: no overlap between sibling components
- **Collectively Exhaustive**: no gaps -- all cases covered

The decomposition serves two audiences simultaneously:
- **Humans**: readable tree for validation, communication, alignment
- **Agents**: structured JSON mapping to Claude Agent SDK primitives (`Agent`, `Runner`, hooks, handoffs)

## Decomposition Methodology

Detailed procedure in `references/decomposition_methodology.md`. Summary:

### Dimension Selection

Score candidates using the 4-criteria rubric:

| Dimension | Best For |
|-----------|----------|
| Temporal | Processes with clear sequential phases |
| Functional | Goals or capabilities without strict ordering |
| Stakeholder | Multi-team processes with handoffs |
| State | Workflows driven by entity state transitions |
| Input-Output | Data transformation pipelines |

Choose the dimension that produces the most natural, non-overlapping cut. Different branches may use different dimensions.

### Atomicity Criteria

A node is atomic (stop decomposing) when ALL hold:

| Criterion | Test |
|-----------|------|
| Co-occurrence | Sub-steps always execute together in this context |
| Single responsibility | Does exactly one thing with one clear outcome |
| Stable interface | Inputs and outputs are well-defined |
| Independent testability | Can verify without running the whole tree |
| SDK-mappable | Maps to one Agent, one tool call, one human action, or one external call |
| Bounded duration | Predictable, finite execution time |

The co-occurrence test is primary. If sub-steps can execute independently, keep decomposing.

### Fan-Out and Depth Limits

- 3-7 children per branch (2 minimum, 7 maximum)
- Max 7 parallel branches
- Warn at >5 depth levels
- Flag atoms with >5 tools or >500 word prompts

## MECE Scoring

| Score Range | ME Interpretation | CE Interpretation |
|-------------|-------------------|-------------------|
| 0.85 - 1.0 | Strong: no overlap | Strong: no gaps |
| 0.70 - 0.84 | Acceptable: minor boundary issues | Acceptable: minor gaps documented |
| 0.50 - 0.69 | Weak: redefine boundaries | Weak: add missing components |
| < 0.50 | Failed: re-cut this level | Failed: fundamental restructuring |

Quality gate: >= 0.70 for export, >= 0.85 for confidence.

### Depth-Adaptive Rigor

- **L1 (top level)**: Full ME/CE validation -- definition-based, example-based, boundary-case
- **L2**: Pairwise ME testing + scenario CE testing
- **L3**: Spot-check ME + stakeholder CE test
- **L4+**: Trust, only flag obvious issues

See `references/validation_heuristics.md` for the complete rubric.

## Agent SDK Mapping

Each atom maps to an SDK primitive based on execution type:

| Execution Type | SDK Primitive | Model Tier |
|---------------|---------------|------------|
| agent | `Agent` + `Runner.run()` | haiku / sonnet / opus based on complexity |
| human | Human-in-the-loop (webhook, ask_user_question, manual) | N/A |
| tool | Direct tool call | N/A |
| external | REST API, gRPC, message queue | N/A |

Branch orchestration types map to Python patterns:
- **sequential**: chained `await` calls
- **parallel**: `asyncio.gather()`
- **conditional**: `if/elif` routing
- **loop**: `for` with termination condition

See `references/agent_sdk_mapping.md` for complete mapping rules.

## Interactive Visualizer (MCP App)

This plugin includes an MCP App server that provides interactive tree visualization. When the `mece-decomposer` MCP server is connected, four MCP tools are available:

| MCP Tool | Purpose |
|----------|---------|
| `mece-decompose` | Render decomposition as interactive collapsible tree with score gauges |
| `mece-validate` | Display validation report with clickable issue navigation |
| `mece-refine-node` | Edit a node from the UI (app-only, not model-invoked) |
| `mece-export-sdk` | Preview generated Agent SDK code with copy button |

On surfaces with MCP App support (Claude Desktop, Cowork, Claude.ai), these display a React UI. On CLI surfaces, they return text summaries.

The MCP server starts automatically when this plugin is installed. The bundled server at `mcp-app/dist/index.cjs` is self-contained (no `node_modules` needed).

## Output Schema

The decomposition JSON schema is defined in `references/output_schema.md`. Key structure:

```json
{
  "metadata": { "scope", "trigger", "completion_criteria", "decomposition_dimension", ... },
  "tree": { "id", "label", "node_type", "children|atom_spec", ... },
  "cross_branch_dependencies": [{ "from_id", "to_id", "dependency_type", ... }],
  "validation_summary": { "me_score", "ce_score", "overall_score", "issues", ... }
}
```

## Structural Validation

Deterministic validation via script:

```bash
uv run mece-decomposer/skills/mece-decomposer/scripts/validate_mece.py <decomposition.json>
```

## References

| Reference | Purpose |
|-----------|---------|
| `references/output_schema.md` | Full JSON schema for decomposition output |
| `references/decomposition_methodology.md` | Step-by-step decomposition procedure |
| `references/sme_interview_protocol.md` | SME interview protocol (5 phases) |
| `references/validation_heuristics.md` | ME/CE scoring rubrics and depth-adaptive rigor |
| `references/agent_sdk_mapping.md` | Tree element to SDK primitive mapping rules |
| `scripts/validate_mece.py` | Deterministic structural validation |

## Credits

Concept by [Ron Zika](https://www.linkedin.com/in/ronzika/).
