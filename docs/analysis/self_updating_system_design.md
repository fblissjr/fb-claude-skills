last updated: 2026-02-13

# self-updating system design

Cross-reference of all source materials with change detection strategies and mapping to skill components.

## source materials inventory

### 1. anthropic skills guide (pdf)

- **location**: `docs/guides/The-Complete-Guide-to-Building-Skill-for-Claude.pdf`
- **structured extraction**: `docs/analysis/skills_guide_structured.md`
- **format**: PDF, 30 pages, 6 chapters
- **published**: January 2026
- **change detection**: File hash comparison
- **update frequency**: Unknown (published once so far)
- **impact**: High - defines best practices for all skills

Key content areas:
- Fundamentals (skill structure, progressive disclosure, portability)
- Planning and design (use cases, success criteria, technical requirements, frontmatter, instructions)
- Testing and iteration (trigger tests, functional tests, performance comparison)
- Distribution and sharing (upload, API, Agent Skills standard, positioning)
- Patterns and troubleshooting (5 patterns, troubleshooting guide)
- Resources and references (official docs, blog posts, example skills, checklist)

### 2. claude code official docs - skills page

- **url**: https://code.claude.com/docs/en/skills
- **local copy**: `docs/claude-docs/claude_docs_skills.md`
- **change detection**: Hash-based (fetch, convert to markdown, hash)
- **update frequency**: Frequent (product releases)
- **impact**: High - authoritative source for features and frontmatter

Key content areas:
- Frontmatter reference (all fields, including Claude Code extensions like context, agent, hooks)
- String substitutions ($ARGUMENTS, $N, ${CLAUDE_SESSION_ID})
- Supporting files pattern
- Invocation control (disable-model-invocation, user-invocable)
- Subagent execution (context: fork, agent types)
- Dynamic context injection (!`command` syntax)
- Visual output generation
- Troubleshooting

**Notable divergences from PDF guide**: The docs page includes fields not in the PDF (argument-hint, disable-model-invocation, user-invocable, model, context, agent, hooks). These are Claude Code extensions to the Agent Skills standard.

### 3. claude code official docs - plugins page

- **url**: https://code.claude.com/docs/en/plugins
- **change detection**: Hash-based
- **impact**: Medium - affects plugin-toolkit skill

### 4. claude code official docs - hooks guide

- **url**: https://code.claude.com/docs/en/hooks-guide
- **change detection**: Hash-based
- **impact**: Medium - affects hook integration in skill-maintainer

### 5. agent skills specification

- **repo**: https://github.com/agentskills/agentskills
- **key files**:
  - `docs/specification.mdx` - the spec itself
  - `skills-ref/src/skills_ref/validator.py` - validation logic
  - `skills-ref/src/skills_ref/parser.py` - parsing logic
- **change detection**: Git-based (commit monitoring)
- **update frequency**: Active development
- **impact**: Critical - defines what makes a valid skill

Key validation rules (from skills-ref):
- name: max 64 chars, lowercase, kebab-case, NFKC normalized
- description: max 1024 chars, non-empty
- compatibility: max 500 chars
- Allowed fields: name, description, license, allowed-tools, metadata, compatibility
- Directory name must match skill name

## change detection strategies

### hash-based (docs)

```
fetch URL -> convert HTML to markdown -> normalize whitespace -> SHA-256 hash
compare to stored hash -> if different: classify change -> update state
```

Advantages:
- Simple, reliable
- Works for any URL
- Catches all changes (content, structure, formatting)

Limitations:
- Can't distinguish meaningful changes from cosmetic ones without deeper analysis
- Requires fetching the full page each time
- Rate-sensitive to page layout changes that don't affect content

Mitigation: Normalize aggressively (strip whitespace, navigation, images) before hashing. Classify changes using keyword heuristics.

### git-based (source repos)

```
shallow clone with --shallow-since -> get commits -> filter to watched files
extract APIs from changed Python files -> check for deprecation keywords
```

Advantages:
- Rich metadata (commit messages, authors, file-level changes)
- Can detect breaking changes via keyword scanning
- API extraction gives precise impact assessment

Limitations:
- Requires git access (public repos or configured credentials)
- Shallow clones may miss context
- AST analysis only works for Python files

### file-hash (local files)

```
SHA-256 of file bytes -> compare to stored hash
```

For local files like the PDF guide that can't be fetched from a URL.

## mapping: sources to skill components

### what changes in each source affect

| Source | Affected Component | Change Type | Action |
|---|---|---|---|
| Skills docs: frontmatter reference | SKILL.md frontmatter | Field additions/changes | Update skills to use new fields |
| Skills docs: invocation control | SKILL.md frontmatter | New control options | Review if skills should use them |
| Skills docs: string substitutions | SKILL.md body | New variables available | Update skills if useful |
| Skills docs: troubleshooting | references/best_practices.md | New troubleshooting guidance | Update best practices |
| Plugins docs: plugin.json format | plugin-toolkit | Structure changes | Update plugin-toolkit skill |
| Hooks guide: hook API | check_freshness.py | Hook configuration changes | Update hook integration |
| Agent Skills spec: fields | All skills | New/changed required fields | Validate and update all skills |
| Agent Skills spec: validator | validate_skill.py | New validation rules | Update validation wrapper |
| Agent Skills spec: parser | All scripts | Parsing logic changes | Update if we parse frontmatter |
| PDF guide: best practices | references/best_practices.md | New recommendations | Update checklist |
| PDF guide: patterns | references/update_patterns.md | New patterns | Update patterns reference |

## architecture decisions

### state management

**Decision**: State in repo (`skill-maintainer/state/`), not in `~/.claude/`.

**Why**:
- Versioned with git, so changes are auditable
- Portable across machines (clone repo, get state)
- CI/CD can read and update state
- Backup is automatic (git history)

**Trade-off**: State shows up in git status. Mitigated by .gitignore for transient files and only committing meaningful state changes.

### update modes

**Decision**: Default to `apply-local` (apply changes, validate, don't commit).

**Why**:
- Safe: user reviews diff before committing
- Non-destructive: backups created before modification
- Flexible: user can accept, modify, or revert
- Trust: builds user confidence in the system

**Other modes**: `report-only` (just report), `create-pr` (for CI), `auto-update` (disabled by default).

### validation chain

**Decision**: Always validate after any update, using both skills-ref and extended checks.

**Why**:
- skills-ref is the authoritative validator for the Agent Skills spec
- Our extended checks add best-practice warnings from the Anthropic guide
- Double validation catches both structural and quality issues
- Failing validation prevents bad updates from landing

### progressive rollout

**Decision**: Start with docs monitoring and manual review. Add automation incrementally.

**Why**:
- Building trust in the system before automating
- Docs change less frequently than code, easier to validate
- Manual review catches false positives in change classification
- Can tune thresholds based on real data before automating

## monitoring schedule

| Source | Check Interval | Priority |
|---|---|---|
| anthropic-skills-docs | 24h | High |
| agentskills-spec | 24h | Critical |
| anthropic-skills-guide (PDF) | 168h (weekly) | Medium |

## future considerations

1. **Content-aware diffing**: Instead of just hash comparison, use LLM to summarize what changed and its significance.

2. **Auto-generated test suites**: When best practices change, automatically generate test queries to verify skills still work correctly.

3. **Dependency graph**: Track which skills depend on which reference files, so changes to references propagate correctly.

4. **Community skill monitoring**: Monitor the anthropics/skills repo for new example skills that demonstrate patterns we should adopt.

5. **API monitoring**: When the skills API adds new features (endpoints, parameters), detect and document them.
