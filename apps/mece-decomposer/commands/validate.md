---
description: Validate a MECE decomposition for compliance, structural integrity, and SDK readiness
argument-hint: "<decomposition JSON or file path>"
---

# /validate

Check a MECE decomposition for structural integrity, MECE compliance, and Agent SDK readiness.

## Usage

```
/validate <decomposition JSON or file path>
```

Examples:
- `/validate` then paste decomposition JSON
- `/validate output.json`
- `/validate` after a `/decompose` or `/interview` session (validates the last output)

## Validation Layers

### 1. Structural Validation (deterministic)

```bash
uv run mece-decomposer/skills/mece-decomposer/scripts/validate_mece.py <decomposition.json>
```

Checks:
- Schema compliance (required fields, types, valid enums)
- Hierarchical ID consistency (parent-child prefix pattern)
- Cross-branch dependency validity (IDs exist, no self-references)
- Fan-out limits (2-7 children per branch, max 7 parallel)
- Atom completeness (all atoms have `atom_spec`, all branches have `orchestration`)
- Prompt/tool limits (flag atoms with >5 tools or >500 word prompts)
- Depth limits (warn at >5 levels)

### 2. MECE Quality Assessment (judgment-based)

Using the scoring rubrics from the **mece-decomposer** skill:
- **ME testing**: definition-based, example-based, boundary-case at each level
- **CE testing**: scenario enumeration, negation test, stakeholder test
- **Depth-adaptive rigor**: L1 full, L2 pairwise, L3 spot-check, L4+ trust
- Weighted score aggregation

## Output

```
## Validation Report

**Status:** PASS / FAIL
**ME Score:** 0.XX — [interpretation]
**CE Score:** 0.XX — [interpretation]
**Overall:** 0.XX — [interpretation]

### Issues
| Severity | Location | Type | Description |
|----------|----------|------|-------------|
| error    | node:1.2 | gap  | Missing ... |
| warning  | node:2   | depth| Tree depth ... |

### Recommendations
- [Fix for each error]
- [Improvement for each warning]
```

### Interactive Report (when MCP server connected)

The `mece-validate` MCP tool renders a visual report with clickable issue locations that navigate to the problem node in the tree.

## Score Interpretation

| Range | ME | CE |
|-------|----|----|
| 0.85-1.0 | Strong: no overlap | Strong: no gaps |
| 0.70-0.84 | Acceptable: minor boundary issues | Acceptable: minor gaps documented |
| 0.50-0.69 | Weak: redefine boundaries | Weak: add missing components |
| < 0.50 | Failed: re-cut this level | Failed: restructure |

Quality gate: >= 0.70 for export, >= 0.85 for confidence.

## Next Steps

- Score too low? "Let me fix the issues" -> re-run `/validate`
- Ready? "Export as Agent SDK code" -> `/export`
