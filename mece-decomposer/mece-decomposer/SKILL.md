---
name: mece-decomposer
description: Decomposes goals, tasks, processes, and workflows into MECE (Mutually Exclusive, Collectively Exhaustive) components. Produces dual output -- a human-readable tree for SME validation and structured JSON that maps directly to Claude Agent SDK primitives for agentic execution. Bridges tacit knowledge to executable agents.
---

# MECE Decomposer

## Purpose

Business subject matter experts carry tacit knowledge about processes that lives as assumptions in their heads. When building agentic workflows with Claude Agent SDK, the hardest part is defining "what good looks like" -- and SMEs cannot articulate that without first decomposing the process into granular, non-overlapping components.

This skill applies MECE decomposition to any input -- goals, tasks, processes, workflows -- and produces output that serves two audiences simultaneously:

- **Human-readable tree**: for SME validation, communication, and alignment
- **Structured JSON**: maps directly to Claude Agent SDK primitives (`Agent`, `Runner`, hooks, handoffs) for agentic execution

The decomposition itself becomes the shared contract between humans and agents.

## Commands

| Command | Purpose |
|---------|---------|
| `decompose` | Break down a goal, process, or workflow into MECE components with SDK mapping |
| `interview` | Extract process knowledge from an SME through structured conversation |
| `validate` | Check an existing decomposition for MECE compliance and structural integrity |
| `export` | Generate Agent SDK code scaffolding from a validated decomposition |

---

## decompose

Takes a process, goal, or workflow description and produces a complete MECE decomposition with both human-readable and machine-readable output.

### Usage

The user provides a description of what to decompose. This can range from a single sentence to a detailed specification.

> "Decompose our customer onboarding process from sign-up to first value delivery"

> "Break down the CI/CD pipeline for our microservices architecture"

> "MECE decompose: quarterly financial close process"

### Process

Follow the methodology in `references/decomposition_methodology.md`. In summary:

1. **Define scope** -- establish boundary, trigger, and completion criteria. If the input is ambiguous, ask clarifying questions before proceeding. Do not guess at scope boundaries.

2. **Select dimension** -- score candidate dimensions (temporal, functional, stakeholder, state, input-output) using the 4-criteria rubric. Document the winner and rationale.

3. **First-level cut** -- produce 3-7 L1 components. Apply full MECE validation (see `references/validation_heuristics.md`).

4. **Recursive descent** -- decompose each L1 component. Choose dimension per branch (may differ from L1). Decrease validation rigor with depth per the depth-adaptive schedule.

5. **Atomicity testing** -- at each leaf, apply the co-occurrence heuristic and supporting tests. Classify atoms by execution type (agent/human/tool/external).

6. **Cross-branch dependency scan** -- identify data, sequencing, resource, and approval dependencies between branches.

7. **SDK mapping** -- map atoms to Agent SDK primitives per `references/agent_sdk_mapping.md`. Assign model tiers.

8. **Validation sweep** -- run final structural checks. Compute ME/CE scores.

### Output

Produce two outputs:

**1. Human-readable tree** (markdown)

```
Employee Onboarding (sequential)
+-- Pre-Arrival Setup (parallel)
|   +-- [agent] Provision IT Equipment (~5m, sonnet)
|   +-- [human] Prepare HR Documents (~2h, webhook)
+-- Day One Orientation (sequential)
|   +-- [agent] Generate Welcome Package (~3m, haiku)
|   +-- [human] Team Introduction (~1h, manual)
+-- First Week Training (sequential)
    +-- [agent] Create Training Plan (~10m, sonnet)
    +-- [agent] Assess Initial Progress (~5m, sonnet)
```

Each line shows: label, execution type in brackets, estimated duration, model tier (for agents) or integration method (for humans).

**2. Agent SDK JSON**

Full JSON conforming to the schema in `references/output_schema.md`. This is the machine-readable contract.

To validate the JSON structurally, run:

```bash
uv run scripts/validate_mece.py <output.json>
```

---

## interview

Structured conversational extraction of process knowledge from a subject matter expert. Use this when the process is not documented or when documentation is outdated.

### Usage

> "Interview me about our invoice approval workflow"

> "I need to extract our deployment process -- let's do an SME interview"

### Process

Follow the protocol in `references/sme_interview_protocol.md`. The interview has five phases:

1. **Context and Scope** (3-5 questions) -- establish what we are decomposing, who is involved, what triggers it, when it is done, and what is excluded.

2. **Happy Path Walkthrough** (open-ended) -- the SME narrates the end-to-end process as it works when everything goes right. Probe each step for actor, duration, inputs, outputs, conditionality, and parallelism.

3. **Exception Discovery** (per step) -- go back through each step and surface failure modes, edge cases, skip conditions, and branching logic.

4. **Boundary Conditions** -- discover handoffs, parallel activities, upstream dependencies, downstream consumers, time constraints, and approval gates.

5. **Validation** -- present the decomposition tree and iterate with the SME until they confirm it covers the process completely without overlap.

### Adaptive Behavior

Adjust interview style based on the SME:

- **Structured thinker**: match their top-down approach, validate MECE against their mental model
- **Narrative thinker**: let them tell stories, organize afterward, use their stories as validation scenarios
- **Resistant/time-constrained**: show a draft decomposition and let them correct it (Phase 5 first)

### Output

Same dual output as `decompose` -- human-readable tree + Agent SDK JSON.

---

## validate

Check an existing decomposition (JSON) for MECE compliance, structural integrity, and SDK readiness.

### Usage

> "Validate this decomposition JSON"

> "Check if my MECE tree is structurally valid"

### Process

Two validation layers:

**1. Structural validation** (deterministic, via script)

```bash
uv run scripts/validate_mece.py <decomposition.json>
```

Checks:
- Schema compliance (all required fields, correct types, valid enums)
- Hierarchical ID consistency (parent-child prefix pattern)
- Cross-branch dependency reference validity (all IDs exist, no self-references)
- Fan-out limits (2-7 children per branch, max 7 parallel)
- Atom completeness (all atoms have `atom_spec`, all branches have `orchestration`)
- Prompt/tool limits (flag atoms with >5 tools or >500 word prompts)
- Depth limits (warn at >5 levels)

**2. MECE quality assessment** (judgment-based, by Claude)

Apply the heuristics in `references/validation_heuristics.md`:
- ME testing: definition-based, example-based, boundary-case at each level
- CE testing: scenario enumeration, negation test, stakeholder test
- Depth-adaptive rigor (L1 full, L2 pairwise, L3 spot-check, L4+ trust)
- Compute aggregate scores with weighted averaging

### Output

Validation report with:
- Pass/fail status
- ME score, CE score, overall score
- Issue list (errors, warnings, info) with locations and descriptions
- Recommendations for fixing failures

---

## export

Generate Claude Agent SDK Python code scaffolding from a validated decomposition.

### Usage

> "Export this decomposition as Agent SDK code"

> "Generate the Python scaffolding for this MECE tree"

### Process

1. Verify the decomposition passes validation (run `validate` first if not already validated)
2. Apply the mapping rules in `references/agent_sdk_mapping.md`
3. Generate Python code with:
   - One `Agent` definition per agent atom
   - Orchestration functions per branch type (sequential, parallel, conditional, loop)
   - Cross-branch dependency wiring
   - Hook-based error handling from atom error modes
   - Model tier assignments

### Output

Python module with:
- Agent definitions
- Orchestration functions
- A `main()` entry point that executes the tree
- Comments linking each code section to its tree node ID

---

## Decomposition Quality

### Atomicity Criteria

A node is atomic (should not be decomposed further) when ALL of these hold:

| Criterion | Test |
|-----------|------|
| **Co-occurrence** | Sub-steps always execute together in this context |
| **Single responsibility** | Does exactly one thing with one clear outcome |
| **Stable interface** | Inputs and outputs are well-defined |
| **Independent testability** | Can verify it works without running the whole tree |
| **SDK-mappable** | Maps to one Agent, one tool call, one human action, or one external call |
| **Bounded duration** | Predictable, finite execution time |

The co-occurrence test is primary. If sub-steps can execute independently, keep decomposing.

See `references/decomposition_methodology.md` Step 5 for the full procedure.

### MECE Scoring

| Score Range | ME Interpretation | CE Interpretation |
|-------------|-------------------|-------------------|
| 0.85 - 1.0 | Strong: no overlap | Strong: no gaps |
| 0.70 - 0.84 | Acceptable: minor boundary issues | Acceptable: minor gaps documented |
| 0.50 - 0.69 | Weak: redefine boundaries | Weak: add missing components |
| < 0.50 | Failed: re-cut this level | Failed: fundamental restructuring |

Overall quality gate: >= 0.70 for export, >= 0.85 for confidence.

See `references/validation_heuristics.md` for the full scoring rubric.

---

## Examples

### Example 1: Business Process (Invoice Approval)

**Input**: "Decompose our invoice approval workflow from receipt to payment"

**Output (human-readable tree)**:

```
Invoice Approval Workflow (sequential)
+-- Invoice Receipt and Logging (sequential)
|   +-- [tool] Extract Invoice Data (~10s, OCR/parse)
|   +-- [agent] Validate Invoice Completeness (~1m, haiku)
|   +-- [agent] Match to Purchase Order (~2m, sonnet)
+-- Review and Approval (conditional)
|   condition: invoice_amount threshold
|   +-- Standard Approval (sequential)        [amount < $5000]
|   |   +-- [agent] Auto-Approve Check (~30s, haiku)
|   |   +-- [human] Manager Sign-Off (~4h, webhook)
|   +-- Escalated Approval (sequential)       [amount >= $5000]
|       +-- [human] Director Review (~8h, webhook)
|       +-- [human] VP Sign-Off (~24h, webhook)
+-- Payment Processing (sequential)
    +-- [agent] Generate Payment Instructions (~1m, sonnet)
    +-- [external] Submit to Payment System (~30s, rest_api)
    +-- [agent] Send Confirmation (~30s, haiku)
```

### Example 2: Technical Workflow (CI/CD Pipeline)

**Input**: "Break down our CI/CD pipeline from commit to production deployment"

**Output (human-readable tree)**:

```
CI/CD Pipeline (sequential)
+-- Build Phase (sequential)
|   +-- [tool] Checkout Source (~5s, git)
|   +-- [tool] Install Dependencies (~30s, package manager)
|   +-- [tool] Compile/Bundle (~2m, build tool)
+-- Test Phase (parallel)
|   +-- [tool] Run Unit Tests (~3m, test runner)
|   +-- [tool] Run Integration Tests (~5m, test runner)
|   +-- [tool] Run Linter/Static Analysis (~1m, linter)
|   +-- [tool] Security Scan (~2m, scanner)
+-- Deploy Phase (sequential)
|   +-- [agent] Generate Release Notes (~2m, sonnet)
|   +-- [tool] Deploy to Staging (~3m, deployment tool)
|   +-- [agent] Run Smoke Tests (~2m, sonnet)
|   +-- [human] Approve Production Deploy (~1h, webhook)
|   +-- [tool] Deploy to Production (~3m, deployment tool)
+-- Post-Deploy (parallel)
    +-- [agent] Monitor Error Rates (~5m, sonnet)
    +-- [agent] Notify Stakeholders (~30s, haiku)
```

### Example 3: Abstract Goal (Improve Customer Retention)

**Input**: "Decompose our goal to improve customer retention"

This is a goal, not a process -- it decomposes along a functional dimension rather than temporal.

**Output (human-readable tree)**:

```
Improve Customer Retention (parallel)
+-- Churn Prediction (sequential)
|   +-- [agent] Analyze Usage Patterns (~10m, opus)
|   +-- [agent] Score Churn Risk (~5m, sonnet)
|   +-- [agent] Generate At-Risk List (~2m, haiku)
+-- Proactive Engagement (conditional)
|   condition: churn_risk_tier
|   +-- High Risk (sequential)                [risk > 0.8]
|   |   +-- [human] Personal Outreach (~30m, manual)
|   |   +-- [agent] Create Retention Offer (~5m, sonnet)
|   +-- Medium Risk (sequential)              [0.4 < risk <= 0.8]
|   |   +-- [agent] Send Targeted Campaign (~2m, sonnet)
|   +-- Low Risk (sequential)                 [risk <= 0.4]
|       +-- [agent] Schedule Check-In (~1m, haiku)
+-- Product Improvement (sequential)
|   +-- [agent] Aggregate Feedback Themes (~10m, sonnet)
|   +-- [agent] Prioritize Feature Requests (~5m, opus)
|   +-- [human] Review and Approve Roadmap (~2h, manual)
+-- Measurement (sequential)
    +-- [agent] Track Retention Metrics (~5m, sonnet)
    +-- [agent] Generate Monthly Report (~5m, sonnet)
```

---

## Composability

### Inputs This Skill Accepts

| Input Type | Description | Example |
|-----------|-------------|---------|
| Verbal description | Free-text process/goal description | "Our hiring process from req to start date" |
| SOP / documentation | Existing written procedures | "Here's our runbook for incident response" |
| Flowcharts / diagrams | Visual process representations | "I have a Mermaid diagram of our approval flow" |
| Existing decomposition | JSON from a previous decomposition | "Validate and refine this tree" |
| SME conversation | Live interview with a domain expert | "Interview me about our onboarding process" |

### Outputs This Skill Produces

| Output Type | Format | Consumer |
|-------------|--------|----------|
| Human-readable tree | Markdown (indented text tree) | SMEs, product managers, documentation |
| Agent SDK JSON | JSON per `references/output_schema.md` | Claude Agent SDK, orchestration code |
| Validation report | JSON | Quality assurance, iteration |
| SDK code scaffold | Python | Developers building agentic workflows |

### Integration Points

- **Upstream**: Any source of process knowledge (documents, SMEs, existing systems)
- **Downstream**: Claude Agent SDK for execution, documentation systems for reference, visualization tools for presentation

## References

| Reference | Purpose |
|-----------|---------|
| `references/output_schema.md` | Full JSON schema specification for decomposition output |
| `references/decomposition_methodology.md` | Step-by-step decomposition procedure |
| `references/sme_interview_protocol.md` | Conversational extraction protocol for SME interviews |
| `references/validation_heuristics.md` | ME/CE scoring rubrics and depth-adaptive rigor |
| `references/agent_sdk_mapping.md` | Mapping rules from tree elements to SDK primitives |
| `scripts/validate_mece.py` | Deterministic structural validation of output JSON |

## Credits

Concept by [Ron Zika](https://www.linkedin.com/in/ronzika/).
