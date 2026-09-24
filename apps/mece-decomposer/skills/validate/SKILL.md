---
name: validate
description: Validate a MECE decomposition for compliance, structural integrity, and SDK readiness. Use when user says "validate decomposition", "check MECE compliance", "run validation", or wants to verify a decomposition tree passes quality gates.
---

# /validate

Check a MECE decomposition for structural integrity, MECE quality and export readiness.

Usage: `/validate <decomposition JSON or file path>`, or `/validate` after `/decompose` or `/interview` to check the last output.

<layers>
1. **Structural, deterministic.** Run the validator first and report its findings as it states them:

   ```bash
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/mece-decomposer/scripts/validate_mece.py <decomposition.json>
   ```

   It checks schema compliance and enums, hierarchical ID consistency, dependency references, fan-out and parallel limits, atom and branch completeness, tool and prompt size per atom, and depth.

2. **MECE quality, judgment.** Score ME and CE at each level with the tests, weights and depth-adaptive rigor in `references/validation_heuristics.md` of the mece-decomposer skill. Every score cites the pairs, examples or scenarios it was computed from, so the user can dispute a specific one.
</layers>

<report>
```
## Validation Report

**Status:** PASS / CONDITIONAL PASS / FAIL
**ME Score:** 0.XX -- [interpretation]
**CE Score:** 0.XX -- [interpretation]
**Overall:** 0.XX -- [interpretation]

### Issues
| Severity | Location | Type | Description |
|----------|----------|------|-------------|
| error    | node:1.2 | gap  | Missing ... |
| warning  | node:2   | depth| Tree depth ... |

### Recommendations
- [Fix for each error]
- [Improvement for each warning]
```

Status follows the gates: overall >= 0.85 pass, 0.70 to 0.84 conditional pass (exportable with the issues documented), below 0.70 fail. When the `mece-validate` MCP tool is available, also render the report through it.
</report>

A decomposition at or above 0.70 goes to `/export`; below it, fix the issues and validate again.
