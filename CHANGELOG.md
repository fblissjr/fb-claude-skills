# changelog

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
