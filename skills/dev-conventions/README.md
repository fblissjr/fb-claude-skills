last updated: 2026-08-03

# dev-conventions

Development conventions with automatic project detection. A SessionStart hook detects Python/JS project markers and injects the relevant conventions into Claude's context. Skills provide detailed reference tables on demand.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install dev-conventions@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/skills/dev-conventions
```

## hooks

| Hook | Event | What it does |
|------|-------|--------------|
| `session-start.sh` | SessionStart | Detects Python/JS markers in cwd (root + 2 levels deep for monorepos), injects matching directives as additionalContext. |

### detection markers

| Marker | Directive injected |
|--------|--------------------|
| `pyproject.toml`, `*.py` (root or 2 levels deep) | `python.md` -- uv, pinning, lock file policy |
| `package.json`, `tsconfig.json`, `bun.lock` (root or 2 levels deep) | `javascript.md` -- bun, JS/TS conventions |
| Any Python or JS marker | `tdd.md` -- red/green TDD as a directive |
| `internal/` or `internal/log/` directory | `doc-conventions.md` -- session logging, last-updated dates |

### composable directives

All injected content lives in `hooks/directives/` as standalone `.md` files. The hook concatenates whichever directives match and returns them as a single `additionalContext` block.

To add a new directive: drop a `.md` file in `hooks/directives/` and add a detection condition to `hooks/dev-conventions-session-start.sh`.

### ground coverage: blocks silence themselves where local rules exist

Each directive declares its *ground* as a regex on line 2 (`# ground: ...`). Before injecting a block, the hook greps that pattern across the repo's own conventions surfaces -- root `CLAUDE.md`, `.claude/rules/*.md`, and `rules[]` in `.dev-conventions.json`. Covered ground means that block stays silent, per block: a CLAUDE.md that only describes module layout silences nothing; a repo that states its own package-manager rule silences exactly that block. Silencing gates prose only -- the PreToolUse enforcement hook never consults it.

To make the conventions local in the first place, `/dev-conventions:init` scaffolds tailored convention lines into the repo's own files (skipping ground already covered), after which the blocks are silent here automatically -- and the scaffolded text reaches every collaborator's Claude through normal context loading, including people who never installed this plugin.

### per-repo muting

The manual override, for ground the coverage pattern cannot see (a local rule phrased in repo-specific vocabulary). Mute by filename in the tracked `.dev-conventions.json` (`/dev-conventions:configure mute tdd`, or by hand):

```json
{ "directives": { "tdd": false, "doc-conventions": false } }
```

Muting trims the shipped defaults only -- the repo's own `rules[]` still load even with every directive muted. The injected block opens with a standing supersession line: a repo-local rule covering the same ground wins over any shipped block.

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `python-tooling` | `/dev-conventions:python-tooling` | Full uv conversion tables, pinning strategy, lock file workflow (detailed reference) |
| `doc-conventions` | `/dev-conventions:doc-conventions` | Last-updated dates, lowercase filenames, session logs, dependency change tracking, document the "why" |
| `dep-audit` | `/dev-conventions:dep-audit` | Dependency security audit: uv audit, bun audit, transitive analysis, remediation workflow |
| `init` | `/dev-conventions:init` | Scaffold the conventions into the repo's own files, once -- detects the stack, skips covered ground, writes tailored lines; the ambient blocks then silence themselves here |

## how it works

When a session begins, the hook checks `cwd` for project markers (`pyproject.toml`, `package.json`, `*.py`, `bun.lock`). It first checks the project root, then falls back to scanning up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, `dist`, `build`, `.next`, `.output`. For each detected marker, the hook reads the corresponding directive file from `hooks/directives/` and concatenates the results into a single `additionalContext` block -- no manual invocation needed. For full conversion tables or detailed methodology, invoke the skills directly.
