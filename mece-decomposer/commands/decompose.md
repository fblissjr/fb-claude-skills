---
description: Break down a goal, process, or workflow into MECE components with Agent SDK mapping
argument-hint: "<process, goal, or workflow description>"
---

# /decompose

Decompose a process, goal, or workflow into MECE (Mutually Exclusive, Collectively Exhaustive) components with dual output -- a human-readable tree and structured JSON mapping to Claude Agent SDK primitives.

## Usage

```
/decompose <description of what to decompose>
```

Examples:
- `/decompose our customer onboarding process from sign-up to first value delivery`
- `/decompose the CI/CD pipeline for our microservices architecture`
- `/decompose quarterly financial close process`
- `/decompose` then paste a JSON/YAML/CSV export from a workflow tool

## Workflow

### 1. Interpret Input

If the user provides structured data (JSON, XML, YAML, CSV, or any workflow/process export), do NOT assume you understand the schema. Ask what the data represents, what key fields mean, and how entities relate. Present your interpretation back, let them correct it, repeat until agreed. For free-text, skip this.

### 2. Define Scope

Establish boundary, trigger, and completion criteria. If ambiguous, ask clarifying questions. Do not guess at scope boundaries.

### 3. Select Dimension

Score candidate dimensions (temporal, functional, stakeholder, state, input-output) using the 4-criteria rubric from the **mece-decomposer** skill. Document the winner and rationale.

### 4. First-Level Cut

Produce 3-7 L1 components. Apply full MECE validation (see `references/validation_heuristics.md`).

### 5. Recursive Descent

Decompose each L1. Choose dimension per branch (may differ from L1). Decrease validation rigor with depth per the depth-adaptive schedule.

### 6. Atomicity Testing

At each leaf, apply the co-occurrence heuristic. Classify atoms by execution type: agent, human, tool, or external.

### 7. Cross-Branch Dependencies

Identify data, sequencing, resource, and approval dependencies between branches.

### 8. SDK Mapping

Map atoms to Agent SDK primitives per `references/agent_sdk_mapping.md`. Assign model tiers.

### 9. Validation Sweep

Run final structural checks. Compute ME/CE scores.

## Output

### 1. Human-Readable Tree (markdown)

```
Process Name (orchestration type)
+-- Phase 1 (parallel)
|   +-- [agent] Step A (~5m, sonnet)
|   +-- [human] Step B (~2h, webhook)
+-- Phase 2 (sequential)
    +-- [tool] Step C (~10s, tool_name)
    +-- [agent] Step D (~1m, haiku)
```

Each line: label, execution type in brackets, estimated duration, model tier or integration method.

### 2. Agent SDK JSON

Full JSON conforming to `references/output_schema.md`. To validate structurally:

```bash
uv run mece-decomposer/skills/mece-decomposer/scripts/validate_mece.py <output.json>
```

### 3. Interactive Visualization (when MCP server connected)

After producing the JSON, call the `mece-decompose` MCP tool with the full JSON string to render the interactive tree in Claude Desktop, Cowork, or Claude.ai.

## Next Steps

After decomposition:
- "Want me to validate this decomposition for MECE compliance?" -> `/validate`
- "Should we refine any branches through an SME interview?" -> `/interview`
- "Ready to export Agent SDK code?" -> `/export`
