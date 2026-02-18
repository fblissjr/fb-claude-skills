# mece-decomposer

last updated: 2026-02-17

A Claude Code skill that decomposes goals, tasks, processes, and workflows into MECE (Mutually Exclusive, Collectively Exhaustive) components. Produces dual output -- a human-readable tree for SME validation and structured JSON that maps directly to Claude Agent SDK primitives for agentic execution.

## Problem

Business SMEs have tacit knowledge about processes that is stuck in their heads as assumptions. When building agentic workflows with Claude Agent SDK, the hardest part is defining "what good looks like" -- and SMEs can't articulate that without decomposing the process into granular components first.

## What It Does

Takes any input -- a goal, a process description, an SOP, a live conversation with an SME -- and produces:

1. **Human-readable tree** for validation and communication
2. **Structured JSON** that maps directly to Agent SDK primitives (`Agent`, `Runner`, hooks, handoffs)

The decomposition itself becomes the shared contract between humans and agents.

### Example Output (Human-Readable)

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

## Installation

```bash
# from within Claude Code:
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install mece-decomposer@fb-claude-skills
```

Or from the terminal:

```bash
claude plugin marketplace add fblissjr/fb-claude-skills
claude plugin install mece-decomposer@fb-claude-skills
```

## Commands

| Command | Purpose |
|---------|---------|
| `decompose` | Break down a goal, process, or workflow into MECE components with SDK mapping |
| `interview` | Extract process knowledge from an SME through structured conversation |
| `validate` | Check an existing decomposition for MECE compliance and structural integrity |
| `export` | Generate Agent SDK code scaffolding from a validated decomposition |

## Skill Structure

```
mece-decomposer/
+-- .claude-plugin/
|   +-- plugin.json
+-- README.md
+-- skills/
    +-- mece-decomposer/
        +-- SKILL.md                                    # Core skill definition
        +-- references/
        |   +-- decomposition_methodology.md            # 8-step decomposition procedure
        |   +-- sme_interview_protocol.md               # 5-phase conversational extraction
        |   +-- validation_heuristics.md                # ME/CE scoring rubrics
        |   +-- agent_sdk_mapping.md                    # Tree -> Agent SDK mapping rules
        |   +-- output_schema.md                        # Full JSON schema specification
        +-- scripts/
            +-- validate_mece.py                        # Deterministic structural validator
```

## Validation Script

Structural validation of decomposition JSON output:

```bash
uv run mece-decomposer/skills/mece-decomposer/scripts/validate_mece.py <decomposition.json>
```

Checks schema compliance, hierarchical ID consistency, dependency validity, fan-out limits, atomicity completeness, and cross-checks declared summary stats against computed values.

## Dependencies

- `orjson` -- JSON serialization for the validation script

## Credits

Idea genesis from [Ron Zika](https://www.linkedin.com/in/ronzika/).
