---
description: Extract process knowledge from an SME through structured MECE interview
argument-hint: "<process or workflow to interview about>"
---

# /interview

Structured conversational extraction of process knowledge from a subject matter expert. Produces a MECE decomposition through guided dialogue.

## Usage

```
/interview <process or workflow to extract>
```

Examples:
- `/interview our invoice approval workflow`
- `/interview the deployment process for our SaaS platform`
- `/interview` then describe what process you want to map

## How It Works

```
STANDALONE (always works)
- Structured 5-phase interview protocol
- Adapts to your communication style
- Produces MECE tree + Agent SDK JSON

SUPERCHARGED (when MCP server connected)
+ Interactive tree visualization as you build it
+ Click nodes to refine, validate scores live
```

## Interview Protocol

### Phase 1: Context and Scope (3-5 questions)

Establish what we are decomposing:
- What is the process and who is involved?
- What triggers it and when is it done?
- What is explicitly excluded?

### Phase 2: Happy Path Walkthrough (open-ended)

You narrate the end-to-end process as it works when everything goes right. I probe each step for:
- Who does it (actor)
- How long it takes (duration)
- What goes in and what comes out (inputs/outputs)
- Is it conditional or always happens (conditionality)
- Can things happen in parallel (parallelism)

### Phase 3: Exception Discovery (per step)

Go back through each step and surface:
- What fails and how
- Edge cases and skip conditions
- Branching logic

### Phase 4: Boundary Conditions

Discover handoffs, parallel activities, upstream dependencies, downstream consumers, time constraints, and approval gates.

### Phase 5: Validation

Present the decomposition tree and iterate until you confirm it covers the process completely without overlap.

## Adaptive Behavior

I adjust interview style based on how you think:

- **Structured thinker**: I match your top-down approach, validate MECE against your mental model
- **Narrative thinker**: I let you tell stories, organize afterward, use your stories as validation scenarios
- **Time-constrained**: I show a draft decomposition and let you correct it (Phase 5 first)

## Output

Same dual output as `/decompose`:
1. Human-readable tree (markdown)
2. Agent SDK JSON
3. Interactive visualization (when MCP server connected)

## Tips

1. **Don't worry about structure** -- just describe how things work. I'll organize it.
2. **Include the messy parts** -- exceptions and edge cases are the most valuable.
3. **Say "it depends"** -- that's a branching point, and I'll probe for conditions.
4. **Correct me freely** -- the tree is wrong until you say it's right.
