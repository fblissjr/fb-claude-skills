# Output Schema

last updated: 2026-02-17

The canonical JSON schema for MECE decomposition output. Every decomposition produced by this skill conforms to this schema. The structure serves two audiences: humans read the tree visually, agents consume the JSON programmatically.

## Top-Level Structure

```json
{
  "metadata": { ... },
  "tree": { ... },
  "cross_branch_dependencies": [ ... ],
  "validation_summary": { ... }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata` | `Metadata` | yes | Scope, dimension, source, version info |
| `tree` | `Node` | yes | Root node of the decomposition tree |
| `cross_branch_dependencies` | `Dependency[]` | yes | Flat list of inter-branch dependencies (empty array if none) |
| `validation_summary` | `ValidationSummary` | yes | Aggregate ME/CE scores and flagged issues |

## Metadata

```json
{
  "scope": "string",
  "trigger": "string",
  "completion_criteria": "string",
  "decomposition_dimension": "temporal | functional | stakeholder | state | input_output | custom",
  "dimension_rationale": "string",
  "source_type": "sme_interview | document | verbal | observation | hybrid",
  "inclusions": ["string"],
  "exclusions": ["string"],
  "version": "string",
  "created_at": "ISO 8601 datetime string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scope` | string | yes | What this decomposition covers -- the boundary statement |
| `trigger` | string | yes | What initiates the process/workflow |
| `completion_criteria` | string | yes | How you know the process is done |
| `decomposition_dimension` | enum | yes | Primary dimension used for the first-level cut |
| `dimension_rationale` | string | yes | Why this dimension was selected over alternatives |
| `source_type` | enum | yes | How the knowledge was acquired |
| `inclusions` | string[] | no | Explicitly in-scope items (empty if not specified) |
| `exclusions` | string[] | no | Explicitly out-of-scope items (empty if not specified) |
| `version` | string | yes | Schema version, currently `"1.0.0"` |
| `created_at` | string | yes | ISO 8601 timestamp of creation |

## Node (Recursive, Discriminated)

Every node in the tree is one of two types, discriminated by `node_type`.

### Common Fields (All Nodes)

```json
{
  "id": "string",
  "node_type": "branch | atom",
  "label": "string",
  "description": "string",
  "depth": 0,
  "parent_id": "string | null"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Hierarchical ID: `"1"`, `"1.1"`, `"1.1.2"` etc. |
| `node_type` | `"branch"` or `"atom"` | yes | Discriminator field |
| `label` | string | yes | Human-readable short name (2-6 words) |
| `description` | string | yes | What this node represents and why it exists as a unit |
| `depth` | integer | yes | Tree depth (root = 0) |
| `parent_id` | string or null | yes | Parent node ID, null for root |

### Branch Node

A branch node has children and an orchestration strategy. It never has an `atom_spec`.

```json
{
  "id": "1",
  "node_type": "branch",
  "label": "Order Fulfillment",
  "description": "End-to-end order processing from receipt to delivery",
  "depth": 0,
  "parent_id": null,
  "orchestration": "sequential | parallel | conditional | loop",
  "orchestration_rationale": "string",
  "condition": "string | null",
  "loop_spec": { ... } | null,
  "children": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `orchestration` | enum | yes | How children relate to each other |
| `orchestration_rationale` | string | yes | Why this orchestration was chosen |
| `condition` | string | no | For `conditional`: the branching condition expression |
| `loop_spec` | `LoopSpec` | no | For `loop`: iteration details |
| `children` | `Node[]` | yes | Child nodes (minimum 2, maximum 7) |

#### LoopSpec

```json
{
  "iterator": "string",
  "termination": "string",
  "max_iterations": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iterator` | string | yes | What is being iterated over |
| `termination` | string | yes | When the loop stops |
| `max_iterations` | integer | no | Safety bound (0 = unbounded) |

### Atom Node

An atom is a leaf node -- the smallest unit that cannot be decomposed further without losing coherence. It always has an `atom_spec` and never has `children`.

```json
{
  "id": "1.2.1",
  "node_type": "atom",
  "label": "Validate Shipping Address",
  "description": "Verify address completeness and deliverability",
  "depth": 2,
  "parent_id": "1.2",
  "atom_spec": { ... }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `atom_spec` | `AtomSpec` | yes | Execution specification (see below) |

## AtomSpec (Discriminated by execution_type)

```json
{
  "execution_type": "agent | human | tool | external",
  "estimated_duration": "string",
  "inputs": ["string"],
  "outputs": ["string"],
  "error_modes": ["string"],
  ...type-specific fields
}
```

### Common AtomSpec Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `execution_type` | enum | yes | Discriminator for execution strategy |
| `estimated_duration` | string | yes | Human-readable estimate (e.g. `"30s"`, `"5m"`, `"2h"`) |
| `inputs` | string[] | yes | What this atom needs to start |
| `outputs` | string[] | yes | What this atom produces when done |
| `error_modes` | string[] | yes | Known failure scenarios |

### execution_type: "agent"

Maps to Claude Agent SDK's `Agent` class.

```json
{
  "execution_type": "agent",
  "estimated_duration": "2m",
  "inputs": ["order_data", "inventory_snapshot"],
  "outputs": ["allocation_result"],
  "error_modes": ["insufficient_stock", "invalid_sku"],
  "agent_definition": {
    "name": "string",
    "description": "string",
    "prompt": "string",
    "tools": ["string"],
    "model": "haiku | sonnet | opus",
    "model_rationale": "string",
    "max_turns": 0
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_definition.name` | string | yes | Agent identifier (snake_case) |
| `agent_definition.description` | string | yes | One-line purpose statement |
| `agent_definition.prompt` | string | yes | System prompt for the agent |
| `agent_definition.tools` | string[] | yes | Tool names the agent can use |
| `agent_definition.model` | enum | yes | Model tier selection |
| `agent_definition.model_rationale` | string | yes | Why this model tier was chosen |
| `agent_definition.max_turns` | integer | no | Turn limit (0 = unlimited) |

### execution_type: "human"

Requires human action. Maps to `AskUserQuestion` tool or external webhook.

```json
{
  "execution_type": "human",
  "estimated_duration": "1h",
  "inputs": ["draft_document"],
  "outputs": ["approved_document", "revision_notes"],
  "error_modes": ["rejection", "timeout"],
  "human_instruction": {
    "action": "string",
    "context": "string",
    "decision_criteria": "string",
    "escalation": "string",
    "integration_method": "ask_user_question | webhook | manual"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `human_instruction.action` | string | yes | What the human needs to do |
| `human_instruction.context` | string | yes | Background info the human needs |
| `human_instruction.decision_criteria` | string | yes | How the human should decide |
| `human_instruction.escalation` | string | no | What to do if the human is unavailable |
| `human_instruction.integration_method` | enum | yes | How the system waits for the human |

### execution_type: "tool"

Direct tool invocation without an agent wrapper.

```json
{
  "execution_type": "tool",
  "estimated_duration": "5s",
  "inputs": ["file_path"],
  "outputs": ["file_contents"],
  "error_modes": ["file_not_found", "permission_denied"],
  "tool_invocation": {
    "tool_name": "string",
    "parameters": {},
    "retry_policy": "none | fixed | exponential",
    "max_retries": 0
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_invocation.tool_name` | string | yes | Tool identifier |
| `tool_invocation.parameters` | object | yes | Static parameter template (may include `"$ref"` placeholders) |
| `tool_invocation.retry_policy` | enum | no | Retry strategy on failure |
| `tool_invocation.max_retries` | integer | no | Retry count limit |

### execution_type: "external"

Integration with external systems outside the agent runtime.

```json
{
  "execution_type": "external",
  "estimated_duration": "30s",
  "inputs": ["api_request"],
  "outputs": ["api_response"],
  "error_modes": ["timeout", "auth_failure", "rate_limit"],
  "external_integration": {
    "system": "string",
    "operation": "string",
    "protocol": "rest_api | grpc | message_queue | file_system | database",
    "timeout": "string",
    "fallback": "string"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `external_integration.system` | string | yes | Target system name |
| `external_integration.operation` | string | yes | What operation to perform |
| `external_integration.protocol` | enum | yes | Integration protocol |
| `external_integration.timeout` | string | no | Max wait time |
| `external_integration.fallback` | string | no | What to do if the system is unavailable |

## Cross-Branch Dependencies

A flat top-level array to avoid bidirectional references within the tree. Each dependency describes a relationship between two atoms in different branches.

```json
{
  "from_id": "string",
  "to_id": "string",
  "dependency_type": "data | sequencing | resource | approval",
  "description": "string",
  "artifact": "string | null"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_id` | string | yes | Source atom ID (producer) |
| `to_id` | string | yes | Target atom ID (consumer) |
| `dependency_type` | enum | yes | Nature of the dependency |
| `description` | string | yes | What flows between these atoms |
| `artifact` | string | no | Named data artifact if applicable |

### Dependency Types

- **data**: `to_id` needs output produced by `from_id`
- **sequencing**: `to_id` must wait for `from_id` to complete (no data exchange)
- **resource**: both atoms contend for the same limited resource
- **approval**: `to_id` requires explicit sign-off from `from_id`

## Validation Summary

Computed during the validation sweep. Captures the structural quality of the decomposition.

```json
{
  "me_score": 0.0,
  "ce_score": 0.0,
  "overall_score": 0.0,
  "levels_assessed": 0,
  "total_nodes": 0,
  "total_atoms": 0,
  "total_branches": 0,
  "max_depth": 0,
  "max_fan_out": 0,
  "issues": [ ... ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `me_score` | float | Mutual exclusivity score, 0.0-1.0 |
| `ce_score` | float | Collective exhaustiveness score, 0.0-1.0 |
| `overall_score` | float | Weighted average: `0.5 * me_score + 0.5 * ce_score` |
| `levels_assessed` | integer | How many tree levels were validated |
| `total_nodes` | integer | Total nodes in the tree |
| `total_atoms` | integer | Count of atom (leaf) nodes |
| `total_branches` | integer | Count of branch (internal) nodes |
| `max_depth` | integer | Deepest level in the tree |
| `max_fan_out` | integer | Largest number of children on any branch |
| `issues` | `Issue[]` | Flagged problems, sorted by severity |

### Issue

```json
{
  "severity": "error | warning | info",
  "location": "string",
  "issue_type": "overlap | gap | fan_out | depth | atomicity | dependency | schema",
  "message": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `severity` | enum | `error` blocks export, `warning` needs review, `info` is advisory |
| `location` | string | Node ID or path where the issue was found |
| `issue_type` | enum | Category of the issue |
| `message` | string | Human-readable description |

## Full Example (Abbreviated)

```json
{
  "metadata": {
    "scope": "Employee onboarding from offer acceptance to first productive day",
    "trigger": "Candidate accepts employment offer",
    "completion_criteria": "New hire completes first assigned task independently",
    "decomposition_dimension": "temporal",
    "dimension_rationale": "Onboarding has clear sequential phases with natural time boundaries",
    "source_type": "sme_interview",
    "inclusions": ["IT setup", "HR paperwork", "team introduction", "training"],
    "exclusions": ["recruiting", "salary negotiation", "performance reviews"],
    "version": "1.0.0",
    "created_at": "2026-02-17T10:00:00Z"
  },
  "tree": {
    "id": "1",
    "node_type": "branch",
    "label": "Employee Onboarding",
    "description": "Complete onboarding process from offer acceptance to productive day one",
    "depth": 0,
    "parent_id": null,
    "orchestration": "sequential",
    "orchestration_rationale": "Phases have strict temporal dependencies",
    "children": [
      {
        "id": "1.1",
        "node_type": "branch",
        "label": "Pre-Arrival Setup",
        "description": "Everything that happens before the employee's first day",
        "depth": 1,
        "parent_id": "1",
        "orchestration": "parallel",
        "orchestration_rationale": "IT and HR setup can happen simultaneously",
        "children": [
          {
            "id": "1.1.1",
            "node_type": "atom",
            "label": "Provision IT Equipment",
            "description": "Order and configure laptop, accounts, and access badges",
            "depth": 2,
            "parent_id": "1.1",
            "atom_spec": {
              "execution_type": "agent",
              "estimated_duration": "5m",
              "inputs": ["employee_profile", "role_requirements"],
              "outputs": ["equipment_order", "account_credentials"],
              "error_modes": ["equipment_unavailable", "license_limit_reached"],
              "agent_definition": {
                "name": "it_provisioner",
                "description": "Generates IT provisioning checklist and account setup instructions",
                "prompt": "Given an employee profile and role requirements, produce a complete IT provisioning plan including hardware, software licenses, and access permissions.",
                "tools": ["Read", "Write"],
                "model": "sonnet",
                "model_rationale": "Requires analysis of role-to-permission mapping but not complex reasoning",
                "max_turns": 5
              }
            }
          },
          {
            "id": "1.1.2",
            "node_type": "atom",
            "label": "Prepare HR Documents",
            "description": "Generate and send employment paperwork for signature",
            "depth": 2,
            "parent_id": "1.1",
            "atom_spec": {
              "execution_type": "human",
              "estimated_duration": "2h",
              "inputs": ["offer_letter", "employee_data"],
              "outputs": ["signed_documents"],
              "error_modes": ["missing_information", "signature_timeout"],
              "human_instruction": {
                "action": "Review and sign employment documents",
                "context": "Standard onboarding paperwork including NDA, tax forms, and benefits enrollment",
                "decision_criteria": "All fields completed accurately, no discrepancies with offer terms",
                "escalation": "Notify HR manager if not completed within 48 hours",
                "integration_method": "webhook"
              }
            }
          }
        ]
      }
    ]
  },
  "cross_branch_dependencies": [],
  "validation_summary": {
    "me_score": 0.95,
    "ce_score": 0.90,
    "overall_score": 0.925,
    "levels_assessed": 2,
    "total_nodes": 4,
    "total_atoms": 2,
    "total_branches": 2,
    "max_depth": 2,
    "max_fan_out": 2,
    "issues": []
  }
}
```

## Schema Version History

| Version | Changes |
|---------|---------|
| `1.0.0` | Initial schema release |
