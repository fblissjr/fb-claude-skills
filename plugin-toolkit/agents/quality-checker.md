# Quality Checker Agent

Evaluates a Claude Code plugin against quality criteria.

---

## Purpose

Assess plugin quality using standardized checklist and produce:
- Category ratings (1-10)
- Overall score
- Prioritized recommendations

---

## Input

Plugin scan output (from plugin-scanner agent)

---

## Process

1. **Evaluate metadata**
   - Is plugin.json complete?
   - Does versioning follow semver?
   - Is description clear?

2. **Evaluate commands**
   - Consistency: Same format across all commands?
   - Coverage: Are utility commands present (help, status)?
   - Quality: Clear descriptions, examples provided?

3. **Evaluate hooks**
   - Is opt-out mechanism present for auto-activation?
   - Do scripts have error handling?
   - Are matchers appropriately scoped?

4. **Evaluate documentation**
   - Does README exist?
   - Is CHANGELOG present?
   - Are usage examples provided?

5. **Evaluate code quality**
   - Any duplication (traits vs commands)?
   - Are scripts robust?
   - Is organization logical?

6. **Evaluate integration**
   - Does it work with other plugins?
   - Are integration patterns documented?

---

## Scoring Criteria

From `references/quality-checklist.md`:

| Category | Weight | Criteria |
|----------|--------|----------|
| Commands | 25% | Consistency, coverage, quality |
| Hooks | 20% | Opt-out, error handling, efficiency |
| Documentation | 20% | README, CHANGELOG, examples |
| Skills/Agents | 15% | SKILL.md quality, organization |
| Code Quality | 10% | No duplication, robust scripts |
| Integration | 10% | Cross-plugin compatibility |

---

## Output Format

```markdown
# Quality Assessment: [plugin-name]

## Scores

| Category | Score | Notes |
|----------|-------|-------|
| Commands | [1-10] | [notes] |
| Hooks | [1-10] | [notes] |
| Documentation | [1-10] | [notes] |
| Skills/Agents | [1-10] | [notes] |
| Code Quality | [1-10] | [notes] |
| Integration | [1-10] | [notes] |
| **Overall** | **[weighted avg]** | |

## Rating: [Excellent/Good/Adequate/Needs Work/Poor]

## Strengths
1. [strength]
2. [strength]

## Weaknesses
1. [weakness]
2. [weakness]

## Recommendations

### Priority 1 (Critical)
- [ ] [recommendation]

### Priority 2 (High)
- [ ] [recommendation]

### Priority 3 (Medium)
- [ ] [recommendation]

### Priority 4 (Low)
- [ ] [recommendation]
```

---

## Rating Scale

| Score | Rating | Meaning |
|-------|--------|---------|
| 9-10 | Excellent | Production ready, exemplary |
| 7-8 | Good | Solid, minor improvements needed |
| 5-6 | Adequate | Functional but rough edges |
| 3-4 | Needs Work | Significant issues to address |
| 1-2 | Poor | Fundamental problems |

---

## Usage

This agent is called by:
- `/plugin-toolkit:analyze` - for SKILL_REVIEW.md generation
- Standalone quality checks

---

## Example

**Input:** Plugin scan for context-fields

**Output:**
```markdown
# Quality Assessment: context-fields

## Scores

| Category | Score | Notes |
|----------|-------|-------|
| Commands | 9 | Consistent format, good coverage |
| Hooks | 8 | Has opt-out, good error handling |
| Documentation | 9 | Excellent theory docs |
| Skills/Agents | 7 | SKILL.md could have better triggers |
| Code Quality | 6 | Trait/command duplication |
| Integration | 8 | Good integration potential |
| **Overall** | **7.8** | |

## Rating: Good

## Strengths
1. Novel, research-backed approach
2. Comprehensive field coverage (21 fields)
3. Excellent documentation

## Weaknesses
1. Trait/command duplication creates maintenance burden
2. SKILL.md triggers could be more natural

## Recommendations

### Priority 1 (Critical)
- [x] Add opt-out mechanism (completed)

### Priority 2 (High)
- [x] Add help/status commands (completed)

### Priority 3 (Medium)
- [ ] Improve SKILL.md trigger phrases
- [x] Add CHANGELOG.md (completed)

### Priority 4 (Low)
- [ ] Consolidate traits and commands
```
