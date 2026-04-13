# trigger: javascript
## JavaScript/TypeScript conventions (auto-detected)
- Package manager: ALWAYS use bun. NEVER use npm, yarn, pnpm, or npx.
  - Install: bun install / bun add <pkg>
  - Version pinning: applications pin exact (`bun add express@5.1.0`), libraries use caret ranges (`bun add express@^5.1.0`). When unsure, pin exact.
  - Dev deps: bun add -d <pkg>
  - Run scripts: bun run <script>
  - Execute: bunx <tool> (not npx)
  - Init: bun init
  - Lock file: bun.lockb (not package-lock.json or yarn.lock)
