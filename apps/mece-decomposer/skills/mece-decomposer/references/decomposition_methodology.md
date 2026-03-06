# Decomposition Methodology

last updated: 2026-02-17

Step-by-step procedure for MECE decomposition. Claude follows these steps in order, though iteration is expected -- later steps often reveal issues that require revisiting earlier decisions.

## Step 1: Scope Definition

Before decomposing anything, define what you are decomposing and what lies outside the boundary.

### Required Outputs

| Element | Question | Example |
|---------|----------|---------|
| **Scope statement** | What process/goal/workflow are we decomposing? | "Customer order fulfillment from order placement to delivery confirmation" |
| **Trigger** | What event initiates this? | "Customer clicks 'Place Order' button" |
| **Completion criteria** | How do you know it's done? | "Customer receives delivery confirmation email and tracking shows 'Delivered'" |
| **Inclusions** | What is explicitly in scope? | Payment processing, inventory allocation, shipping, notifications |
| **Exclusions** | What is explicitly out of scope? | Returns, refunds, customer support escalations |

### Scope Boundary Test

Ask: "If I removed this item, would the process still be complete from trigger to completion?" If yes, it is a candidate for exclusion. If no, it must be included.

### Common Scope Failures

- **Too broad**: "Run the business" -- no clear trigger or completion
- **Too narrow**: "Validate email format" -- already atomic, nothing to decompose
- **Fuzzy boundaries**: "Handle customer issues" -- overlaps with too many processes

If scope is unclear, switch to the interview protocol (see `sme_interview_protocol.md`) to extract it conversationally.

## Step 2: Dimension Selection

Choose the primary dimension along which the first-level cut will be made. The dimension determines the "lens" through which you see the components.

### Candidate Dimensions

| Dimension | Cuts By | Best For | Example |
|-----------|---------|----------|---------|
| **Temporal** | When things happen | Processes with clear phases | Onboarding: pre-arrival -> day 1 -> week 1 -> month 1 |
| **Functional** | What kind of work | Cross-functional processes | Order: payment + inventory + shipping + notification |
| **Stakeholder** | Who does the work | Multi-team processes | Hiring: recruiter + hiring manager + HR + IT |
| **State** | What state the entity is in | Status-driven workflows | Ticket: new -> triaged -> assigned -> resolved -> closed |
| **Input-Output** | What flows in and out | Data transformation pipelines | ETL: extract -> transform -> validate -> load |

### Scoring Criteria

Score each candidate dimension 0-2 on these criteria:

| Criterion | 0 | 1 | 2 |
|-----------|---|---|---|
| **Natural fit** | Forced, unintuitive grouping | Partially natural | Obviously correct lens |
| **Clean boundaries** | Significant overlap between groups | Some boundary ambiguity | Crisp, unambiguous splits |
| **Balanced depth** | One branch deep, others shallow | Moderate imbalance | Roughly equal complexity per branch |
| **SDK mappability** | Hard to map to agent orchestration | Partially mappable | Clean 1:1 mapping to orchestration patterns |

Select the dimension with the highest total score. Document the rationale and runner-up.

### Mixed Dimensions

The first-level cut uses one dimension. Child branches may use different dimensions. This is normal and expected -- e.g., temporal at L1, functional at L2 within each phase.

## Step 3: First-Level Cut

Produce 3-7 top-level components using the selected dimension.

### Procedure

1. List candidate components based on the dimension
2. Merge any that always co-occur (they are not truly separate)
3. Split any that contain obviously distinct sub-activities
4. Verify count is 3-7 (fewer = too coarse, more = too fine for L1)

### MECE Validation at L1

This level gets the most rigorous validation:

**Mutual Exclusivity Check** (every pair):
- For each pair of L1 components, ask: "Can a single activity belong to both?"
- If yes, the boundary is not clean -- redefine one or both components

**Collective Exhaustiveness Check**:
- List 5-10 concrete scenarios that fall within scope
- For each scenario, identify which L1 component handles it
- If any scenario is unhandled, there is a gap

See `validation_heuristics.md` for detailed scoring.

### Output Format

Document as a flat list before going deeper:

```
1. [Label] -- [One-sentence description of what this covers and does not cover]
2. [Label] -- [...]
3. [Label] -- [...]
```

## Step 4: Recursive Descent

For each L1 component, repeat the decomposition process: choose a dimension (may differ from L1), produce 2-7 children, validate MECE.

### Rigor by Depth

| Level | MECE Rigor | Validation |
|-------|-----------|------------|
| L1 | Full pairwise ME + exhaustive CE | Every pair tested, 5+ scenarios |
| L2 | Full pairwise ME + quick CE | Every pair tested, 3+ scenarios |
| L3 | Spot-check ME + structural CE | Sample pairs, negation test |
| L4+ | Trust-based | Rely on atomicity criteria to stop |

### When to Stop Descending

Stop when any component passes the atomicity test (Step 5). Do not force uniform depth -- some branches are naturally deeper than others.

### Depth Warnings

- **Max recommended depth**: 5 levels. Beyond this, the tree becomes unwieldy.
- **Depth imbalance > 3 levels**: If one branch is 5 levels deep and another is 2, reconsider the L1 cut -- the deep branch may need to be split at L1.

## Step 5: Atomicity Testing

An atom is the smallest unit that cannot be decomposed further without losing coherence. Apply these tests to determine if a node should be a leaf.

### Primary Test: Co-Occurrence Heuristic

> "If I split this into sub-steps, would one sub-step ever execute without the others in this context?"

- **No**: The sub-steps always co-occur. This is an atom -- do not split further.
- **Yes**: The sub-steps are independently triggerable. Continue decomposing.

### Supporting Tests (All Must Pass)

| Test | Pass Criterion |
|------|----------------|
| **Single responsibility** | The node does exactly one thing with one clear outcome |
| **Stable interface** | Inputs and outputs are well-defined and unlikely to change |
| **Independent testability** | You can verify this node works without running the whole tree |
| **SDK-mappable** | Maps cleanly to one `Agent`, one `AskUserQuestion`, one tool call, or one external integration |
| **Bounded duration** | Has a predictable, finite execution time |

### Atomicity Failures

If a node fails atomicity, it must be decomposed further. Common patterns:

- **"Validate and process"** -- two responsibilities (split into validate + process)
- **"Handle all error cases"** -- multiple independent paths (split by error type)
- **"Coordinate between X and Y"** -- orchestration, not execution (make it a branch with X and Y as children)

### Atom Classification

Once confirmed atomic, classify by `execution_type`:

| If the atom... | execution_type |
|----------------|---------------|
| Requires reasoning, language understanding, or judgment | `agent` |
| Requires human decision, approval, or physical action | `human` |
| Is a deterministic operation (API call, file op, calculation) | `tool` |
| Interacts with an external system outside the agent runtime | `external` |

## Step 6: Cross-Branch Dependency Analysis

After the tree is complete, scan for dependencies between atoms in different branches.

### Dependency Discovery Questions

For each atom, ask:
1. "Does this atom need data produced by an atom in a different branch?" (data dependency)
2. "Must this atom wait for an atom in a different branch to complete?" (sequencing dependency)
3. "Does this atom contend for a resource also used by another branch?" (resource dependency)
4. "Does this atom require sign-off from a step in another branch?" (approval dependency)

### Recording Dependencies

Record each dependency in the flat `cross_branch_dependencies` array (see `output_schema.md`). Do not embed dependency references within the tree nodes -- keep them external to avoid circular references.

### Dependency Impact on Orchestration

- **Data dependencies** between parallel branches: the consuming atom must wait for the producing atom, which may force a sequencing constraint
- **Resource dependencies**: may require a semaphore or mutex pattern in orchestration
- **Approval dependencies**: typically introduce a human-in-the-loop pause

If cross-branch dependencies are extensive (>10), the tree structure may be wrong. Consider re-cutting at L1.

## Step 7: SDK Mapping Pass

Convert the validated tree into executable Agent SDK primitives. See `agent_sdk_mapping.md` for full mapping rules.

### Quick Reference

| Tree Element | SDK Primitive |
|-------------|---------------|
| Atom (agent) | `Agent(name, model, instructions, tools)` |
| Atom (human) | `AskUserQuestion` or webhook |
| Atom (tool) | Direct tool call |
| Atom (external) | External API integration |
| Branch (sequential) | Chained `Runner.run()` calls |
| Branch (parallel) | `asyncio.gather()` of `Runner.run()` calls |
| Branch (conditional) | Hook-based routing |
| Branch (loop) | While-loop with termination check |
| Cross-branch dependency | Session/context passing between agents |

### Model Tier Selection

| Tier | When to Use | Cost Signal |
|------|-------------|-------------|
| `haiku` | Simple extraction, formatting, classification | Low |
| `sonnet` | Analysis, summarization, multi-step reasoning | Medium |
| `opus` | Complex judgment, ambiguous inputs, novel situations | High |

Default to `sonnet` unless there is a clear reason for haiku (simple) or opus (complex).

## Step 8: Validation Sweep

Final pass over the complete tree. See `validation_heuristics.md` for detailed procedures.

### Checklist

1. Every branch has 2-7 children
2. Every atom passes all atomicity tests
3. No atom has >5 tools (split if so)
4. No atom has >500 word prompt (simplify if so)
5. All cross-branch dependencies reference valid node IDs
6. No circular dependencies
7. ME score >= 0.7 at every level
8. CE score >= 0.7 at every level
9. Tree depth <= 5
10. Hierarchical IDs are consistent (parent.child pattern)

### When Validation Fails

- **ME failure** (overlap detected): Redefine boundaries between overlapping siblings, or merge them and re-split along a different dimension
- **CE failure** (gap detected): Add missing component, or broaden an existing sibling's scope
- **Structural failure** (too deep, too wide): Re-cut at a higher level

Document all validation results in the `validation_summary` (see `output_schema.md`).
