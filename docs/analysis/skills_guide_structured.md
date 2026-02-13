last updated: 2026-02-13

# skills guide structured reference

Structured markdown extraction from "The Complete Guide to Building Skills for Claude" (Anthropic, January 2026). All content preserved verbatim from the PDF. Used as ground truth for change detection.

## chapter 1: fundamentals

### what is a skill?

A skill is a folder containing:

- **SKILL.md** (required): Instructions in Markdown with YAML frontmatter
- **scripts/** (optional): Executable code (Python, Bash, etc.)
- **references/** (optional): Documentation loaded as needed
- **assets/** (optional): Templates, fonts, icons used in output

### core design principles

#### progressive disclosure

Skills use a three-level system:

1. **First level (YAML frontmatter)**: Always loaded in Claude's system prompt. Provides just enough information for Claude to know when each skill should be used without loading all of it into context.
2. **Second level (SKILL.md body)**: Loaded when Claude thinks the skill is relevant to the current task. Contains the full instructions and guidance.
3. **Third level (Linked files)**: Additional files bundled within the skill directory that Claude can choose to navigate and discover only as needed.

This progressive disclosure minimizes token usage while maintaining specialized expertise.

#### composability

Claude can load multiple skills simultaneously. Your skill should work well alongside others, not assume it's the only capability available.

#### portability

Skills work identically across Claude.ai, Claude Code, and API. Create a skill once and it works across all surfaces without modification, provided the environment supports any dependencies the skill requires.

### mcp + skills relationship

| MCP (Connectivity) | Skills (Knowledge) |
|---|---|
| Connects Claude to your service (Notion, Asana, Linear, etc.) | Teaches Claude how to use your service effectively |
| Provides real-time data access and tool invocation | Captures workflows and best practices |
| What Claude can do | How Claude should do it |

## chapter 2: planning and design

### start with use cases

Before writing any code, identify 2-3 concrete use cases your skill should enable.

Good use case definition:

```
Use Case: Project Sprint Planning
Trigger: User says "help me plan this sprint" or "create sprint tasks"
Steps:
1. Fetch current project status from Linear (via MCP)
2. Analyze team velocity and capacity
3. Suggest task prioritization
4. Create tasks in Linear with proper labels and estimates
Result: Fully planned sprint with tasks created
```

Ask yourself:
- What does a user want to accomplish?
- What multi-step workflows does this require?
- Which tools are needed (built-in or MCP?)
- What domain knowledge or best practices should be embedded?

### common skill use case categories

#### category 1: document and asset creation
Used for: Creating consistent, high-quality output including documents, presentations, apps, designs, code, etc.

Key techniques:
- Embedded style guides and brand standards
- Template structures for consistent output
- Quality checklists before finalizing
- No external tools required - uses Claude's built-in capabilities

#### category 2: workflow automation
Used for: Multi-step processes that benefit from consistent methodology, including coordination across multiple MCP servers.

Key techniques:
- Step-by-step workflow with validation gates
- Templates for common structures
- Built-in review and improvement suggestions
- Iterative refinement loops

#### category 3: mcp enhancement
Used for: Workflow guidance to enhance the tool access an MCP server provides.

Key techniques:
- Coordinates multiple MCP calls in sequence
- Embeds domain expertise
- Provides context users would otherwise need to specify
- Error handling for common MCP issues

### define success criteria

#### quantitative metrics
- Skill triggers on 90% of relevant queries
  - How to measure: Run 10-20 test queries. Track how many times it loads automatically vs. requires explicit invocation.
- Completes workflow in X tool calls
  - How to measure: Compare the same task with and without the skill enabled. Count tool calls and total tokens consumed.
- 0 failed API calls per workflow
  - How to measure: Monitor MCP server logs during test runs. Track retry rates and error codes.

#### qualitative metrics
- Users don't need to prompt Claude about next steps
- Workflows complete without user correction
- Consistent results across sessions
- Can a new user accomplish the task on first try with minimal guidance?

### technical requirements

#### file structure

```
your-skill-name/
  SKILL.md                  # Required - main skill file
  scripts/                  # Optional - executable code
    process_data.py         # Example
    validate.sh             # Example
  references/               # Optional - documentation
    api-guide.md            # Example
    examples/               # Example
  assets/                   # Optional - templates, etc.
    report-template.md      # Example
```

#### critical rules

**SKILL.md naming:**
- Must be exactly `SKILL.md` (case-sensitive)
- No variations accepted (SKILL.MD, skill.md, etc.)

**Skill folder naming:**
- Use kebab-case: `notion-project-setup`
- No spaces: ~~`Notion Project Setup`~~
- No underscores: ~~`notion_project_setup`~~
- No capitals: ~~`NotionProjectSetup`~~

**No README.md:**
- Don't include README.md inside your skill folder
- All documentation goes in SKILL.md or references/
- Note: when distributing via GitHub, you'll still want a repo-level README

### yaml frontmatter

The YAML frontmatter is how Claude decides whether to load your skill. Get this right.

#### minimal required format

```yaml
---
name: your-skill-name
description: What it does. Use when user asks to [specific phrases].
---
```

#### field requirements

**name** (required):
- kebab-case only
- No spaces or capitals
- Should match folder name

**description** (required):
- MUST include BOTH: what the skill does AND when to use it (trigger conditions)
- Under 1024 characters
- No XML tags (< or >)
- Include specific tasks users might say
- Mention file types if relevant

**license** (optional):
- Use if making skill open source
- Common: MIT, Apache-2.0

**compatibility** (optional):
- 1-500 characters
- Indicates environment requirements: intended product, required system packages, network access needs, etc.

**metadata** (optional):
- Any custom key-value pairs
- Suggested: author, version, mcp-server
- Example: `metadata: { author: ProjectHub, version: 1.0.0, mcp-server: projecthub }`

#### security restrictions

Forbidden in frontmatter:
- XML angle brackets (< >)
- Skills with "claude" or "anthropic" in name (reserved)

Why: Frontmatter appears in Claude's system prompt. Malicious content could inject instructions.

### writing effective skills

#### the description field

Structure: `[What it does] + [When to use it] + [Key capabilities]`

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

### writing the main instructions

Recommended structure template:
```markdown
---
name: your-skill
description: [...]
---

# Your Skill Name

## Instructions

### Step 1: [First Major Step]
Clear explanation of what happens.
```

#### best practices for instructions

Be Specific and Actionable:
```
# Good:
Run `python scripts/validate.py --input {filename}` to check data format.
If validation fails, common issues include:
- Missing required fields (add them to the CSV)
- Invalid date formats (use YYYY-MM-DD)

# Bad:
Validate the data before proceeding.
```

Include error handling:
```markdown
## Common Issues

### MCP Connection Failed
If you see "Connection refused":
1. Verify MCP server is running: Check Settings > Extensions
2. Confirm API key is valid
3. Try reconnecting: Settings > Extensions > [Your Service] > Reconnect
```

Reference bundled resources clearly:
```markdown
Before writing queries, consult `references/api-patterns.md` for:
- Rate limiting guidance
- Pagination patterns
- Error codes and handling
```

Use progressive disclosure: Keep SKILL.md focused on core instructions. Move detailed documentation to `references/` and link to it.

## chapter 3: testing and iteration

### testing approaches

- **Manual testing in Claude.ai** - Run queries directly and observe behavior. Fast iteration, no setup required.
- **Scripted testing in Claude Code** - Automate test cases for repeatable validation across changes.
- **Programmatic testing via skills API** - Build evaluation suites that run systematically against defined test sets.

Pro Tip: Iterate on a single task before expanding. The most effective skill creators iterate on a single challenging task until Claude succeeds, then extract the winning approach into a skill.

### recommended testing approach

#### 1. triggering tests

Goal: Ensure your skill loads at the right times.

Test cases:
- Triggers on obvious tasks
- Triggers on paraphrased requests
- Doesn't trigger on unrelated topics

#### 2. functional tests

Goal: Verify the skill produces correct outputs.

Test cases:
- Valid outputs generated
- API calls succeed
- Error handling works
- Edge cases covered

#### 3. performance comparison

Goal: Prove the skill improves results vs. baseline.

Compare with and without the skill:
- Token consumption
- Number of back-and-forth messages
- Failed API calls
- User corrections needed

### using the skill-creator skill

The skill-creator skill - available in Claude.ai via plugin directory or download for Claude Code - can help you build and iterate on skills.

Creating skills: Generate skills from natural language descriptions, produce properly formatted SKILL.md with frontmatter, suggest trigger phrases and structure.

Reviewing skills: Flag common issues (vague descriptions, missing triggers, structural problems), identify potential over/under-triggering risks, suggest test cases.

### iteration based on feedback

Skills are living documents. Plan to iterate based on:

**Undertriggering signals:**
- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Solution: Add more detail and nuance to the description, including keywords particularly for technical terms

**Overtriggering signals:**
- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Solution: Add negative triggers, be more specific

## chapter 4: distribution and sharing

### current distribution model (january 2026)

How individual users get skills:
1. Download the skill folder
2. Zip the folder (if needed)
3. Upload to Claude.ai via Settings > Capabilities > Skills
4. Or place in Claude Code skills directory

Organization-level skills:
- Admins can deploy skills workspace-wide (shipped December 18, 2025)
- Automatic updates
- Centralized management

### agent skills: an open standard

Anthropic published Agent Skills as an open standard. Like MCP, skills should be portable across tools and platforms - the same skill should work whether you're using Claude or other AI platforms. Authors can note platform-specific features in the `compatibility` field.

### using skills via api

Key capabilities:
- `/v1/skills` endpoint for listing and managing skills
- Add skills to Messages API requests via the `container.skills` parameter
- Version control and management through the Claude Console
- Works with the Claude Agent SDK for building custom agents

When to use API vs. Claude.ai:
| Use Case | Best Surface |
|---|---|
| End users interacting with skills directly | Claude.ai / Claude Code |
| Manual testing and iteration during development | Claude.ai / Claude Code |
| Individual, ad-hoc workflows | Claude.ai / Claude Code |
| Applications using skills programmatically | API |
| Production deployments at scale | API |
| Automated pipelines and agent systems | API |

### recommended approach today

Start by hosting your skill on GitHub with a public repo, clear README, and example usage with screenshots. Then add a section to your MCP documentation that links to the skill, explains why using both is valuable, and provides a quick-start guide.

### positioning your skill

Focus on outcomes, not features:
```
# Good:
"The ProjectHub skill enables teams to set up complete project
workspaces in seconds -- including pages, databases, and
templates -- instead of spending 30 minutes on manual setup."

# Bad:
"The ProjectHub skill is a folder containing YAML frontmatter
and Markdown instructions that calls our MCP server tools."
```

## chapter 5: patterns and troubleshooting

### choosing your approach: problem-first vs. tool-first

- **Problem-first**: "I need to set up a project workspace" -> Your skill orchestrates the right MCP calls in the right sequence. Users describe outcomes; the skill handles the tools.
- **Tool-first**: "I have Notion MCP connected" -> Your skill teaches Claude the optimal workflows and best practices. Users have access; the skill provides expertise.

### pattern 1: sequential workflow orchestration

Use when: Multi-step processes in a specific order.

Key techniques: Explicit step ordering, dependencies between steps, validation at each stage, rollback instructions for failures.

### pattern 2: multi-mcp coordination

Use when: Workflows span multiple services.

Key techniques: Clear phase separation, data passing between MCPs, validation before moving to next phase, centralized error handling.

### pattern 3: iterative refinement

Use when: Output quality improves with iteration.

Key techniques: Explicit quality criteria, iterative improvement, validation scripts, know when to stop iterating.

### pattern 4: context-aware tool selection

Use when: Same outcome, different tools depending on context.

Key techniques: Clear decision criteria, fallback options, transparency about choices.

### pattern 5: domain-specific intelligence

Use when: Your skill adds specialized knowledge beyond tool access.

Key techniques: Domain expertise embedded in logic, compliance before action, comprehensive documentation, clear governance.

### troubleshooting

#### skill won't upload
- "Could not find SKILL.md in uploaded folder": Rename to exactly SKILL.md (case-sensitive)
- "Invalid frontmatter": Check for `---` delimiters, proper YAML formatting
- "Invalid skill name": Name has spaces or capitals, use kebab-case

#### skill doesn't trigger
- Symptom: Skill never loads automatically
- Fix: Revise description field - is it too generic? Does it include trigger phrases users would actually say? Does it mention relevant file types?
- Debugging approach: Ask Claude "When would you use the [skill name] skill?" and adjust based on what's missing.

#### skill triggers too often
- Solutions: Add negative triggers, be more specific, clarify scope

#### instructions not followed
1. Instructions too verbose - keep concise, use bullet points, move detailed reference to separate files
2. Instructions buried - put critical instructions at the top, use ## Important or ## Critical headers
3. Ambiguous language - be explicit and specific
4. Model "laziness" - add explicit encouragement in user prompts (not SKILL.md)

#### large context issues
- Optimize SKILL.md size: move detailed docs to references/, link instead of inline, keep under 5,000 words
- Reduce enabled skills: evaluate if you have more than 20-50 simultaneously, recommend selective enablement, consider skill "packs"

## chapter 6: resources and references

### official documentation
- Best Practices Guide
- Skills Documentation
- API Reference
- MCP Documentation

### blog posts
- Introducing Agent Skills
- Engineering Blog: Equipping Agents for the Real World
- Skills Explained
- How to Create Skills for Claude
- Building Skills for Claude Code
- Improving Frontend Design through Skills

### example skills
- Public skills repository: GitHub: anthropics/skills
- Contains Anthropic-created skills you can customize

### tools and utilities
- skill-creator skill: Built into Claude.ai and available for Claude Code. Generates skills from descriptions, reviews and provides recommendations.
- Validation: skill-creator can assess your skills. Ask: "Review this skill and suggest improvements"

### reference a: quick checklist

#### before you start
- [ ] Identified 2-3 concrete use cases
- [ ] Tools identified (built-in or MCP)
- [ ] Reviewed this guide and example skills
- [ ] Planned folder structure

#### during development
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

#### before upload
- [ ] Tested triggering on obvious tasks
- [ ] Tested triggering on paraphrased requests
- [ ] Verified doesn't trigger on unrelated topics
- [ ] Functional tests pass
- [ ] Tool integration works (if applicable)
- [ ] Compressed as .zip file

#### after upload
- [ ] Test in real conversations
- [ ] Monitor for under/over-triggering
- [ ] Collect user feedback
- [ ] Iterate on description and instructions
- [ ] Update version in metadata

---

content hash: (computed at check time by docs_monitor.py)
