# Analysis Template

Use this structure when generating analysis documentation for plugins.

---

## ANALYSIS.md Structure

```markdown
# [Plugin Name]: Technical Analysis

## Executive Summary

**[plugin-name]** is a Claude Code plugin that [brief description].

**Overall Assessment: [Strong/Good/Needs Work]**

| Category | Rating | Notes |
|----------|--------|-------|
| Concept/Design | [rating] | [notes] |
| Code Quality | [rating] | [notes] |
| Documentation | [rating] | [notes] |
| User Experience | [rating] | [notes] |
| Integration Potential | [rating] | [notes] |

---

## Architecture Overview

[Directory tree showing plugin structure]

---

## Component Inventory

### Commands ([count])

| Command | Purpose | File |
|---------|---------|------|
| /[name] | [description] | commands/[name].md |

### Hooks ([count])

| Event | Purpose | Script |
|-------|---------|--------|
| [event] | [description] | hooks/[script] |

### Traits ([count])

| Trait | Purpose | File |
|-------|---------|------|
| [name] | [description] | traits/[name].md |

### Skills ([count])

| Skill | Purpose | File |
|-------|---------|------|
| [name] | [description] | skills/[name]/SKILL.md |

---

## Data Flow

[Describe how data flows through the plugin]

---

## Key Findings

### Strengths
1. [strength 1]
2. [strength 2]

### Weaknesses
1. [weakness 1]
2. [weakness 2]

---

## Related Files

- [RECOMMENDATIONS.md](./RECOMMENDATIONS.md)
- [INTEGRATION_WORKFLOWS.md](./INTEGRATION_WORKFLOWS.md)
- [SKILL_REVIEW.md](./SKILL_REVIEW.md)
```

---

## RECOMMENDATIONS.md Structure

```markdown
# Recommendations for [Plugin Name]

Prioritized improvements identified through analysis.

---

## Priority 1: [Issue Title] (Critical)

### Current Issue
[Description of the problem]

### Impact
[Why this matters]

### Recommended Solution
[How to fix it]

### Implementation Status
- [ ] Not started
- [ ] In progress
- [x] Completed

---

## Priority 2: [Issue Title] (High)

[Same structure]

---

## Implementation Checklist

- [ ] Priority 1: [description]
- [ ] Priority 2: [description]
- [ ] Priority 3: [description]
```

---

## INTEGRATION_WORKFLOWS.md Structure

```markdown
# Integration Workflows

How [plugin-name] integrates with other Claude Code plugins.

---

## Overview

[Brief description of integration potential]

---

## With [Other Plugin Name]

### Workflow: [Workflow Name]

[Step-by-step workflow combining both plugins]

### Enhanced Behavior

[What the combination achieves that neither does alone]

---

## Cross-Plugin Composition Matrix

| Task | Primary Plugin | This Plugin | Enhanced Behavior |
|------|----------------|-------------|-------------------|
| [task] | [plugin] | [feature] | [result] |

---

## Best Practices

[Guidelines for effective integration]
```

---

## SKILL_REVIEW.md Structure

```markdown
# Skill Review: [Plugin Name]

Independent quality assessment.

---

## Skill Metadata

| Property | Value |
|----------|-------|
| Name | [name] |
| Version | [version] |
| Author | [author] |
| License | [license] |

---

## Quality Assessment

### Command Quality

| Aspect | Rating | Notes |
|--------|--------|-------|
| Consistency | [1-10] | [notes] |
| Coverage | [1-10] | [notes] |
| Documentation | [1-10] | [notes] |

### Hook Implementation

| Aspect | Rating | Notes |
|--------|--------|-------|
| Opt-out available | [Yes/No] | [notes] |
| Error handling | [1-10] | [notes] |
| Efficiency | [1-10] | [notes] |

### Overall

| Category | Rating |
|----------|--------|
| Design | [1-10] |
| Implementation | [1-10] |
| Documentation | [1-10] |
| User Experience | [1-10] |
| Maintainability | [1-10] |
| **Overall** | **[average]/10** |

---

## Actionable Recommendations

### Immediate
- [ ] [action]

### Short-term
- [ ] [action]

### Long-term
- [ ] [action]
```
