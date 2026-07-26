# trigger: any
## TDD workflow (auto-loaded)
- ALWAYS write a failing test first, then implement, then refactor. No exceptions for behavioral changes, and never skip the red step: if you cannot make it fail first, you do not yet understand the requirement.
- Every new test records its claim — one line on what breaks if it is deleted. A test whose claim nobody can recover becomes unauditable scar tissue.
- Auditing an existing suite for claims, drift, and dead weight: `/postmortem:test-audit`.
