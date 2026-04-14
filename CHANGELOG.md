# changelog

## 0.22.6

### fixed
- **mece-decomposer**: bump to v0.4.1 so marketplace update refreshes stale hooks.json cache (array->object fix from v0.22.4 was never picked up)
- **dimensional-modeling**: bump to v0.3.1 (same stale cache issue)
- **env-forge**: bump to v0.3.1 (same stale cache issue)
- **tui-design**: bump to v0.3.1 (same stale cache issue)

## 0.22.5

### added
- **dev-conventions**: new `dep-audit` skill -- dependency security auditing via `uv audit` (Python) and `bun audit` (JS/TS), transitive analysis, remediation workflow, CI integration
- **dev-conventions**: version pinning conventions in python.md and javascript.md directives -- applications pin exact, libraries use floors/caret ranges
- **dev-conventions**: dependency change tracking in doc-conventions -- session logs now include a structured table of package changes

### changed
- **dev-conventions**: bumped plugin to v0.5.0
- Global rule (`.claude/rules/general.md`) now includes version pinning guidance for both uv and bun

## 0.22.4

### added
- **tui-design**: SessionStart hook auto-injects Five Principles when Rich/Textual/Questionary/Click imports detected. Directive: `hooks/directives/tui-principles.md`. Bumped to v0.3.0.
- **dimensional-modeling**: SessionStart hook auto-injects Kimball principles when DuckDB imports, .duckdb files, or fact_/dim_ SQL patterns detected. Directive: `hooks/directives/kimball-principles.md`. Bumped to v0.3.0.
- **mece-decomposer**: SessionStart hook auto-injects MECE principles when Agent SDK imports or decomposition files detected. Directive: `hooks/directives/mece-principles.md`. Bumped to v0.4.0.
- **env-forge**: SessionStart hook auto-injects task-first design principles when `.env-forge/` directory or fastapi-mcp usage detected. Directive: `hooks/directives/env-forge-principles.md`. Bumped to v0.3.0.

### changed
- **dev-conventions**: refactored SessionStart hook to composable directive files (`hooks/directives/*.md`). Each directive declares its trigger signal (`python`, `javascript`, `docs`, `any`) on line 1. Adding a new convention = dropping a file, no shell editing.
- **dev-conventions**: promoted doc-conventions (last-updated dates, lowercase filenames, document-the-why) to auto-loaded directive alongside TDD and session logging
- **dev-conventions**: bumped plugin to v0.4.0

## 0.22.3

### added
- **json-query**: added to marketplace -- installable plugin for jg/jq tool selection and syntax guidance (from schema-bench research)

### changed
- **dev-conventions**: SessionStart hook now detects project markers up to 2 levels deep for monorepo layouts (e.g., `backend/pyproject.toml`, `web/frontend-app/package.json`). Skips `node_modules`, `.venv`, `.git`, etc.

### fixed
- **dev-conventions**: replaced bare `python3` calls in SessionStart hook with `jq` -- eliminates stdlib json usage and bare python3 convention violations

## 0.22.2

### changed
- **dev-conventions**: SessionStart hook now injects TDD as a directive (not a hint) and adds session logging directive when `internal/` directory exists
- **dev-conventions**: bumped plugin to v0.3.0

## 0.22.1

### changed
- **VISION.md**: added `## the architecture` section (trees not workflows, harness coupling, context isolation, use-before-prepare, structured outputs as state, compound feedback loops)
- **VISION.md**: broadened intro paragraph to frame both architecture and retrieval
- **VISION.md**: extended `## what this means for this repo` with 4 new bullets (agent topology, harness-native design, state management, compound feedback)
- **CLAUDE.md**: updated blockquote to reference architectural worldview alongside retrieval
- **CLAUDE.md**: updated "Context as retrieval" subsection to match new VISION.md language
- **README.md**: updated VISION.md blockquote to match new language, dropped overly specific detail
- **docs/analysis/memory_and_rules_system.md**: updated auto memory description to reflect VISION.md architecture section

## 0.22.0

### added
- **skill-dashboard**: Phase B -- drill-down, measure, verify
  - `skill-measure` tool: per-file token breakdown for a single skill (path, chars, tokens, pctOfTotal)
  - `skill-verify` tool: app-only tool that updates `metadata.last_verified` in SKILL.md frontmatter on disk
  - sidebar UI: click any skill row to open file breakdown table with percentage bars and budget status
  - "Mark Verified" button: updates SKILL.md and refreshes quality data
  - two-panel layout (main + sidebar) with grid-based responsive design
  - new components: SkillSidebar, FileBreakdownTable
  - refactored `measureTokens` into `measureTokensDetailed` (returns per-file entries) + thin wrapper
  - `findSkillPath` helper for resolving skill name to SKILL.md path
  - bumped to v1.1.0

## 0.21.0

### changed
- **skill-dashboard**: rebuilt as ext-apps MCP App (TypeScript, React, same pattern as mece-decomposer)
  - replaced Python rawHtml server with interactive ext-apps UI
  - `skill-quality-check` tool: discovers skills/plugins, runs 5 per-skill + 3 per-plugin + 5 repo checks
  - optional `filter` parameter for skill name substring matching
  - all check logic ported to native TypeScript (gray-matter for frontmatter, no Python dependency)
  - components: SummaryBar, SkillTable with token budget bars, PluginTable, RepoChecks with status dots
  - dual transport: stdio + HTTP (port 3002)
  - version sync check: validates plugin.json, marketplace.json, SKILL.md, pyproject.toml alignment
  - removed Python files: server.py, templates/dashboard.html, pyproject.toml
  - removed from uv workspace members (no longer a Python package)
  - bumped to v1.0.0

### added
- **skill-maintainer**: `/skill-maintainer:sync-versions <plugin> <version>` -- bump a plugin's version across all sources (plugin.json, marketplace.json, SKILL.md, pyproject.toml) atomically

### fixed
- **version alignment**: synced plugin.json across 4 plugins that had drifted from marketplace.json
  - dimensional-modeling: 0.1.0 -> 0.2.0
  - tui-design: 0.1.0 -> 0.2.0
  - skill-maintainer: 0.1.0 -> 0.3.0
  - readwise-reader: marketplace 0.1.0 -> 1.0.0 (aligned with plugin.json/SKILL.md)

## 0.20.1

### added
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:quality` (filter by skill name, substring match)
- **skill-maintainer**: `$ARGUMENTS` support for `/skill-maintainer:init-maintenance` (target directory path)
- **skill-maintainer**: cross-reference validation in quality skill (checks `load the \`X\` skill` patterns resolve)
- **skill-maintainer**: reference file date check in quality skill (checks `last updated:` line in references/*.md)

## 0.20.0

### added
- **skill-maintainer**: new installable plugin at `skills/skill-maintainer/`
  - `/skill-maintainer:maintain`: full maintenance pass (upstream, sources, quality, best practices review) -- replaces legacy `.claude/commands/maintain.md`
  - `/skill-maintainer:quality`: quick quality check (spec, tokens, freshness, description quality) -- no CLI install required
  - `/skill-maintainer:init-maintenance`: set up `.skill-maintainer/` config and state in any repo
  - `references/best_practices.md`: machine-parseable checklist bundled with the plugin
  - skills embed maintenance knowledge directly (thresholds, rules, checks) -- falls back to CLI if available but doesn't require it
  - registered in marketplace.json

### changed
- **skill-maintainer** (CLI): README updated to note plugin is the primary interactive interface, CLI is for CI/headless
- CLAUDE.md: updated repo structure, installation list, maintenance table for plugin

### removed
- `.claude/commands/maintain.md`: replaced by `/skill-maintainer:maintain` plugin skill
- `.claude/commands/` directory: empty after command removal

## 0.19.0

### added
- **dev-conventions**: SessionStart hook for automatic project-type detection
  - detects Python/JS markers in cwd, injects uv/orjson/bun/TDD conventions as additionalContext
  - skills reframed as on-demand references (no longer claim background auto-trigger)
  - bumped plugin version to 0.2.0

## 0.18.3

### fixed
- **skill-maintainer**: `measure_tokens()` now counts only `.md` files (was counting `.py`, `.json`, `.sh`, etc. that are executed, not loaded into context)
  - mece-decomposer dropped from 23,283 to 16,647 tokens (scripts/validate_mece.py was 6,636 phantom tokens)

## 0.18.2

### changed
- **mece-decomposer**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `decompose`, `interview`, `validate`, `export` now use Agent Skills frontmatter (proper `skills/<name>/SKILL.md` layout)
  - removed `commands/` directory (legacy format caused "Legacy format" separator in Cowork)
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **mece-decomposer**: bumped plugin version to 0.3.0
- **mece-decomposer**: updated main skill and README references from "commands" to "skills"
- **env-forge**: converted 4 legacy `commands/*.md` files to proper `skills/<name>/SKILL.md` format
  - `browse`, `forge`, `launch`, `verify` now use Agent Skills frontmatter
  - removed `commands/` directory
  - all 4 skills have trigger phrases in description, metadata.author/version/last_verified
- **env-forge**: bumped plugin version to 0.2.0
- **env-forge**: updated main skill and README references from "commands" to "skills"
- CLAUDE.md: updated stale `apps/env-forge/commands/forge.md` path reference

## 0.18.1

### added
- **agent-state**: `domain`, `task_type`, `status` columns on `dim_skill_version` for routing and lifecycle management
- **agent-state**: new workspace package for DuckDB audit and state tracking
  - Kimball star schema: `fact_run`, `fact_run_message`, `fact_watermark`, `dim_run_source`, `dim_skill_version`, `dim_watermark_source`
  - `RunContext` context manager: atomic watermark commits on success, automatic rollback on failure
  - skill version lineage: `dim_skill_version` connects pipeline outputs to agent inputs
  - watermark tracking: replaces `upstream_hashes.json` with queryable history (`v_latest_watermark`)
  - views: `v_run_tree` (recursive hierarchy), `v_flywheel` (producer->skill->consumer), `v_restartable_failures`
  - migration from `changes.jsonl` and `upstream_hashes.json`
  - CLI: `agent-state init|status|runs|tree|watermarks|flywheel|migrate`
  - storage: single global DuckDB at `~/.claude/agent_state.duckdb`

## 0.18.0

### changed
- **repo structure**: reorganized from flat layout to type-based grouping
  - `skills/`: pure markdown skill bundles (tui-design, dimensional-modeling, cogapp-markdown, dev-conventions, mcp-apps, plugin-toolkit)
  - `apps/`: MCP server applications (mece-decomposer, env-forge, skill-dashboard, heylook-monitor, readwise-reader)
  - `tools/`: CLI packages (skill-maintainer)
- **readwise-reader**: migrated from `~/claude/cowork-plugins/readwise-reader` into `apps/readwise-reader/`
  - flattened `plugin/readwise-reader/` contents to top level
  - converted build system from setuptools to hatchling
  - skill-maintainer dep changed from git URL to workspace reference
  - removed non-portable artifacts (certs, models, zip, .venv, scripts/package_plugin.sh)
- workspace member paths updated: `skill-maintainer` -> `tools/skill-maintainer`, `env-forge` -> `apps/env-forge`, etc.
- readwise-reader excluded from default workspace (requires Python 3.13+)
- skill-dashboard `PROJECT_ROOT` fixed for new `apps/` depth
- marketplace.json source paths updated for all plugins
- root `.mcp.json` server path updated
- skill-maintainer git-install subdirectory updated to `tools/skill-maintainer`

### fixed
- **readwise-reader**: added `metadata.last_verified`, `metadata.author`, `metadata.version` to all 3 SKILL.md files
- **readwise-reader**: fixed description quality (added WHAT verb + WHEN trigger) on all 3 skills
- **readwise-reader**: added `repository` field to plugin.json
- stale path references in READMEs and rules from pre-reorg layout (skill-maintainer git-install path, skill-dashboard server.py path, mece-decomposer dev setup path)
- general.md state path corrected to `.skill-maintainer/state/`
- marketplace_distribution_patterns.md section 4.1 updated for current repo layout
- create-mcp-app and migrate-oai-app descriptions fixed (added WHAT verb)
- docs/claude-docs: flattened 2 files from nested .md-named directories, added to index
- docs/README.md: removed empty internals section, added memory and best_practices to claude-docs index
- removed stale web-tdd references from 4 analysis docs (deleted in v0.14.0)
- mcp_ecosystem_audit: updated for current plugin set (added readwise-reader, env-forge, dev-conventions)
- claude_ecosystem_synthesis.md: fixed 9 stale path/config references for v0.17.0/v0.18.0 changes
- claude_ecosystem_synthesis.md: rewrote section 8 for property-driven maintenance (was stale CDC pipeline from v0.12.x), fixed report count 15->16
- skills_guide_analysis.md: config.yaml -> .skill-maintainer/config.json

## 0.17.0

### changed
- **skill-maintainer**: converted from `package = false` scripts to a proper installable Python package
  - new `src/skill_maintainer/` package with CLI entry point `skill-maintain`
  - git-installable: `uv add git+<repo>#subdirectory=skill-maintainer`
  - all commands accept `--dir <path>` to target any skill repo (default: `.`)
  - subcommands: init, validate, quality, freshness, measure, test, upstream, sources, log
  - per-repo config in `.skill-maintainer/config.json` (upstream URLs, tracked repos)
  - per-repo state in `.skill-maintainer/state/` (hashes, changes log)
  - best_practices.md moved to `.skill-maintainer/best_practices.md`
  - version bumped to 0.2.0
- **skill-dashboard**: replaced `sys.path.insert` hack with proper `skill-maintainer` workspace dependency
  - imports now: `from skill_maintainer.tests import ...` and `from skill_maintainer.shared import ...`
  - removed unused `sys` import

## 0.16.0

### changed
- **skill-dashboard**: rewritten to show full run_tests.py dataset (was: 5 columns from file scan; now: skills + plugins + repo hygiene pass/fail)
  - server.py imports test_skills/test_plugins/test_repo_hygiene from run_tests.py (no more duplicated discovery/measurement code)
  - HTML template: skills table with spec, description quality, freshness, budget, body size; plugins table with manifest/marketplace/README checks; repo hygiene section
  - dropped pyyaml dependency (no longer parses frontmatter directly)
  - bumped to v0.3.0
- **skill-dashboard**: moved `.mcp.json` from `skill-dashboard/` to project root so Claude Code auto-discovers the MCP server
- **skill-maintainer**: consolidated `measure_tokens()` and `check_description_quality()` into `shared.py` (was duplicated in run_tests.py and quality_report.py)

## 0.15.1

### added
- **skill-maintainer**: `run_tests.py` -- red/green test suite encoding best_practices.md as pass/fail checks
  - three categories: skills (spec, budget, body size, staleness, description), plugins (manifest, marketplace, README), repo hygiene (gitignore, hooks, state, duplicates, freshness)
  - `--verbose` shows all results; `--category skills|plugins|repo` runs one category
  - no network calls, no file writes, pure read-only
- **skill-maintainer**: `/maintain` slash command for full maintenance passes
  - orchestrates pull_sources.py -> check_upstream.py -> quality_report.py -> best_practices.md review
  - Claude proposes edits to best_practices.md based on detected changes; user approves before any writes
- **skill-maintainer**: `pull_sources.py` script for pulling 10 tracked coderef repos and detecting changes
  - records HEAD SHAs in `upstream_hashes.json["local_repos"]`, captures commit logs for changed repos
  - appends `source_pull` events to `changes.jsonl` audit log
  - CLI flags: `--no-pull`, `--no-save`, `--no-log`
- `VISION.md`: design principles document -- skills as retrieval, precision/recall framework, progressive disclosure, always-loaded context justification
- **skill-maintainer**: `shared.py` -- added `discover_plugins()` function (mirrors `discover_skills()` for plugin directories)

### changed
- `query_log.py`: added `source_pull` event type display
- `.claude/rules/plugins.md`: removed stale references to config.yaml and monitored_sources.md (removed in v0.13.0)
- **skill-maintainer**: `best_practices.md` rewritten as machine-parseable checklist with sections mapped to VISION.md principles
- **skill-maintainer**: `README.md` rewritten with full workflow section (before/after changes, periodic maintenance, individual checks table)

### removed
- PostToolUse hook on Skill tool (was firing on every skill invocation across all sessions; staleness now checked on-demand via `/maintain` or `check_freshness.py`)
- `.claude/hooks/check-skill-freshness.sh`: dead hook script (PostToolUse hook removed)
- `.gitignore`: removed blanket `.claude/` ignore; project-shared files (rules, commands, hooks, settings.json) are now tracked

## 0.15.0

### changed
- **pyproject.toml**: restructured as uv workspace with four members (skill-maintainer, env-forge, skill-dashboard, mece-decomposer)
  - each subfolder declares its own dependencies instead of a monolithic root
  - removed `coderef/` editable paths that broke on clone (local-only symlinks)
  - `skills-ref` now installed from PyPI; `mcp-ui-server` from git (github.com/idosal/mcp-ui)
  - root is a workspace coordinator with dev-only deps (pytest, ruff)
  - setup: `uv sync --all-packages`; existing `uv run` commands unchanged

### added
- **dev-conventions**: new installable plugin extracting global CLAUDE.md into selective skills
  - `python-tooling` (background): enforces uv over pip, orjson over json
  - `bun-tooling` (background): enforces bun over npm/yarn/pnpm
  - `tdd-workflow` (user-invocable): red/green TDD workflow
  - `doc-conventions` (user-invocable): last-updated dates, lowercase filenames, session logs, document the "why"

## 0.14.0

### removed
- **web-tdd**: removed plugin (generic TDD workflow that duplicates Claude's built-in knowledge; stack preferences belong in CLAUDE.md)

### changed
- migrated all JS/TS tooling references from npm/npx to bun/bunx across package.json scripts, SKILL.md files, READMEs, and settings
- replaced package-lock.json with bun.lockb in heylook-monitor and mece-decomposer/mcp-app

## 0.13.0

### changed
- **skill-maintainer**: replaced pipeline-driven model with property-driven maintenance
  - removed: SKILL.md (no longer a skill), DuckDB store (store.py, migrate_state.py), CDC pipeline (docs_monitor.py, source_monitor.py, update_report.py, apply_updates.py), journal system (journal.py), config.yaml, state.json
  - added: pre-commit git hook (validates staged SKILL.md files with skills-ref)
  - added: PostToolUse Claude Code hook (checks last_verified age when any skill is invoked)
  - added: quality_report.py (unified CLI: validation, token budget, last_verified, description quality)
  - added: check_upstream.py (on-demand upstream doc change detection via llms-full.txt hashing)
  - added: query_log.py (query append-only changes.jsonl audit log)
  - simplified: validate_skill.py, measure_content.py, check_freshness.py (removed DuckDB deps, auto-discover skills)
  - added `.claude/settings.json` with PostToolUse hook config
  - added `.claude/hooks/check-skill-freshness.sh`
- all 10 SKILL.md files: added `metadata.last_verified: 2026-02-25` to frontmatter
- `pyproject.toml`: removed `duckdb` dependency
- `CLAUDE.md`: removed DuckDB/CDC/pipeline docs, updated maintenance section with hook/CLI model

## 0.12.1

### changed
- **env-forge**: extracted `scripts/shared.py` module from duplicated code in catalog.py and materialize.py (constants, download_file, load_jsonl, ensure_dir)
- **env-forge**: materialize.py now compile-checks generated server.py and verifiers.py before writing (WARNING on error, never blocks)
- **env-forge**: verifier assembly deduplicates imports across verifier records instead of raw code concatenation
- **env-forge**: forge.md adds new step 2 "Reference from Catalog" (search AWM-1K for structural exemplar before generating from scratch)
- **env-forge**: README.md expanded with Quick Start, Status (Phase 1 vs 2), and Patterns sections
- `docs/README.md`: expanded to authoritative documentation index (16 analysis reports, synthesis, internals, 18 captured claude-docs)
- `CLAUDE.md`: replaced 36-line documentation index with pointer to docs/README.md; added catalog-as-exemplar pattern and huggingface-hub dependency; fixed domain report count (15 -> 16); net ~20 lines removed

## 0.12.0

### added
- **env-forge**: new installable plugin for generating database-backed MCP tool environments
  - SKILL.md: task-first environment design methodology extracted from AWM synthesis pipeline
  - 2 commands (browse, forge) + 2 Phase 2 stubs (launch, verify)
  - references: schema_patterns.md, api_design_rules.md, verification_patterns.md, fastapi_mcp_template.md, catalog_index.md
  - scripts: catalog.py (search/browse AWM-1K on HF), materialize.py (fetch and write environment), validate_env.py (structural validation)
  - two modes: browse 1000 pre-generated environments from AWM-1K catalog, or forge new ones from scenario descriptions
  - covers: SQLite schema synthesis, RESTful API design, FastAPI+MCP server generation, DB state verification, self-correction patterns
  - fetches data from Snowflake/AgentWorldModel-1K on HF at runtime (no large files in repo)

## 0.11.3

### added
- `skill-dashboard`: new project-scoped Python MCP App plugin
  - pure Python server (FastMCP + mcp-ui rawHtml) -- no Node.js or build step
  - reads skill registry from `skill-maintainer/config.yaml`, SKILL.md frontmatter for versions
  - queries DuckDB store for freshness and token budget data; falls back to file mtime scan
  - self-contained HTML dashboard (Tailwind CDN + Alpine.js CDN) with color-coded status, budget bars, and filter buttons
  - reference implementation for the Python-native MCP App pattern
  - `mcp-ui-server` editable dependency added to `pyproject.toml`
- `.claude/rules/general.md`: always-loaded general conventions (package manager, JSON, logs, READMEs)
- `.claude/rules/skills.md`: path-scoped to `**/SKILL.md` -- trigger phrases, 1024-char limit, script paths, 500-line limit
- `.claude/rules/plugins.md`: path-scoped to `**/.claude-plugin/**`, `**/plugin.json` -- new plugin checklist, auto-discovery, required fields

### changed
- `skill-maintainer/config.yaml`: added `https://code.claude.com/docs/en/memory` to `anthropic-skills-docs` watched pages
- `CLAUDE.md`: removed Conventions section (~28 lines); replaced with one-liner pointing to `.claude/rules/`; fixed domain report count (14 -> 15)

## 0.11.2

### added
- `docs/analysis/memory_and_rules_system.md`: domain report covering the six-level memory hierarchy, auto memory storage and behavior, CLAUDE.md import syntax, `.claude/rules/` modular path-scoped rules, glob patterns, organization-level management, and how this repo uses memory
- `docs/reports/claude_ecosystem_synthesis.md`: new section 2.5 (Memory and Rules System) with hierarchy table, auto memory details, import syntax, rules comparison table
- `docs/reports/claude_ecosystem_synthesis.md`: memory & rules row added to Component Maturity Assessment (section 4)
- `docs/reports/claude_ecosystem_synthesis.md`: memory mentions added to Solo (CLAUDE.local.md, auto memory) and Team (.claude/rules/) building strategies (section 5), and Enterprise (managed policy CLAUDE.md) tier (section 5)
- `docs/reports/claude_ecosystem_synthesis.md`: auto memory and project memory rows added to This Repo as Reference (section 10)
- `docs/reports/claude_ecosystem_synthesis.md`: memory report added to Report Index (section 11)

### changed
- `skill-maintainer/SKILL.md`: added disambiguation note in journal section distinguishing DuckDB session journal from Claude's built-in auto memory system

## 0.11.1

### fixed
- **mece-decomposer MCP App**: VALIDATE_SCRIPT path resolution broken when running from compiled `dist/index.cjs` -- `import.meta.dirname` polyfills to `__dirname` (= `mcp-app/dist/`), so `..` resolved to `mcp-app/` instead of `mece-decomposer/`. Added `PLUGIN_ROOT` constant with source vs dist detection.
- **mece-decomposer MCP App**: HTTP server bound to `0.0.0.0` (all interfaces) creating DNS rebinding risk. Changed to `127.0.0.1` (localhost only).
- **mece-decomposer MCP App**: stale build artifacts (`index.js`, `server.js`) accumulating in `dist/` from older builds. Added `prebuild` script to clean dist before each build.

## 0.11.0

### added
- **7 domain reports** in `docs/analysis/`: comprehensive coverage of the Claude extension ecosystem
  - `plugin_system_architecture.md`: plugin anatomy, schema, component types, auto-discovery, implementation audit of all 7 repo plugins
  - `marketplace_distribution_patterns.md`: marketplace schema, source types, monorepo patterns, enterprise distribution
  - `mcp_protocol_and_servers.md`: MCP protocol fundamentals, primitives, transports, TypeScript/Python SDKs, inspector, registry
  - `mcp_apps_and_ui_development.md`: MCP Apps SDK, MCP UI SDK, tool-UI linkage, React hooks, framework templates, bundling
  - `hooks_system_patterns.md`: all 14 event types, 3 hook types, matchers, security/automation patterns, plugin hooks
  - `subagents_and_agent_teams.md`: custom agents, built-in agents, tool control, agent teams, delegation patterns
  - `cross_surface_compatibility.md`: 7 surfaces, feature compatibility matrix, transport requirements, permission model differences
- **synthesis report** in `docs/reports/claude_ecosystem_synthesis.md`: executive summary, architecture decision tree, component maturity assessment, building strategies, cross-surface strategy, maintenance problem, report index

### changed
- `CLAUDE.md`: refactored to cover full ecosystem (plugins, MCP, hooks, agents), added documentation index section, added plugin/MCP development sections, streamlined from 251 to 256 lines
- `README.md`: added documentation section with links to all 14 domain reports and synthesis, organized by domain/existing/synthesis/internals categories

## 0.10.0

### added
- **mece-decomposer MCP App**: interactive tree visualization companion for MECE decompositions
  - 4 MCP tools: mece-decompose (tree render), mece-validate (structural validation), mece-refine-node (app-only editing), mece-export-sdk (Agent SDK code generation)
  - React UI with recursive tree view, expand/collapse, node selection, dependency badges
  - streaming support via useStreamingTree hook (progressive tree building as Claude generates)
  - sidebar panels: metadata, node detail (editable), validation report with score gauges, export preview with copy
  - SDK code generation: walks tree recursively, emits Agent() for agent atoms, orchestration functions for branches
  - follows ext-apps SDK patterns (basic-server-react structure, threejs-server wrapper pattern)
  - validation tool spawns validate_mece.py via subprocess with graceful fallback if uv unavailable
  - co-located at mece-decomposer/mcp-app/

## 0.9.0

### added
- **mece-decomposer**: new installable plugin for MECE decomposition of goals, tasks, and workflows
  - SKILL.md: 4 commands (decompose, interview, validate, export)
  - references: decomposition_methodology.md, sme_interview_protocol.md, validation_heuristics.md, agent_sdk_mapping.md, output_schema.md
  - scripts: validate_mece.py for deterministic structural validation of decomposition JSON
  - dual output: human-readable tree for SME validation + structured JSON mapping to Agent SDK primitives
  - covers: MECE scoring rubrics, depth-adaptive rigor, atomicity criteria, cross-branch dependency scanning

### fixed
- restored root pyproject.toml (was accidentally overwritten by mece-decomposer-specific one)
- restructured mece-decomposer to standard plugin layout (skills/mece-decomposer/)

## 0.8.0

### added
- **tui-design**: new installable plugin for terminal UI design
  - SKILL.md: 5 principles (semantic color, responsive layout, right component, visual hierarchy, progressive density)
  - references: rich_patterns.md, questionary_patterns.md, anti_patterns.md, layout_recipes.md
  - covers: Rich component selection, Questionary interactive prompts, 9 anti-patterns with before/after, 4 complete layout recipes
  - 16-color safe palette with semantic meanings, pipe-safe output patterns

## 0.7.0

### added
- **dimensional-modeling**: new installable plugin for Kimball-style star schema design
  - SKILL.md: router skill teaching dimensional modeling patterns for DuckDB agent state
  - references: schema_patterns.md, query_patterns.md, key_generation.md, anti_patterns.md, dag_execution.md
  - covers: SCD Type 2 dimensions, hash surrogate keys, fact table design, analytical views, agent execution DAG
- star-schema-llm-context: repo cleanup
  - deleted ~3950 lines of dead knowledge graph code (graph_algorithms.py, mcp_server.py, schema.sql, db_manager.py, setup.py, requirements.txt, Makefile, ARCHITECTURE.md, config.yaml)
  - rewrote README.md with clear vision statement (pattern library, not code library)
  - rewrote CLAUDE.md to reflect current state
  - added pyproject.toml
  - replaced speculative expansion roadmap (embeddings, graph DB) with DAG execution model and automation patterns

## 0.6.0

### changed
- **store.py**: complete rewrite from OLTP to Kimball dimensional model
  - MD5 hash surrogate keys on all dimensions (replaced integer PKs and MAX(id)+1 pattern)
  - SCD Type 2 on all dimension tables (effective_from/to, is_current, hash_diff for change detection)
  - no PRIMARY KEY constraints on dimensions (SCD Type 2 requires multiple rows per entity)
  - no primary keys on fact tables (dropped all 6 sequences; grain = composite dimension keys + timestamp)
  - no FK constraints (join by convention, validate at application layer)
  - metadata columns on all tables: record_source, session_id, inserted_at
  - meta_schema_version table for schema evolution tracking
  - meta_load_log table for operational visibility (script execution tracking)
  - merged fact_session into fact_session_event (session boundaries are events with event_type='session_start'/'session_end')
  - all views updated to filter is_current = TRUE and join on hash_key
  - automatic v1 -> v2 schema migration (detects old schema, drops and recreates)
- **migrate_state.py**: added --force flag for clean schema recreation, integrated with meta_load_log
- **source_monitor.py**: explicit record_source='source_monitor' on change records
- **journal.py**: rewritten for merged session/event model (no more fact_session table)
- duckdb_schema.md: complete rewrite reflecting v2 Kimball schema

### added
- `v_skill_budget_trend` view and `--budget-trend` CLI flag: token budget trend over time per skill (meta-cognition: "am I getting fatter?")
- `docs/analysis/abstraction_analogies.md`: unified framework document -- selection under constraint, five invariant operations (decompose/route/prune/synthesize/verify), database analogy for skills, DAG hierarchy model
- CLAUDE.md: selection-under-constraint design principle, dimensional model section, three-repo architecture
- README.md: design philosophy section
- star-schema-llm-context design docs: library_design.md and abstraction_analogies.md (canonical home)

### fixed
- SCD Type 2 bug: removed PRIMARY KEY from dimension tables that would cause constraint violations when closing old rows and opening new ones (hash_key must appear in multiple rows for SCD Type 2)

## 0.5.0

### added
- DuckDB-backed relational store (`store.py`) replacing flat `state.json` overwrite pattern
  - star schema: dimension tables (dim_source, dim_skill, dim_page, skill_source_dep) + append-only fact tables (fact_watermark_check, fact_change, fact_validation, fact_update_attempt, fact_content_measurement, fact_session, fact_session_event)
  - pre-built views: v_latest_watermark, v_latest_page_hash, v_skill_freshness, v_skill_budget, v_latest_source_check
  - WAL mode for concurrent access from hooks
  - backward-compatible state.json export via `Store.export_state_json()`
- `migrate_state.py`: one-time migration from state.json into DuckDB with round-trip verification
- `measure_content.py`: token budget tracker for all tracked skills
  - walks skill directories, classifies files, measures line/word/char/token counts
  - budget thresholds: 4000 tokens (warn), 8000 tokens (critical)
  - records measurements in fact_content_measurement for historical tracking
- `journal.py`: session activity logger with three modes
  - append: fast JSONL buffer for hooks (no DuckDB access, <50ms)
  - ingest: batch import JSONL into DuckDB
  - query: show recent session activity with filters
- `/skill-maintainer budget` command for token budget measurement
- `/skill-maintainer history` command for temporal change queries
- `/skill-maintainer journal` command for session activity queries
- `docs/internals/duckdb_schema.md`: full schema documentation
- `docs/analysis/data_centric_agent_state_research.md`: strategic research on star schema patterns for LLM agent systems (10 use cases analyzed)
- `duckdb>=1.0` dependency

### changed
- `docs_monitor.py`: migrated from load_state/save_state to Store class
- `source_monitor.py`: migrated from load_state/save_state to Store class
- `check_freshness.py`: migrated from JSON traversal to DuckDB v_skill_freshness view
- `apply_updates.py`: records update attempts and validations in DuckDB
- `validate_skill.py`: records validation results in fact_validation table
- `update_report.py`: reads changes from DuckDB instead of state dict
- skill-maintainer SKILL.md version bumped to 0.2.0 with new commands documented

## 0.4.0

### changed
- migrated all plugins to canonical `.claude-plugin/plugin.json` manifest location (was `plugin.json` at root)
- removed non-standard `skills` and `agents` array fields from plugin manifests (auto-discovery handles these)
- added `repository` field to all plugin manifests
- created root `.claude-plugin/marketplace.json` making this repo a proper plugin marketplace
- rewrote README.md installation section with correct CLI commands (`install`/`uninstall`, not `add`/`remove`)
- README.md now documents the marketplace-based install flow (`/plugin marketplace add fblissjr/fb-claude-skills`)
- README.md usage section updated with correct namespaced skill invocations
- updated CLAUDE.md repo structure and installation sections to match new layout
- replaced docs/claude-docs/ HTML scrapes with clean markdown from live site (3 replaced, 2 new)
- added docs/claude-docs/claude_docs_discover_plugins.md and claude_docs_plugin_marketplaces.md
- updated docs/README.md with claude-docs contents table
- added discover-plugins and plugin-marketplaces to skill-maintainer config.yaml watched pages
- updated docs/analysis/skills_guide_analysis.md with v0.4.0 compliance section
- added skill-maintainer/README.md (was the only module without one)

## 0.3.1

### added
- heylook-monitor: MCP App dashboard for heylookitsanllm local LLM server
  - live monitoring: models, system metrics (RAM/CPU), per-model performance (TPS, latency)
  - quick inference panel for testing prompts against local models
  - 4 tools: show_llm_dashboard, poll_status, quick_inference, list_local_models
  - server-side API proxying (no CSP issues), auto-polling with graceful degradation
  - follows system-monitor-server reference implementation pattern

### changed
- web-tdd: restructured as installable plugin (SKILL.md moved to `skills/web-tdd/SKILL.md`, added plugin.json, metadata fields)
- cogapp-markdown: restructured as installable plugin (SKILL.md moved to `skills/cogapp-markdown/SKILL.md`, added plugin.json, metadata fields)
- all plugin READMEs: standardized with installation commands, skills table, invocation examples
- root README.md: added comprehensive installation guide (clone + install, GitHub install, project-scoped, uninstall, usage)
- CLAUDE.md: added Installation section, updated repo structure to reflect plugin layout, added READMEs convention

## 0.3.0

### added
- mcp-apps: new skill module for building and migrating MCP Apps (interactive UIs for MCP)
  - create-mcp-app skill: guides building MCP Apps from scratch (framework selection, tool+resource registration, theming, streaming, testing)
  - migrate-oai-app skill: step-by-step migration from OpenAI Apps SDK to MCP Apps SDK with API mapping tables and CSP checklist
  - plugin.json: plugin manifest with both skills
  - references/: local copies of upstream docs (overview, patterns, testing, specification, migration guide) for offline use
  - README.md: user-facing documentation
- skill-maintainer: ext-apps source added to config.yaml for upstream change detection
  - monitors 7 upstream files (2 skills, 1 spec, 4 docs)
  - create-mcp-app and migrate-oai-app tracked as managed skills
- docs/internals/: technical documentation for skill-maintainer system
  - api_reference.md: function signatures, parameters, return types for all Python scripts
  - schema.md: formal schemas for state.json and config.yaml
  - troubleshooting.md: common issues, error messages, recovery procedures
- docs/README.md: documentation index linking all doc sections
- CLAUDE.md: added "adding a new skill module" checklist and direct skills-ref validate shortcut

## 0.2.1

### changed
- docs_monitor.py: rewritten as CDC pipeline (detect -> identify -> classify)
  - detect: HEAD request comparing Last-Modified header (zero bandwidth if unchanged)
  - identify: fetch llms-full.txt, split by page, hash each watched page
  - classify: keyword heuristic on diff text
  - removed markdownify dependency (no longer needed)
- config.yaml: sources use llms_full_url + pages instead of individual urls
- state.json: new format with _watermark (per-source) and _pages (per-page) with last_changed tracking
- check_freshness.py, apply_updates.py, update_report.py: updated for new state format

### removed
- .github/workflows/skill-maintenance.yml and validate-skills.yml: local freshness hooks are sufficient; CI adds overhead without value for solo use

## 0.2.0

### added
- skill-maintainer: new skill for automated skill maintenance and monitoring
  - docs_monitor.py: hash-based change detection for Anthropic docs URLs
  - source_monitor.py: git-based upstream code change detection (generalized from mlx-skills)
  - update_report.py: unified change report generation
  - apply_updates.py: update pipeline with report-only, apply-local, and create-pr modes
  - validate_skill.py: extended validation wrapping skills-ref with best practice checks
  - check_freshness.py: lightweight staleness check for hooks integration
  - config.yaml: source registry and skill tracking configuration
  - references/: best practices, monitored sources, update patterns documentation
  - state/: versioned state for content hashes, timestamps, versions
- docs/analysis/: structured reference documentation
  - skills_guide_structured.md: full extraction from Anthropic skills guide PDF
  - skills_guide_analysis.md: gap analysis and actionable findings
  - self_updating_system_design.md: cross-reference of all sources with architecture decisions
- GitHub Actions workflows
  - skill-maintenance.yml: daily cron + manual dispatch for automated monitoring
  - validate-skills.yml: PR validation for skill file changes
- pyproject.toml: uv-based dependency management with skills-ref integration

### fixed
- docs_monitor.py: content extraction now extracts main content div instead of capturing raw JS/CSS from Next.js pages

### changed
- plugin-toolkit/skills/plugin-toolkit/SKILL.md: added metadata.version field
- CLAUDE.md: comprehensive get-up-to-speed guide for the repo (Phase 8)

## 0.1.0

### added
- plugin-toolkit: plugin analysis, polish, and feature management skill
- web-tdd: test-driven development workflow for web applications
- cogapp-markdown: auto-generate markdown sections using cogapp
