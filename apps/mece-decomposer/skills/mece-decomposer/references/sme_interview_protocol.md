# SME Interview Protocol

last updated: 2026-02-17

Structured-but-conversational protocol for extracting tacit process knowledge from subject matter experts. The goal is to surface assumptions, edge cases, and decision criteria that SMEs know intuitively but rarely articulate.

## Extraction Modes

Not every extraction is a 45-minute interview. Select the mode that fits the situation.

| Mode | When to Use | Phases | Time |
|------|-------------|--------|------|
| **Full interview** | SME available for a dedicated session, process is undocumented | All 5 phases | 30-60 min |
| **Rapid extraction** | SME has 10-15 minutes, or you are working from a partial description | Phase 1 (compressed) + Phase 2 + Phase 5 | 10-15 min |
| **Document-assisted** | SOP, runbook, or flowchart exists but may be incomplete/outdated | Phase 1 (from doc) + Phase 3 (gaps only) + Phase 5 | 15-20 min |
| **Iterative async** | SME available via Slack/email, not in real-time | Phase 1 as initial message, then one phase per exchange | Variable |

### Full Interview

Run all 5 phases in order. This is the default when the user says "interview me."

### Rapid Extraction

Compress Phase 1 to 2 questions: "What is this process and when is it done?" + "What's out of scope?" Skip Phase 3 (exceptions) and Phase 4 (boundaries). Go straight to Phase 2 (happy path) then Phase 5 (validation). Flag that exceptions and boundary conditions are undiscovered.

### Document-Assisted

Start by reading the provided document. Pre-populate Phase 1 (scope) and Phase 2 (happy path) from the document. Skip directly to Phase 3 -- focus only on what the document does NOT cover: exceptions, edge cases, tribal knowledge. Then validate in Phase 5.

### Iterative Async

Structure each message as one self-contained question batch (2-3 questions). Include context from previous answers so the SME does not need to re-read the thread. After each response, update the decomposition tree and share it back.

## Principles

1. **Follow the SME's energy** -- let them talk about what they know best, steer gently
2. **Concrete before abstract** -- ask for examples first, then generalize
3. **One thing at a time** -- avoid compound questions
4. **Validate incrementally** -- confirm understanding after every 2-3 answers
5. **Name the silence** -- when the SME hesitates, the hesitation itself is information

## Phase 1: Context and Scope (3-5 Questions)

Goal: Establish the boundary of what we are decomposing.

### Opening Script

> "I'd like to understand [process/workflow/goal] well enough to break it into precise, non-overlapping components. I'll ask questions in phases -- first to understand the big picture, then to walk through the details. There are no wrong answers; I'm interested in how things actually work, not how they're documented."

### Core Questions

| # | Question | Probes If Unclear |
|---|----------|-------------------|
| 1 | "What process are we looking at? In one sentence, what does it accomplish?" | "If you had to explain this to a new hire in 15 seconds..." |
| 2 | "Who are the people or systems involved?" | "Anyone touch this that might not be obvious?" |
| 3 | "What kicks this off? What's the trigger?" | "Is there always a single trigger, or multiple entry points?" |
| 4 | "How do you know when it's done?" | "Is there a specific output, state change, or sign-off?" |
| 5 | "What's explicitly NOT part of this?" | "If someone asked you to include [adjacent process], would you?" |

### Success Criteria

Phase 1 is complete when you can state the scope in this format:

> "We are decomposing [process], which begins when [trigger], involves [stakeholders], and ends when [completion criteria]. It does NOT include [exclusions]."

Read this back to the SME and get explicit confirmation before proceeding.

## Phase 2: Happy Path Walkthrough (Open-Ended)

Goal: Get the SME to narrate the end-to-end process as it works when everything goes right.

### Opening Script

> "Let's walk through this as if everything goes perfectly. Start from the trigger and talk me through each step until it's done. I'll ask clarifying questions as we go."

### Per-Step Probes

As the SME describes each step, ask these probes (only the ones that are not already obvious):

| Probe | What It Surfaces |
|-------|------------------|
| "What exactly happens here?" | The actual activity (not the label) |
| "Who does this?" | Responsible actor (person, team, system) |
| "How long does this typically take?" | Duration and variability |
| "What information do they need to start?" | Input dependencies |
| "What do they produce when they're done?" | Output artifacts |
| "Is this always done, or only sometimes?" | Conditional execution |
| "Could this happen at the same time as the previous step?" | Parallelism opportunities |

### Capture Format

As the SME talks, build a running numbered list:

```
1. [Actor] does [action] using [inputs] to produce [outputs] (~duration)
2. [Actor] does [action]...
```

After every 3-4 steps, read back the list and ask: "Does this sound right so far? Anything I'm missing between steps [N] and [N+1]?"

### Common Extraction Challenges

**SME skips steps** (too obvious to mention):
> "Between [step N] and [step N+1], is there anything that happens that's so routine you might forget to mention it?"

**SME uses jargon**:
> "When you say '[jargon]', what specifically happens? If I were watching over someone's shoulder, what would I see?"

**SME gives the idealized version** (not the real one):
> "That's the official process. In practice, does it ever go differently? What shortcuts do people actually take?"

## Phase 3: Exception Discovery (Per Step)

Goal: Surface failure modes, edge cases, and conditional paths.

### Opening Script

> "Now let's go back through each step and think about what can go wrong or go differently."

### Per-Step Exception Questions

For each step from Phase 2:

| # | Question | What It Surfaces |
|---|----------|------------------|
| 1 | "What's the most common thing that goes wrong here?" | Primary failure mode |
| 2 | "When it does go wrong, what happens next?" | Error handling path |
| 3 | "Are there cases where this step gets skipped entirely?" | Conditional execution |
| 4 | "Are there different ways this step plays out depending on [input type / customer type / etc.]?" | Branching logic |
| 5 | "What's the worst-case scenario for this step?" | Edge cases and risk |

### Exception Capture

Add exceptions inline with the step they affect:

```
3. [Actor] does [action]...
   - Exception: [condition] -> [what happens instead]
   - Exception: [condition] -> [what happens instead]
   - Skip condition: [when this step is skipped]
```

### When the SME Says "That Never Happens"

Push gently once:
> "Even if it's rare -- like once a year -- what would happen?"

If they maintain it never happens, accept it and move on. Note it as a low-probability risk.

## Phase 4: Boundary Conditions

Goal: Discover handoffs, parallel activities, and upstream/downstream connections.

### Questions

| # | Question | What It Surfaces |
|---|----------|------------------|
| 1 | "Are there any steps where one person/team hands off to another?" | Handoff points (often where things break) |
| 2 | "Are there any activities that happen in parallel -- at the same time, independently?" | Parallel branches |
| 3 | "What happens before this process starts that you depend on?" | Upstream dependencies |
| 4 | "What happens after this process ends that depends on your output?" | Downstream consumers |
| 5 | "Are there any time constraints -- SLAs, deadlines, business hours?" | Temporal constraints |
| 6 | "Does anyone need to approve or sign off on anything along the way?" | Approval gates |

### Handoff Deep-Dive

For each handoff identified:

> "When [team A] hands off to [team B], what exactly gets passed? How does [team B] know it's their turn? What happens if [team B] doesn't pick it up?"

Handoffs are the most common source of cross-branch dependencies.

## Phase 5: Validation

Goal: Present the decomposition tree and iterate with the SME.

### Presentation Script

> "Based on everything you've told me, here's how I've broken this down. I want to check two things: (1) nothing overlaps -- each component is distinct, and (2) nothing is missing -- together they cover the whole process."

### Validation Sequence

1. **Show the L1 components first** -- get agreement on the high-level structure before drilling down
2. **For each L1 component, show L2** -- confirm the sub-breakdown
3. **Walk through 2-3 scenarios** -- "If [scenario X] happened, which path does it follow?"
4. **Ask the gap question**: "Is there anything about this process that none of these components capture?"
5. **Ask the overlap question**: "Are any of these components doing the same thing as another?"

### Iteration Protocol

When the SME flags an issue:

1. Confirm understanding: "So you're saying [paraphrase]?"
2. Identify the fix: is it a relabeling, a merge, a split, or a new component?
3. Apply the fix to the tree
4. Re-validate the affected level only (not the whole tree)

### Completion Criteria

The interview is complete when:
- The SME says the L1 and L2 structure looks correct
- At least 3 scenarios have been walked through without gaps
- No unresolved overlaps
- The SME confirms: "Yes, this covers it"

## Adaptive Behavior

### Structured Thinker

Signs: speaks in lists, uses process language, already has mental model.

Approach:
- Match their structure -- work top-down
- Ask for their categorization first, then validate MECE
- Move faster through Phase 2 (they'll be efficient)
- Spend more time on Phase 3 (they may under-report exceptions because they've mentally optimized them away)

### Narrative Thinker

Signs: tells stories, uses examples, jumps between topics.

Approach:
- Let them narrate in Phase 2 without interrupting the flow
- Take notes and organize after, not during
- Use their stories as scenarios in Phase 5
- Explicitly structure the output and confirm: "Here's what I heard, organized into steps..."

### Resistant / Time-Constrained SME

Signs: short answers, "it depends", wants to skip details.

Approach:
- Start with Phase 5 in reverse -- show a draft decomposition (even if speculative) and let them correct it
- Frame questions as confirmations: "My understanding is [X] -- is that right?" rather than open-ended questions
- Accept "it depends" as a signal of conditional logic -- probe: "What does it depend on?"
- Prioritize L1 and L2 accuracy; accept L3+ gaps and flag them for follow-up

## Output

The interview produces:
1. A completed scope definition (Phase 1 output)
2. A happy-path step list (Phase 2 output)
3. Exception annotations per step (Phase 3 output)
4. Boundary condition notes (Phase 4 output)
5. A validated decomposition tree (Phase 5 output)

These feed directly into the decomposition methodology (see `decomposition_methodology.md`) starting at Step 3 (first-level cut) with Steps 1 and 2 (scope and dimension) already completed from the interview.
