---
name: bun-tooling
description: >-
  Enforce bun over npm/yarn/pnpm for JavaScript and TypeScript projects. Use when working in JS/TS projects,
  when npm install or yarn add appears, when package-lock.json or yarn.lock is referenced. Triggers on
  "npm install", "npm run", "yarn add", "yarn install", "pnpm", "npx", "package-lock.json".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-03-03
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
