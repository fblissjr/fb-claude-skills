# trigger: javascript
## JavaScript/TypeScript conventions (auto-detected)
- Package manager is bun: `bun add`, `bun run <script>`, `bunx`. Never npm/yarn/pnpm — those and `bun.lock` edits are hook-blocked, but reaching for `bun run` is on you.
- Pin on the way in: apps exact (`bun add express@5.1.0`), libraries caret (`bun add express@^5.1.0`). Unsure → exact.
- Depth, plus npm→bun migration: `/dev-conventions:bun-tooling`.
