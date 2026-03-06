---
name: tdd-workflow
description: >-
  Red/green TDD workflow: write a failing test first, then implement, then refactor. Use when writing tests,
  implementing features test-first, or when user says "TDD", "test first", "red green refactor",
  "write a test", "test-driven". Invoke with /dev-conventions:tdd-workflow.
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-03-03
---

# Test-Driven Development Workflow

Follow red/green/refactor for every change.

## The cycle

1. **Red**: Write a test that describes the desired behavior. Run it. Watch it fail. If it passes, the test is wrong or the feature already exists.
2. **Green**: Write the minimum code to make the test pass. No more. Run the test. Watch it pass.
3. **Refactor**: Clean up both the implementation and the test. Run the test again. Still green.

## Rules

- **One behavior per test.** A test that checks two things is two tests.
- **Test names describe behavior, not implementation.** `test_expired_token_returns_401` not `test_check_token`.
- **Group related tests.** Put tests for the same module/feature in the same test file.
- **Never write implementation before the test.** The test defines the contract.
- **Never skip the red step.** If you can't make the test fail first, you don't understand the requirement.

## Scope

When this skill is explicitly invoked, always follow TDD. When auto-triggered, apply TDD to any change that adds or modifies testable behavior. Skip TDD only for pure configuration changes with no behavioral component.
