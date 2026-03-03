last updated: 2026-03-03

# best practices checklist

Machine-parseable best practices extracted from the Anthropic skills guide (PDF), official Claude Code docs, Agent Skills spec, and this repo's design principles (see `VISION.md`). Used by skill-maintainer scripts and the test suite to validate skills and detect drift.

## context hygiene

These checks enforce the retrieval principles in `VISION.md`. The context window is attention, not memory. Every loaded item competes for the model's focus.

### token budget

- [ ] Skill directory total under 4,000 tokens (2% of 200k context window). Estimation: chars / 4
- [ ] Skill directory total under 8,000 tokens (hard ceiling -- above this degrades attention on other context)
- [ ] SKILL.md body under 500 lines
- [ ] Heavy reference material in `references/` directory, not inline in SKILL.md
- [ ] Token estimation is approximate (chars / 4). Real tokenization varies by content type. Treat as a budget heuristic, not exact measurement

### description precision

Descriptions are reverse queries. They determine when a skill loads. Vague descriptions cause overtriggering (low precision). Missing trigger phrases cause undertriggering (low recall).

- [ ] Description includes WHAT the skill does (action verbs: handles, generates, validates, designs)
- [ ] Description includes WHEN to use it (trigger phrases: "use when user says...", "when the user wants to...")
- [ ] Description is specific enough to avoid matching unrelated queries
- [ ] Description includes negative scope if needed ("do NOT use for...")
- [ ] No duplicate or near-duplicate descriptions across skills (causes ambiguous routing)

### always-loaded context

Everything in this list loads on every session. Each line is a fixed cost.

- [ ] CLAUDE.md: only operational instructions, no reference material
- [ ] `.claude/rules/`: unconditional rules are minimal; use path globs to scope rules that don't apply everywhere
- [ ] Skill descriptions (all installed): each must justify its presence in the 2% budget
- [ ] `settings.json`: no ambient hooks that fire on high-frequency events without documented justification
- [ ] Auto-memory (MEMORY.md): under 200 lines, no session-specific or stale entries

### hooks

- [ ] No hooks that fire on every tool call, file read, or other high-frequency event without documented justification
- [ ] Hook purpose and trigger documented in README or inline comments
- [ ] Hook output is minimal (one-line stderr, not paragraphs of context)
- [ ] All hooks exit 0 (non-blocking) unless they are intentional gates (like pre-commit validation)

## skill structure

Source: Anthropic skills guide (PDF, Jan 2026)

### file layout

- [ ] SKILL.md file exists (exact case: `SKILL.md`)
- [ ] Folder named in kebab-case
- [ ] YAML frontmatter has `---` delimiters
- [ ] No README.md inside skill folder (docs go in SKILL.md or references/)
- [ ] Detailed docs moved to `references/` and linked from SKILL.md body

### frontmatter fields

- [ ] `name` field: kebab-case, no spaces, no capitals, matches folder name
- [ ] `name` field: max 64 characters
- [ ] `name` field: does not contain "claude" or "anthropic" (reserved)
- [ ] `description` field: under 1024 characters
- [ ] `description` field: no XML angle brackets (< >)
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

## invocation control

Source: Claude Code official docs

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

## spec compliance

Source: Agent Skills spec (agentskills.io). Enforced by `agentskills validate`.

- [ ] name: required, non-empty string
- [ ] name: lowercase only (Unicode letters + hyphens allowed)
- [ ] name: no consecutive hyphens (--)
- [ ] name: cannot start/end with hyphen
- [ ] name: directory name must match skill name exactly
- [ ] name: NFKC Unicode normalization applied
- [ ] description: required, non-empty string
- [ ] Only allowed fields in frontmatter: name, description, license, allowed-tools, metadata, compatibility

## maintenance

- [ ] `metadata.last_verified` present in every SKILL.md frontmatter
- [ ] `last_verified` date is within 30 days
- [ ] Plugin listed in root `marketplace.json` (if installable)
- [ ] Plugin has a README.md with installation instructions
- [ ] Plugin `plugin.json` has required fields: name, version, description, author, repository
- [ ] `best_practices.md` has a `last updated` date within 30 days

## quality signals

Source: Anthropic skills guide (PDF)

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

### undertriggering (low recall)

- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Fix: add more detail and keywords to description

### overtriggering (low precision)

- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Fix: add negative triggers, be more specific, clarify scope
