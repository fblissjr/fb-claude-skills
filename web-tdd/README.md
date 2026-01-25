# web-tdd

A Claude skill for test-driven development of web applications.

## Installation

For Claude Code:
```bash
ln -s /path/to/web-tdd ~/.claude/plugins/web-tdd
```

For Claude.ai skills:
Copy SKILL.md to your skills directory.

## What This Replaces

This is a simplified, unified version that replaces:
- `vibium-tdd` (too many agents, missing spec.md pattern)
- `web-app-tdd` (Playwright-only, no Python backend support)

## Key Differences from Previous Skills

| Feature | Old Skills | web-tdd |
|---------|-----------|---------|
| Agents | 4 agents (coverage-analyzer, setup-helper, test-generator, test-validator) | None - single SKILL.md |
| Spec tracking | None | spec.md with TODOs |
| Push control | Implicit "push if remote configured" | Explicit "push manually, always" |
| Gitignore | Not mentioned | Set up upfront |
| Python backend | Separate uv-tdd skill | Integrated (pytest + httpx) |
| E2E choice | Vibium OR Playwright (separate skills) | Both documented, you choose |

## Philosophy

Borrowed from `uv-tdd`:
1. Single source of truth (SKILL.md)
2. spec.md as living documentation
3. TDD cycle: test → fail → implement → pass → document → commit
4. You control all remote operations (no auto-push)

## Usage

Trigger phrases:
- "Help me add tests to my React app"
- "Set up TDD for my Vite project"
- "I need to test this feature"
- "Create tests for the login flow"

The skill covers:
- React + Node (Vitest everywhere)
- React + Python (Vitest frontend, pytest backend)
- E2E with Playwright or Vibium
