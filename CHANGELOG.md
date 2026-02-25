# changelog

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
