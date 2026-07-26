# trigger: javascript
## JavaScript/TypeScript conventions (auto-detected)
- Package manager is bun: `bun add`, `bun run <script>`, `bunx`. (npm/yarn/pnpm and hand-edits to `bun.lock` are hook-blocked in bun projects, so this line is only a reminder to reach for `bun run` rather than a bare node invocation.)
- Pinning: applications pin exact (`bun add express@5.1.0`), libraries use caret (`bun add express@^5.1.0`). When unsure, pin exact.
- Full reference: /dev-conventions:bun-tooling.
