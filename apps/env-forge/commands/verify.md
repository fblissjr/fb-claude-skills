---
description: "Run verification functions against current DB state for a task (Phase 2)"
argument-hint: "<environment name> <task number>"
---

# /env-forge:verify

> Phase 2 -- not yet implemented. This command will run verification functions against the current database state for a specific task.

## Planned Behavior

```
/env-forge:verify volunteer_match 3
/env-forge:verify e_commerce_33 0
/env-forge:verify volunteer_match --all
```

1. Load `verifiers.py` from the environment directory
2. Snapshot current.db as the "final" state
3. Run the specified verification function (or all)
4. Report pass/fail with diagnostics

## Current Workaround

Run verifiers manually:

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "verifiers",
    ".env-forge/environments/<name>/verifiers.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

result = mod.verify_task_0("db/initial.db", "db/current.db")
print(result)
```

Or from the command line:

```bash
cd .env-forge/environments/<name>
uv run python -c "
from verifiers import verify_task_0
print(verify_task_0('db/initial.db', 'db/current.db'))
"
```

## Phase 2 Additions

- Run all verifiers with summary report
- Pretty-print diagnostics with pass/fail indicators
- Reset-and-verify: reset DB, run task via agent, verify automatically
- Batch verification across multiple tasks
- Export verification results as JSON for analysis
