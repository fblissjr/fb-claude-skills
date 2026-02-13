last updated: 2026-02-13

# monitored sources

What the skill-maintainer monitors for changes and why.

## docs sources

### anthropic skills docs
- **url**: https://code.claude.com/docs/en/skills
- **why**: Primary reference for skill structure, frontmatter fields, invocation control, string substitutions, and troubleshooting. Changes here directly affect how skills should be written.
- **change impact**: High. New frontmatter fields, changed validation rules, or new features require skill updates.
- **detection**: Hash-based. Fetch page, convert to markdown, hash content, compare to stored hash.

### anthropic plugins docs
- **url**: https://code.claude.com/docs/en/plugins
- **why**: Plugin packaging requirements affect plugin-toolkit and any skills distributed as plugins.
- **change impact**: Medium. plugin.json format changes, new plugin features.
- **detection**: Hash-based.

### anthropic hooks guide
- **url**: https://code.claude.com/docs/en/hooks-guide
- **why**: Hook integration is part of the skill-maintainer freshness check system.
- **change impact**: Medium. Hook API changes affect check_freshness.py integration.
- **detection**: Hash-based.

### anthropic skills guide (pdf)
- **file**: docs/guides/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- **why**: Comprehensive best practices guide. Updates mean new patterns, changed recommendations.
- **change impact**: High. Best practices changes ripple through all skills.
- **detection**: File hash comparison. Manual trigger when PDF is replaced.

## source repos

### agentskills spec
- **repo**: https://github.com/agentskills/agentskills
- **watched files**:
  - `docs/specification.mdx` - The spec itself; field additions, naming rule changes
  - `skills-ref/src/skills_ref/validator.py` - Validation logic; new checks, changed limits
  - `skills-ref/src/skills_ref/parser.py` - Parsing logic; new frontmatter handling
- **why**: The Agent Skills open standard defines what makes a valid skill. Changes here are authoritative.
- **change impact**: Critical. Breaking changes require immediate skill updates.
- **detection**: Git-based. Shallow clone, check commits since last run, analyze diffs.

### ext-apps (MCP Apps SDK)
- **repo**: https://github.com/modelcontextprotocol/ext-apps
- **watched files**:
  - `plugins/mcp-apps/skills/create-mcp-app/SKILL.md` - Upstream create skill; changes affect our adapted version
  - `plugins/mcp-apps/skills/migrate-oai-app/SKILL.md` - Upstream migrate skill; changes affect our adapted version
  - `specification/2026-01-26/apps.mdx` - The MCP Apps spec (SEP-1865); authoritative reference for both skills
  - `docs/patterns.md` - Production patterns reference; copied to local references/
  - `docs/overview.md` - Architecture overview; copied to local references/
  - `docs/testing-mcp-apps.md` - Testing guide; copied to local references/
  - `docs/migrate_from_openai_apps.md` - Migration mapping tables; copied to local references/
- **why**: The MCP Apps SDK is the upstream source for both mcp-apps skills. The skills are near-direct ports of the upstream Claude Code plugin skills, and the local references/ directory contains copies of upstream docs.
- **change impact**: High. Upstream skill changes should be reviewed and merged. Spec changes may require skill and reference updates. Doc changes should be synced to local references/.
- **detection**: Git-based. Shallow clone, check commits since last run, analyze diffs.

## adding new sources

To add a new source, edit `config.yaml` or use `/skill-maintainer add-source`.

For docs sources, provide the URL. The monitor will fetch, convert to markdown, and hash.

For source repos, provide the git URL and list of files to watch. The monitor will shallow-clone and check for commits affecting those files.
