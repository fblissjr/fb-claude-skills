# trigger: javascript
## JavaScript/TypeScript conventions (auto-detected)
- Package manager: ALWAYS use bun, NEVER npm/yarn/pnpm/npx (`bun add`, `bun run`, `bunx`).
- Pinning: applications pin exact (`bun add express@5.1.0`), libraries use caret (`bun add express@^5.1.0`). When unsure, pin exact.
- Lock file: `bun.lock` (text format, bun >= 1.2); never hand-edit, update via `bun install`.
- Full reference: /dev-conventions:bun-tooling.
