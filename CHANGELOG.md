# changelog

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
