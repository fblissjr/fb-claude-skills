last updated: 2026-02-14

# Anthropic Skills Best Practices Guide - Full Analysis Report

> Source: "The Complete Guide to Building Skills for Claude" (30-page PDF)

---

## Navigation

- [Part 1: Guide Summary](#part-1-guide-summary) -- Distilled best practices from the official PDF
  - [1.1 Fundamentals](#11-fundamentals)
  - [1.2 Planning and Design](#12-planning-and-design)
  - [1.3 Technical Requirements](#13-technical-requirements)
  - [1.4 Writing Effective Skills](#14-writing-effective-skills)
  - [1.5 Testing and Iteration](#15-testing-and-iteration)
  - [1.6 Distribution and Sharing](#16-distribution-and-sharing)
  - [1.7 Patterns and Troubleshooting](#17-patterns-and-troubleshooting)
  - [1.8 Quick Checklist](#18-quick-checklist-reference-a)

---

## Part 1: Guide Summary

### 1.1 Fundamentals

**What is a skill?**

A skill is a folder containing instructions that teach Claude how to handle specific tasks or workflows. It is packaged as a simple folder with:

- `SKILL.md` (required) -- Instructions in Markdown with YAML frontmatter
- `scripts/` (optional) -- Executable code (Python, Bash, etc.)
- `references/` (optional) -- Documentation loaded as needed
- `assets/` (optional) -- Templates, fonts, icons used in output

**Core design principles:**

1. **Progressive Disclosure** -- Skills use a three-level system:
   - **First level (YAML frontmatter)**: Always loaded into Claude's system prompt. Provides just enough information for Claude to know WHEN each skill should be used. Must be minimal to conserve tokens.
   - **Second level (SKILL.md body)**: Loaded only when Claude thinks the skill is relevant to the current task. Contains the full instructions and guidance.
   - **Third level (Linked files)**: Additional files bundled within the skill directory that Claude can choose to navigate and discover only as needed (references/, scripts/, etc.).

2. **Composability** -- Claude can load multiple skills simultaneously. Your skill should work well alongside others, not assume it is the only capability available.

3. **Portability** -- Skills work identically across Claude.ai, Claude Code, and API. Create a skill once and it works across all surfaces without modification, provided the environment supports any dependencies the skill requires.

**For MCP Builders: Skills + Connectors**

- MCP provides the professional kitchen (connectivity): Connects Claude to your service, provides real-time data access and tool invocation, defines what Claude can do
- Skills provide the recipes (knowledge): Teaches Claude how to use your service effectively, captures workflows and best practices, defines how Claude should do it

### 1.2 Planning and Design

**Start with use cases.** Before writing any code, identify 2-3 concrete use cases your skill should enable.

**Good use case definition format:**
```
Use Case: [Name]
Trigger: User says "[phrase]" or "[phrase]"
Steps:
1. [First action]
2. [Second action]
Result: [Expected outcome]
```

**Ask yourself:**
- What does a user want to accomplish?
- What multi-step workflows does this require?
- Which tools are needed (built-in or MCP)?
- What domain knowledge or best practices should be embedded?

**Common skill use case categories:**

| Category | Used For | Key Techniques |
|----------|----------|----------------|
| **Document & Asset Creation** | Creating consistent, high-quality output (documents, presentations, apps, designs, code) | Embedded style guides, template structures, quality checklists, no external tools needed |
| **Workflow Automation** | Multi-step processes benefiting from consistent methodology, including multi-MCP coordination | Step-by-step workflow with validation gates, templates for common structures, built-in review suggestions, iterative refinement loops |
| **MCP Enhancement** | Workflow guidance to enhance tool access an MCP server provides | Coordinates multiple MCP calls in sequence, embeds domain expertise, provides context users would otherwise need to specify, error handling for common MCP issues |

**Define success criteria:**

Quantitative metrics:
- Skill triggers on 90% of relevant queries (measure: run 10-20 test queries, track auto vs explicit invocation)
- Completes workflow in X tool calls (measure: compare with/without skill, count tool calls and tokens)
- 0 failed API calls per workflow (measure: monitor MCP server logs during test runs)

Qualitative metrics:
- Users don't need to prompt Claude about next steps
- Workflows complete without user correction
- Consistent results across sessions
- New users can accomplish tasks on first try with minimal guidance

### 1.3 Technical Requirements

**File structure:**
```
your-skill-name/
  SKILL.md                  # Required - main skill file
  scripts/                  # Optional - executable code
  references/               # Optional - documentation
  assets/                   # Optional - templates, etc.
```

**Critical rules:**

- **SKILL.md naming**: Must be exactly `SKILL.md` (case-sensitive). No variations (SKILL.MD, skill.md, etc.)
- **Skill folder naming**: Use kebab-case only (`notion-project-setup`). No spaces, no underscores, no capitals.
- **No README.md inside your skill folder**: All documentation goes in SKILL.md or references/. (Note: when distributing via GitHub, you'll still want a repo-level README for human users -- this is separate from the skill folder.)

**YAML frontmatter -- The most important part:**

The YAML frontmatter is how Claude decides whether to load your skill. Get this right.

Minimal required format:
```yaml
---
name: your-skill-name
description: What it does. Use when user asks to [specific phrases].
---
```

**Field requirements:**

`name` (required):
- kebab-case only
- No spaces or capitals
- Should match folder name

`description` (required):
- MUST include BOTH: What the skill does AND When to use it (trigger conditions)
- Under 1024 characters
- No XML tags (< or >)
- Include specific tasks users might say
- Mention file types if relevant

`allowed-tools` (optional):
- Restricts which tools the skill can use (e.g., `Bash(uv:*)`)

`license` (optional):
- Use if making skill open source (MIT, Apache-2.0)

`compatibility` (optional):
- 1-500 characters
- Indicates environment requirements (intended product, required system packages, network access needs)

`metadata` (optional):
- Any custom key-value pairs
- Suggested: author, version, mcp-server

**Security restrictions -- Forbidden in frontmatter:**
- XML angle brackets (< >)
- Skills with "claude" or "anthropic" in name (reserved)
- Why: Frontmatter appears in Claude's system prompt. Malicious content could inject instructions.

### 1.4 Writing Effective Skills

**The description field:**

Formula: `[What it does] + [When to use it] + [Key capabilities]`

Good examples:
```yaml
# Good - specific and actionable
description: Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for "design specs", "component documentation", or "design-to-code handoff".

# Good - includes trigger phrases
description: Manages Linear project workflows including sprint planning, task creation, and status tracking. Use when user mentions "sprint", "Linear tasks", "project planning", or asks to "create tickets".

# Good - clear value proposition
description: End-to-end customer onboarding workflow for PayFlow. Handles account creation, payment setup, and subscription management. Use when user says "onboard new customer", "set up subscription", or "create PayFlow account".
```

Bad examples:
```yaml
# Too vague
description: Helps with projects.

# Missing triggers
description: Creates sophisticated multi-page documentation systems.

# Too technical, no user triggers
description: Implements the Project entity model with hierarchical relationships.
```

**Writing the main instructions (SKILL.md body):**

Recommended structure:
```markdown
---
name: your-skill
description: [...]
---

# Your Skill Name

## Instructions

### Step 1: [First Major Step]
Clear explanation of what happens.

Example:
  ```bash
  python scripts/fetch_data.py --project-id PROJECT_ID
  Expected output: [describe what success looks like]
  ```

### Step 2: [Next Step]
...

## Examples

### Example 1: [common scenario]
User says: "..."
Actions:
1. ...
2. ...
Result: ...

## Troubleshooting

### Error: [Common error message]
Cause: [Why it happens]
Solution: [How to fix]

**Best practices for instructions:**

1. **Be specific and actionable**
   - Good: `Run python scripts/validate.py --input {filename} to check data format. If validation fails, common issues include: Missing required fields (add them to the CSV), Invalid date formats (use YYYY-MM-DD)`
   - Bad: `Validate the data before proceeding.`

2. **Include error handling** -- Provide specific recovery steps for common errors

3. **Reference bundled resources clearly**:
   ```
   Before building queries, consult `references/api-patterns.md` for:
   - Rate limiting guidance
   - Pagination patterns
   - Error codes and handling
   ```

4. **Use progressive disclosure** -- Keep SKILL.md focused on core instructions. Move detailed documentation to `references/` and link to it. Keep SKILL.md under 5,000 words.

### 1.5 Testing and Iteration

**Three testing approaches:**
1. **Manual testing in Claude.ai** -- Run queries directly and observe behavior. Fast iteration, no setup required.
2. **Scripted testing in Claude Code** -- Automate test cases for repeatable validation across changes.
3. **Programmatic testing via skills API** -- Build evaluation suites that run systematically against defined test sets.

**Pro Tip:** Iterate on a single task before expanding. The most effective skill creators iterate on a single challenging task until Claude succeeds, then extract the winning approach into a skill.

**Recommended testing covers three areas:**

**1. Triggering tests** -- Goal: Ensure your skill loads at the right times.
- Should trigger on obvious tasks
- Should trigger on paraphrased requests
- Should NOT trigger on unrelated topics

**2. Functional tests** -- Goal: Verify the skill produces correct outputs.
- Valid outputs generated
- API calls succeed
- Error handling works
- Edge cases covered

**3. Performance comparison** -- Goal: Prove the skill improves results vs. baseline.
- Compare token usage, tool calls, user corrections with vs without skill

**Using the skill-creator skill:**
- Built into Claude.ai and available for Claude Code
- Generate skills from natural language descriptions
- Produces properly formatted SKILL.md with frontmatter
- Suggests trigger phrases and structure
- Reviews skills: flags vague descriptions, missing triggers, structural problems
- Suggests test cases based on skill's stated purpose

**Iteration based on feedback:**

Undertriggering signals:
- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Solution: Add more detail and nuance to the description, include keywords for technical terms

Overtriggering signals:
- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Solution: Add negative triggers, be more specific

### 1.6 Distribution and Sharing

**Current distribution model (January 2026):**

Individual users:
1. Download the skill folder
2. Zip the folder (if needed)
3. Upload to Claude.ai via Settings > Capabilities > Skills
4. Or place in Claude Code skills directory

Organization-level:
- Admins can deploy skills workspace-wide (shipped December 18, 2025)
- Automatic updates
- Centralized management

**Using skills via API:**
- `/v1/skills` endpoint for listing and managing skills
- Add skills to Messages API requests via `container.skills` parameter
- Version control through the Claude Console
- Works with the Claude Agent SDK for building custom agents

**Recommended approach today:**
1. Host on GitHub with public repo
2. Document in your MCP repo (link to skills from MCP docs)
3. Create an installation guide

**Positioning your skill -- Focus on outcomes, not features:**

Good: "The ProjectHub skill enables teams to set up complete project workspaces in seconds -- including pages, databases, and templates -- instead of spending 30 minutes on manual setup."

Bad: "The ProjectHub skill is a folder containing YAML frontmatter and Markdown instructions that calls our MCP server tools."

### 1.7 Patterns and Troubleshooting

**Choosing your approach: Problem-first vs. tool-first**

- **Problem-first**: "I need to set up a project workspace" -> Skill orchestrates the right MCP calls in the right sequence. Users describe outcomes; the skill handles the tools.
- **Tool-first**: "I have Notion MCP connected" -> Skill teaches Claude the optimal workflows and best practices. Users have access; the skill provides expertise.

**Pattern 1: Sequential workflow orchestration**
Use when: Multi-step processes in specific order.
Key techniques: Explicit step ordering, dependencies between steps, validation at each stage, rollback instructions for failures.

**Pattern 2: Multi-MCP coordination**
Use when: Workflows span multiple services.
Key techniques: Clear phase separation, data passing between MCPs, validation before moving to next phase, centralized error handling.

**Pattern 3: Iterative refinement**
Use when: Output quality improves with iteration.
Key techniques: Explicit quality criteria, iterative improvement, validation scripts, know when to stop iterating.

**Pattern 4: Context-aware tool selection**
Use when: Same outcome, different tools depending on context.
Key techniques: Clear decision criteria, fallback options, transparency about choices.

**Pattern 5: Domain-specific intelligence**
Use when: Skill adds specialized knowledge beyond tool access.
Key techniques: Domain expertise embedded in logic, compliance before action, comprehensive documentation, clear governance.

**Troubleshooting guide:**

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Skill won't upload | SKILL.md not named correctly / invalid YAML | Rename to exactly SKILL.md; use --- delimiters; fix YAML syntax |
| Skill never loads automatically | Description too generic or missing triggers | Rewrite description with specific user phrases; include [What]+[When] |
| Skill triggers too often | Description too broad | Add negative triggers; be more specific about scope |
| Skill loads but doesn't follow instructions | Instructions too verbose, buried, or ambiguous | Keep concise; use bullet points; put critical instructions at top; use ## Important headers; be specific not vague |
| Skill seems slow or degraded | Content too large; too many skills enabled | Move docs to references/; keep SKILL.md under 5,000 words; reduce enabled skills |

**Model "laziness" workaround:** Add explicit encouragement:
```markdown
## Performance Notes
- Take your time to do this thoroughly
- Quality is more important than speed
- Do not skip validation steps
```
Note: Adding this to user prompts is more effective than in SKILL.md.

### 1.8 Quick Checklist (Reference A)

**Before you start:**
- [ ] Identified 2-3 concrete use cases
- [ ] Tools identified (built-in or MCP)
- [ ] Reviewed this guide and example skills
- [ ] Planned folder structure

**During development:**
- [ ] Folder named in kebab-case
- [ ] SKILL.md file exists (exact spelling)
- [ ] YAML frontmatter has --- delimiters
- [ ] name field: kebab-case, no spaces, no capitals
- [ ] description includes WHAT and WHEN
- [ ] No XML tags (< >) anywhere
- [ ] Instructions are clear and actionable
- [ ] Error handling included
- [ ] Examples provided
- [ ] References clearly linked

**Before upload:**
- [ ] Tested triggering on obvious tasks
- [ ] Tested triggering on paraphrased requests
- [ ] Verified doesn't trigger on unrelated topics
- [ ] Functional tests pass
- [ ] Tool integration works (if applicable)
- [ ] Compressed as .zip file

**After upload:**
- [ ] Test in real conversations
- [ ] Monitor for under/over-triggering
- [ ] Collect user feedback
- [ ] Iterate on description and instructions
- [ ] Update version in metadata
