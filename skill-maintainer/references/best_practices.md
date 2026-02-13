last updated: 2026-02-13

# best practices checklist

Machine-parseable best practices extracted from the Anthropic skills guide (PDF), official Claude Code docs, and Agent Skills spec. Used by the skill-maintainer to validate skills and detect drift.

## source: anthropic skills guide (pdf, jan 2026)

### structure

- [ ] SKILL.md file exists (exact case: `SKILL.md`)
- [ ] Folder named in kebab-case
- [ ] YAML frontmatter has `---` delimiters
- [ ] No README.md inside skill folder (docs go in SKILL.md or references/)
- [ ] SKILL.md under 500 lines / 5000 words
- [ ] Detailed docs moved to `references/` and linked

### frontmatter fields

- [ ] `name` field: kebab-case, no spaces, no capitals, matches folder name
- [ ] `name` field: max 64 characters
- [ ] `description` field: includes WHAT it does + WHEN to use it (trigger conditions)
- [ ] `description` field: under 1024 characters
- [ ] `description` field: no XML angle brackets (< >)
- [ ] `description` field: includes specific tasks users might say
- [ ] `description` field: mentions relevant file types if applicable
- [ ] `name` field: does not contain "claude" or "anthropic" (reserved)
- [ ] `license` field: present if open source (MIT, Apache-2.0)
- [ ] `compatibility` field: under 500 characters, lists env requirements
- [ ] `metadata` field: key-value pairs only (author, version, mcp-server)
- [ ] No unexpected fields in frontmatter (allowed: name, description, license, allowed-tools, metadata, compatibility)

### instructions quality

- [ ] Instructions are specific and actionable (not vague)
- [ ] Steps include expected commands with actual arguments
- [ ] Error handling section included with common issues
- [ ] Examples provided showing expected input/output
- [ ] References to bundled files are clearly linked
- [ ] No ambiguous language ("validate things properly" -> specific checks)
- [ ] Critical instructions at the top, not buried
- [ ] Bullet points and numbered lists preferred over prose

### progressive disclosure

- [ ] First level (frontmatter): just enough for Claude to know when to load
- [ ] Second level (SKILL.md body): full instructions when skill is relevant
- [ ] Third level (linked files): additional detail loaded on demand

## source: claude code official docs

### invocation control

- [ ] `disable-model-invocation: true` for side-effect workflows (deploy, commit)
- [ ] `user-invocable: false` for background knowledge skills
- [ ] `context: fork` for isolated execution (subagent)
- [ ] `allowed-tools` restricts tool access when skill is active

### string substitutions

- [ ] `$ARGUMENTS` for all arguments passed to skill
- [ ] `$ARGUMENTS[N]` or `$N` for positional arguments
- [ ] `${CLAUDE_SESSION_ID}` for session tracking
- [ ] Dynamic context via `!`command`` syntax (preprocessed)

### distribution

- [ ] Personal skills: `~/.claude/skills/<name>/SKILL.md`
- [ ] Project skills: `.claude/skills/<name>/SKILL.md`
- [ ] Plugin skills: `<plugin>/skills/<name>/SKILL.md`
- [ ] Skill descriptions budget: 2% of context window (fallback 16k chars)

## source: agent skills spec (agentskills.io)

### validation rules (from skills-ref validator)

- [ ] name: required, non-empty string
- [ ] name: lowercase only (Unicode letters + hyphens allowed)
- [ ] name: no consecutive hyphens (--)
- [ ] name: cannot start/end with hyphen
- [ ] name: directory name must match skill name exactly
- [ ] name: NFKC Unicode normalization applied
- [ ] description: required, non-empty string
- [ ] Only allowed fields in frontmatter: name, description, license, allowed-tools, metadata, compatibility

## quality metrics (from pdf guide)

### quantitative

- Skill triggers on 90% of relevant queries
- Completes workflow in X tool calls (compare with/without skill)
- 0 failed API calls per workflow

### qualitative

- Users don't need to prompt Claude about next steps
- Workflows complete without user correction
- Consistent results across sessions
- New user can accomplish task on first try with minimal guidance

## iteration signals

### undertriggering

- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Fix: add more detail and keywords to description

### overtriggering

- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Fix: add negative triggers, be more specific, clarify scope
