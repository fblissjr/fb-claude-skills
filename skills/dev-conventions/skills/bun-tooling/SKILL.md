---
name: bun-tooling
description: >-
  Detailed bun conversion reference for JavaScript and TypeScript projects. Core conventions auto-loaded
  via SessionStart hook; invoke /dev-conventions:bun-tooling for full conversion tables and lock file
  migration steps.
metadata:
  author: Fred Bliss
  version: 0.2.0
  last_verified: 2026-03-13
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

## Lock files

Use `bun.lockb` instead of `package-lock.json` or `yarn.lock`. If migrating an existing project, delete the old lock file and run `bun install` to generate `bun.lockb`.

## Init

Use `bun init` instead of `npm init` or `yarn init`.
