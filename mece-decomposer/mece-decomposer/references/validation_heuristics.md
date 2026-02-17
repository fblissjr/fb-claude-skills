# Validation Heuristics

last updated: 2026-02-17

Scoring rubrics and procedures for validating MECE properties of a decomposition tree. Validation is applied at each level of the tree with rigor that decreases with depth.

## Mutual Exclusivity (ME) Testing

ME tests verify that sibling nodes do not overlap -- no single activity, scenario, or work item should belong to more than one sibling.

### Test 1: Definition-Based ME

Compare the descriptions of each sibling pair. Ask: "Is there any activity that fits both descriptions?"

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | Definitions are clearly disjoint with no ambiguity |
| 1 | Definitions are mostly disjoint but have a gray zone (e.g., "setup" vs "configuration") |
| 0 | Definitions overlap -- a concrete activity could reasonably belong to either |

**Procedure:**
1. List all sibling pairs at the level being tested (for N siblings, there are N*(N-1)/2 pairs)
2. For each pair, compare definitions and assign a score
3. Level ME-definition score = average across all pairs, normalized to 0-1

### Test 2: Example-Based ME

Generate 3-5 concrete examples of activities within the scope. For each example, determine which sibling it belongs to.

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | Every example maps to exactly one sibling with no hesitation |
| 1 | Most examples map cleanly, but 1-2 could arguably go to multiple siblings |
| 0 | Multiple examples map to multiple siblings |

**Procedure:**
1. Generate examples that represent the full range of work within the parent scope
2. For each example, assign it to a sibling
3. Flag any example that could be assigned to more than one sibling
4. Level ME-example score = (examples with unique assignment) / (total examples)

### Test 3: Boundary-Case ME

Deliberately construct edge cases that sit at the boundary between two siblings. These are the hardest test.

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | Even constructed boundary cases have a clear home |
| 1 | Boundary cases require a judgment call but a reasonable person would agree |
| 0 | Boundary cases genuinely belong to both siblings |

**Procedure:**
1. For each sibling pair, construct 1-2 boundary cases
2. Attempt to assign each to exactly one sibling
3. If assignment requires creating a rule that is not already in the description, the boundary is not clean
4. Level ME-boundary score = (clean assignments) / (total boundary cases)

### Aggregate ME Score

```
ME_score = 0.3 * ME_definition + 0.4 * ME_example + 0.3 * ME_boundary
```

Weights emphasize example-based testing because it uses concrete scenarios rather than abstract comparison.

| ME Score | Interpretation | Action |
|----------|---------------|--------|
| 0.85 - 1.0 | Strong ME | Proceed |
| 0.70 - 0.84 | Acceptable ME | Note boundary issues for documentation |
| 0.50 - 0.69 | Weak ME | Redefine boundaries between overlapping siblings |
| < 0.50 | Failed ME | Re-cut this level with a different dimension |

## Collective Exhaustiveness (CE) Testing

CE tests verify that sibling nodes together cover the entire scope of their parent -- no activity within the parent's scope should be unrepresented.

### Test 1: Scenario Enumeration

List concrete scenarios that fall within the parent's scope. Verify each has a home.

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | All scenarios map to a sibling |
| 1 | Most scenarios map, but 1-2 fall in a gray area or require "stretching" a sibling's scope |
| 0 | One or more scenarios have no home |

**Procedure:**
1. Generate 5-10 scenarios representing different types of work within the parent scope
2. Include at least 2 "unusual but valid" scenarios
3. For each, identify which sibling handles it
4. Level CE-scenario score = (covered scenarios) / (total scenarios)

### Test 2: Negation Test

For each sibling, ask: "If this sibling did not exist, what would be lost?" The union of all answers should equal the parent's scope.

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | Removing any sibling leaves a clear, named gap |
| 1 | Removing some siblings leaves a gap, but 1-2 siblings' removal would be partially absorbed by others |
| 0 | One or more siblings could be removed without losing coverage |

**Procedure:**
1. For each sibling, describe what would be lost if it were removed
2. Check: does the union of all "loss descriptions" equal the parent's full scope?
3. If a sibling's removal creates no unique loss, it may be redundant (ME issue) or the scope is already covered by others (restructure needed)
4. Level CE-negation score = (siblings with unique contribution) / (total siblings)

### Test 3: Stakeholder Test

Ask each stakeholder group: "Is there any work you do within [parent scope] that doesn't fit into any of these categories?"

**Scoring:**

| Score | Meaning |
|-------|---------|
| 2 | No stakeholder identifies missing work |
| 1 | Minor gaps identified (administrative overhead, communication tasks) |
| 0 | Significant work categories are missing |

**Procedure:**
1. List all stakeholder groups involved in the parent scope
2. For each, check if their work is fully represented
3. Pay special attention to support roles (admin, coordination, communication) which are often omitted
4. Level CE-stakeholder score = (fully represented stakeholders) / (total stakeholders)

Note: In decompositions from documents rather than interviews, the stakeholder test may not be possible. Use scenario and negation tests only.

### Aggregate CE Score

```
CE_score = 0.4 * CE_scenario + 0.35 * CE_negation + 0.25 * CE_stakeholder
```

Weights emphasize scenario enumeration as the most concrete test.

| CE Score | Interpretation | Action |
|----------|---------------|--------|
| 0.85 - 1.0 | Strong CE | Proceed |
| 0.70 - 0.84 | Acceptable CE | Explicitly note known gaps in documentation |
| 0.50 - 0.69 | Weak CE | Add missing components or broaden existing siblings |
| < 0.50 | Failed CE | Fundamental re-examination of the decomposition |

## Depth-Adaptive Rigor

Not every level needs the same validation intensity. Apply rigor proportional to the level's impact on correctness.

### Level 1 (Full Pairwise)

- **ME**: All three tests, full pairwise comparison of every sibling pair
- **CE**: All three tests with 5+ scenarios
- **Target**: ME >= 0.85, CE >= 0.85
- **Rationale**: L1 errors cascade to the entire tree

### Level 2 (Pairwise + Quick CE)

- **ME**: Definition-based + example-based for all pairs. Boundary-case only for pairs flagged as ambiguous.
- **CE**: Scenario enumeration (3+ scenarios) + negation test. Skip stakeholder test unless the parent branch spans multiple teams.
- **Target**: ME >= 0.75, CE >= 0.75
- **Rationale**: L2 errors affect one branch, not the whole tree

### Level 3 (Spot-Check)

- **ME**: Definition-based for all pairs. Example-based only for the 2-3 most ambiguous pairs.
- **CE**: Negation test only (quick check that each sibling adds unique value).
- **Target**: ME >= 0.70, CE >= 0.70
- **Rationale**: At this depth, atomicity testing is doing most of the quality assurance

### Level 4+ (Trust)

- **ME**: No formal testing. Rely on the atomicity criteria to prevent incorrect splits.
- **CE**: Verify that the parent node's description is fully covered by the children's descriptions.
- **Target**: No numeric target
- **Rationale**: Deep nodes are specific enough that MECE violations are rare

## Combined Scoring

### Overall Score

```
overall_score = 0.5 * ME_score + 0.5 * CE_score
```

Equal weighting -- overlap is as harmful as gaps.

### Score Aggregation Across Levels

The tree-level score is the depth-weighted average:

```
tree_score = sum(level_score * level_weight) / sum(level_weights)

level_weights: L1 = 1.0, L2 = 0.8, L3 = 0.5, L4+ = 0.2
```

### Quality Gates

| Overall Score | Status | Meaning |
|--------------|--------|---------|
| >= 0.85 | Pass | Ready for SDK mapping and export |
| 0.70 - 0.84 | Conditional pass | Exportable with documented caveats |
| 0.50 - 0.69 | Fail | Requires revision before export |
| < 0.50 | Hard fail | Fundamental restructuring needed |

## Issue Classification

When validation finds problems, classify them for the `validation_summary.issues` array:

| Issue Type | Severity Default | Description |
|-----------|-----------------|-------------|
| `overlap` | warning | Two siblings have ambiguous boundary |
| `gap` | warning | A scenario has no home in the current structure |
| `fan_out` | info (>5: warning, >7: error) | Branch has too many children |
| `depth` | info (>4: warning, >5: error) | Tree is deeper than recommended |
| `atomicity` | warning | A leaf node fails one or more atomicity tests |
| `dependency` | info | Cross-branch dependency that may complicate orchestration |
| `schema` | error | Structural violation of the output schema |

Severity may be upgraded based on context. An overlap at L1 is more severe than at L3.
