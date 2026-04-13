---
name: bun-tooling
description: >-
  Convert JavaScript and TypeScript projects to use bun instead of npm/yarn/pnpm. Use when user asks to
  "migrate from npm to bun", "convert to bun", "switch package managers", "replace npm", or "use bun
  instead". Includes conversion tables and lock file migration. Core conventions auto-loaded via
  SessionStart hook; invoke /dev-conventions:bun-tooling for full reference.
metadata:
  author: Fred Bliss
  version: 0.5.0
  last_verified: 2026-04-13
---

# Bun Tooling Conventions

Always use `bun` for JavaScript and TypeScript package management and script execution. Never use `npm`, `yarn`, `pnpm`, or `npx`.

| Instead of | Use |
|------------|-----|
| `npm install` | `bun install` |
| `npm install X` | `bun add X` |
| `npm install -D X` | `bun add -d X` |
| `npm run build` | `bun run build` |
| `npx create-react-app` | `bunx create-react-app` |
| `yarn add X` | `bun add X` |
| `pnpm install` | `bun install` |

## Version pinning

| Project type | Strategy | Example |
|-------------|----------|---------|
| Application (deployed, standalone) | Exact pin | `bun add express@5.1.0` |
| Library (published npm package) | Caret range | `bun add express@^5.1.0` |
| Dev dependency | Caret range | `bun add -d typescript@^5.9.3` |

When in doubt, pin exact. In CI, verify with `bun install --frozen-lockfile`.

## Lock files

Use `bun.lockb` instead of `package-lock.json` or `yarn.lock`. If migrating an existing project, delete the old lock file and run `bun install` to generate `bun.lockb`.

## Init

Use `bun init` instead of `npm init` or `yarn init`.
