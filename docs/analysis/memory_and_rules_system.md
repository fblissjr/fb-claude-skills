last updated: 2026-02-19

# Memory and Rules System

Analysis of Claude Code's memory and rules mechanisms: the six-level hierarchy, auto memory,
CLAUDE.md imports, `.claude/rules/` path-scoped modular rules, and organization-level management.

Source: `docs/claude-docs/claude_docs_memory.md/code_claude_com_docs_en_memory_text.md`

---

## 1. Memory Type Hierarchy

Claude Code provides six distinct memory locations in a hierarchical priority structure.
More specific instructions take precedence over broader ones.

| Level | Location | Purpose | Use Case | Shared With |
|-------|----------|---------|----------|-------------|
| **Managed policy** | macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`; Linux: `/etc/claude-code/CLAUDE.md`; Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | Organization-wide instructions managed by IT/DevOps | Company coding standards, security policies, compliance requirements | All users in the organization |
| **Project memory** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team-shared instructions for the project | Project architecture, coding standards, common workflows | Team via source control |
| **Project rules** | `./.claude/rules/*.md` | Modular, topic-specific project instructions | Language guidelines, testing conventions, API standards | Team via source control |
| **User memory** | `~/.claude/CLAUDE.md` | Personal preferences for all projects | Code style preferences, personal tooling shortcuts | Just you, across all projects |
| **Project memory (local)** | `./CLAUDE.local.md` | Personal project-specific preferences | Sandbox URLs, preferred test data | Just you, current project only |
| **Auto memory** | `~/.claude/projects/<project>/memory/` | Claude's automatic notes and learnings | Project patterns, debugging insights, architecture notes | Just you, per project |

Key behaviors:
- CLAUDE.md files above the working directory load in full at session start.
- CLAUDE.md files in child directories load on demand when Claude reads files there.
- `CLAUDE.local.md` is automatically added to `.gitignore` -- safe for private preferences.
- Auto memory loads only the first 200 lines of `MEMORY.md` into the system prompt.

---

## 2. Auto Memory

Auto memory is Claude's self-maintained knowledge base. Unlike CLAUDE.md files (which you write
for Claude), auto memory contains notes Claude writes for itself during sessions.

### Storage Location

Each project gets a dedicated directory at `~/.claude/projects/<project>/memory/`. The project
path is derived from the git repository root, so all subdirectories within the same repo share
one auto memory directory. Git worktrees get separate directories. Outside a git repo, the
working directory path is used.

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Concise index, loaded into every session (first 200 lines)
├── debugging.md       # Detailed notes on debugging patterns (loaded on demand)
├── api-conventions.md # API design decisions (loaded on demand)
└── ...                # Any other topic files Claude creates
```

### How It Works

- `MEMORY.md` is the index. The first 200 lines are loaded into Claude's system prompt at
  session start. Content beyond 200 lines is not loaded automatically.
- Topic files (`debugging.md`, `patterns.md`, etc.) are not loaded at startup. Claude reads
  them on demand using its standard file tools.
- Claude reads and writes memory files during sessions -- updates happen in real time.
- The system instructs Claude to keep `MEMORY.md` concise by moving detailed notes to topic files.

### What Claude Saves

- Project patterns: build commands, test conventions, code style
- Debugging insights: solutions to tricky problems, common error causes
- Architecture notes: key files, module relationships, important abstractions
- User preferences: communication style, workflow habits, tool choices

### Control

```bash
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1  # Force off
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=0  # Force on
```

Auto memory is gradually rolling out. When neither variable is set, the gradual rollout
applies. The double-negative logic: `DISABLE=0` means "don't disable it", forcing it on.

Use `/memory` during a session to open the file selector, which includes the auto memory
entrypoint alongside CLAUDE.md files.

---

## 3. CLAUDE.md Import Syntax

CLAUDE.md files can import additional files using `@path/to/import` syntax:

```
See @README for project overview and @package.json for available npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

Rules:
- Both relative and absolute paths are allowed.
- Relative paths resolve relative to the file containing the import, not the cwd.
- Imported files can recursively import additional files, max depth of 5 hops.
- Imports are NOT evaluated inside markdown code spans or code blocks (collision avoidance).
- The first time imports are encountered in a project, an approval dialog appears listing the
  specific files. Approve to load; decline to skip. One-time decision: once declined, the
  dialog does not resurface.

Cross-worktree pattern for personal preferences:
```markdown
# Individual Preferences
- @~/.claude/my-project-instructions.md
```

This avoids `CLAUDE.local.md`'s limitation of existing in only one worktree.

Use `/memory` to see which memory files are currently loaded.

---

## 4. Modular Rules with `.claude/rules/`

For larger projects, instructions can be organized into multiple files using the
`.claude/rules/` directory. All `.md` files in this directory are automatically loaded
as project memory, with the same priority as `.claude/CLAUDE.md`.

### Basic Structure

```
your-project/
├── .claude/
│   ├── CLAUDE.md           # Main project instructions
│   └── rules/
│       ├── code-style.md   # Code style guidelines
│       ├── testing.md      # Testing conventions
│       └── security.md     # Security requirements
```

### Path-Specific Rules

Rules can be scoped to specific files using YAML frontmatter with the `paths` field:

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```

Rules without a `paths` field are loaded unconditionally and apply to all files.

### Glob Patterns

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under `src/` directory |
| `*.md` | Markdown files in project root |
| `src/components/*.tsx` | React components in a specific directory |

Multiple patterns are supported:

```yaml
paths:
  - "src/**/*.ts"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
```

Brace expansion works:

```yaml
paths:
  - "src/**/*.{ts,tsx}"
  - "{src,lib}/**/*.ts"
```

### Subdirectory Organization

Rules can be organized into subdirectories -- all `.md` files are discovered recursively:

```
.claude/rules/
├── frontend/
│   ├── react.md
│   └── styles.md
├── backend/
│   ├── api.md
│   └── database.md
└── general.md
```

### Symlinks

The `.claude/rules/` directory supports symlinks, allowing shared rules across multiple projects:

```bash
# Symlink a shared rules directory
ln -s ~/shared-claude-rules .claude/rules/shared

# Symlink individual rule files
ln -s ~/company-standards/security.md .claude/rules/security.md
```

Circular symlinks are detected and handled gracefully.

### User-Level Rules

Personal rules that apply to all projects live at `~/.claude/rules/`:

```
~/.claude/rules/
├── preferences.md    # Personal coding preferences
└── workflows.md      # Preferred workflows
```

User-level rules are loaded before project rules, giving project rules higher priority.

### Best Practices

- Keep rules focused: one topic per file (e.g., `testing.md`, `api-design.md`).
- Use descriptive filenames.
- Use conditional rules (`paths` frontmatter) sparingly -- only when rules truly apply to
  specific file types.
- Organize with subdirectories: group related rules.

---

## 5. Memory Lookup Mechanism

Claude reads memories recursively starting from the current working directory:

1. Claude recurses up from cwd to (but not including) root `/`.
2. Any CLAUDE.md or CLAUDE.local.md files found are loaded in full.
3. CLAUDE.md files in child directories (subtrees) are discovered but NOT loaded at launch.
   They are loaded on demand when Claude reads files in those subtrees.

This is especially useful in monorepos: running Claude from `foo/bar/` loads both
`foo/CLAUDE.md` and `foo/bar/CLAUDE.md`.

### Loading from Additional Directories

```bash
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../shared-config
```

By default, `--add-dir` gives Claude file access to additional directories but does NOT load
their CLAUDE.md files. The environment variable opts in to also loading memory files
(CLAUDE.md, `.claude/CLAUDE.md`, and `.claude/rules/*.md`) from those directories.

---

## 6. Organization-Level Management

Organizations can deploy centrally managed CLAUDE.md files to all users:

1. Create the managed memory file at the managed policy location for the target OS.
2. Deploy via MDM, Group Policy, Ansible, or equivalent configuration management.

This is the mechanism for org-wide enforcement of coding standards, security policies,
and compliance requirements without requiring individual developers to configure anything.

---

## 7. How This Repo Uses Memory

This repository actively uses two levels of the memory hierarchy:

### Auto Memory

Claude maintains `~/.claude/projects/.../memory/MEMORY.md` with:
- Architecture notes (three-repo system, design principles)
- Dimensional model summary (DuckDB schema, key patterns)
- Key file paths (store.py, config.yaml, state.json)
- Gotchas (SCD Type 2 constraints, DuckDB limitations, timezone handling)
- Conventions (uv, orjson, skills-ref validation, semver)

The MEMORY.md in this project's auto memory directory is loaded into every session,
eliminating the need to re-explain project architecture each time.

### Project Memory (CLAUDE.md)

The root `CLAUDE.md` provides:
- Full repo structure and component layout
- Installation instructions for all plugins
- Plugin development conventions
- MCP development references
- Key patterns (CDC, progressive disclosure, selection under constraint)
- Dimensional model documentation (including SCD Type 2 rules)
- Configuration and state file references
- Documentation index

### CLAUDE.local.md

Not currently in use. Could be used by individual contributors for personal sandbox URLs,
local test data paths, or preferred test filters that should not be shared.

---

## 8. Interaction with Other Components

### Memory vs Skills

| Dimension | Memory (CLAUDE.md / rules/) | Skills (SKILL.md) |
|-----------|----------------------------|-------------------|
| Loading | Unconditional -- always loaded at session start | Probabilistic -- loaded when description matches user intent |
| Scope | Project, team, or org-wide standards | Domain-specific expertise |
| Who writes | Humans (or Claude for auto memory) | Skill authors |
| Path-scoping | Yes (`.claude/rules/` with `paths:`) | No |
| Org-level | Yes (managed policy location) | No |
| Plugin system | Independent of plugins | Core plugin component |
| Auto-update | Auto memory updates itself | Updated via CDC pipeline |

Key distinction: memory loads unconditionally and governs Claude's baseline behavior.
Skills load contextually and provide specialized domain knowledge. They are complementary,
not competing.

### Memory vs Hooks

| Dimension | Memory | Hooks |
|-----------|--------|-------|
| Execution | Loaded into context (guidance) | Executes shell commands (enforcement) |
| Guarantee | Probabilistic (Claude reads, may not follow) | Deterministic (always fires) |
| Path-scoping | Yes, via `rules/` frontmatter | Yes, via matcher patterns |

Use memory to teach patterns; use hooks to enforce invariants.

### Memory vs Plugins

Memory (CLAUDE.md and rules/) operates independently of the plugin system. Memory files load
based on filesystem location and the session's working directory. Plugin-provided skills and
agents load via the plugin registry. A plugin can include a CLAUDE.md (via `@import` from its
own SKILL.md), but memory files are not part of the plugin manifest and are not installed with
`/plugin install`.

---

## 9. Gaps and Recommendations

### Gap: `.claude/rules/` Underutilized in This Repo

This repo does not currently use `.claude/rules/`. The CLAUDE.md is comprehensive but
monolithic. Candidates for extraction into focused rule files:
- `rules/skills.md` -- skill authoring conventions (trigger phrases, 500-line limit, etc.)
- `rules/python.md` -- uv, orjson, test patterns
- `rules/plugins.md` -- plugin manifest requirements, checklist
- `rules/dimensional-modeling.md` -- DuckDB SCD Type 2 constraints (currently in CLAUDE.md)

### Gap: No CLAUDE.local.md Usage Documentation

Contributors do not know they can use `CLAUDE.local.md` for private project preferences.
Could be documented in the root README or CLAUDE.md.

### Gap: Import Syntax Not Used

The `@import` syntax in CLAUDE.md is not currently used. Large CLAUDE.md sections
(e.g., the full documentation index table) could be extracted to imported files.

### Recommendation: Add Memory Source to CDC Monitoring

The memory doc URL (`code.claude.com/docs/en/memory`) is not in `skill-maintainer/config.yaml`.
Adding it would catch future changes to auto memory behavior, the rules system, or import syntax.
