# trigger: any
## TDD workflow (auto-loaded)
- ALWAYS write a failing test first, then implement, then refactor. No exceptions for behavioral changes, and never skip the red step: if you cannot make it fail first, you do not yet understand the requirement.
- Every new test's claim — what breaks if it is deleted — must be recoverable. A one-line comment per test is the default form; a file-level convention (header claim plus per-case rationale) that pins each case also satisfies this. A test whose claim nobody can recover becomes unauditable scar tissue.
- Auditing an existing suite for claims, drift, and dead weight: `/postmortem:test-audit`.
