# design principles

Skills are retrieval. The same principles that govern search and information retrieval govern how skills, rules, and context should be designed, loaded, and maintained.

## the retrieval problem

An LLM's context window is not memory -- it is attention. Everything loaded into the window competes for the model's attention. Irrelevant context doesn't just waste tokens. It degrades accuracy, causes unintended behavior, and dilutes the signal the model needs to do its job.

The core problem: given a user's intent, retrieve the right context at the right time, and nothing else.

This is precision and recall applied to context:

- **Precision** (of loaded context): what fraction of the context window is relevant to the current task? Low precision means irrelevant context is loaded -- skill overtriggering, bloated SKILL.md files, ambient hooks injecting noise. The consequence is behavioral corruption: the model acts on information it shouldn't have.

- **Recall** (of needed context): does the model have everything it needs? Low recall means the model falls back to training data, which is stale, unversioned, and unauditable. Controlled retrieval via skills is always preferable to hoping the model "knows" something.

**High precision is the constraint. High recall is the goal.** Retrieve as much relevant context as possible without retrieving irrelevant context. The failure modes are asymmetric: low precision causes active harm (wrong behavior), low recall causes passive degradation (generic behavior). Both are bad. Low precision is worse because you can't un-pollute a context window mid-session.

## what gets loaded and when

Every Claude Code session in this project loads context before the user types anything:

| Layer | What | When loaded | Control mechanism |
|-------|------|-------------|-------------------|
| Global instructions | `~/.claude/CLAUDE.md` | Always | Edit the file |
| Project instructions | `./CLAUDE.md` | Always | Edit the file |
| Auto-memory | `~/.claude/projects/.../memory/MEMORY.md` | Always (first 200 lines) | Edit the file |
| Unconditional rules | `.claude/rules/general.md` | Always | Edit or delete |
| Conditional rules | `.claude/rules/skills.md`, `plugins.md` | When matching files are in context | Path globs in frontmatter |
| Skill descriptions | All installed SKILL.md frontmatter | Always (2% of context budget) | Install/uninstall plugins |
| Settings | `.claude/settings.json` | Always | Edit the file |

This is the static index. It is the always-on cost of this project. Every line must justify its presence.

Skill bodies and references load dynamically:

| Layer | When loaded | Trigger |
|-------|-------------|---------|
| SKILL.md body | When Claude decides the skill is relevant | Description match against user intent |
| `references/` files | When the skill body references them | Explicit link in SKILL.md |
| Scripts | When invoked by the skill | `uv run` or subprocess call |

This three-level structure is staged retrieval:
1. **Index** (frontmatter): always loaded. Tiny, precise. Determines routing.
2. **Summary** (SKILL.md body): loaded on match. Full instructions for the workflow.
3. **Full documents** (references/): loaded on demand. Deep detail when needed.

This maps directly to how a search engine works: index -> snippet -> full page. Each level is a precision gate.

## principles

### 1. optimize for relevant context at the right time

Not minimal context. Not maximal context. **Relevant** context. A complex workflow skill legitimately needs reference material -- but that material should load only when the skill is active, not when it's being considered for activation.

Progressive disclosure is the mechanism: frontmatter is the filter, body is the payload, references are the deep store.

### 2. precision is the constraint, recall is the goal

Every piece of loaded context should be relevant to the current task (precision). Within that constraint, retrieve everything the model needs to avoid falling back to training data (recall).

When in doubt, err on the side of not loading. The user can always ask for more context. They cannot remove context that's already been loaded.

### 3. descriptions are queries in reverse

A skill description is not documentation. It is a **reverse query** -- it describes the set of user intents that should match this skill. The same techniques that make search queries effective make skill descriptions effective: specific terms, explicit scope, negative conditions.

A vague description is a broad query. It matches too much. A precise description with trigger phrases and scope boundaries is a targeted query. It matches what it should and nothing else.

### 4. every always-loaded line must justify its presence

CLAUDE.md, rules, memory, and skill descriptions load on every session. They are the fixed cost of this project. Treat them like a database index: essential for routing, deadly if bloated.

If a rule applies only sometimes, scope it with path globs. If a CLAUDE.md section is only relevant during maintenance, move it to a referenced file. If a skill description is longer than necessary for routing, trim it.

### 5. controlled retrieval over training data

When the model needs domain knowledge, prefer retrieving it from a skill or reference file over relying on training data. Training data is:
- Stale (frozen at a cutoff date)
- Unversioned (you can't diff what the model "knows")
- Unauditable (you can't inspect what it will retrieve from memory)

A skill is versioned, inspectable, updatable, and testable. When you find yourself relying on the model's innate knowledge repeatedly for the same domain, that's a signal to create a skill.

### 6. human feedback closes the loop

Retrieval quality cannot be fully automated. Whether a skill triggered at the right time, whether the loaded context was helpful, whether the result was accurate -- these require human judgment. The maintenance workflow (`/maintain`, test suite, best practices review) keeps a human in the loop for quality decisions that can't be reduced to property checks.

## what this means for this repo

These principles govern everything in fb-claude-skills:

- **Skill authoring**: descriptions are reverse queries (principle 3). Bodies use progressive disclosure (principle 1). Token budgets enforce index hygiene (principle 4).
- **Plugin distribution**: marketplace listing is the catalog. Install/uninstall is the user controlling what's in their always-loaded index (principle 4).
- **Maintenance**: `/maintain` detects when upstream changes affect retrieval quality. The test suite encodes measurable properties. Human review handles the rest (principle 6).
- **Hooks**: must justify their trigger frequency and context injection. Nothing fires ambiently without documented rationale (principles 2 and 4).
- **Rules**: unconditional rules are always-on cost. Conditional (path-scoped) rules are precision-gated retrieval (principle 1).
