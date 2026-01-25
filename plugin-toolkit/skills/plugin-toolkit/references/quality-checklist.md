# Plugin Quality Checklist

Use this checklist when evaluating Claude Code plugins.

---

## Metadata (plugin.json)

- [ ] `name` is descriptive and kebab-case
- [ ] `version` follows semver (x.y.z)
- [ ] `description` clearly explains purpose
- [ ] `author` information present
- [ ] `skills` array lists all skills
- [ ] `agents` array lists all agents (if any)
- [ ] `hooks` path is correct (if using hooks)

---

## Commands

### Consistency

- [ ] All commands use same YAML frontmatter format
- [ ] All commands have `description` field
- [ ] Argument hints provided where helpful
- [ ] Consistent naming convention (kebab-case)
- [ ] No duplicate functionality between commands

### Coverage

- [ ] Core functionality has commands
- [ ] `/help` command exists for discoverability
- [ ] `/status` command exists (if stateful)
- [ ] `/off` and `/on` commands exist (if auto-activating)

### Quality

- [ ] Commands are focused (single responsibility)
- [ ] Commands have clear documentation
- [ ] Examples provided for complex commands
- [ ] Edge cases handled

---

## Hooks

### Implementation

- [ ] Hooks registered in hooks.json
- [ ] Hook scripts are executable
- [ ] Scripts use `set -e` for error handling
- [ ] Scripts handle missing dependencies gracefully

### User Experience

- [ ] Opt-out mechanism exists for auto-activation
- [ ] Hooks don't break on unexpected input
- [ ] Token overhead is reasonable
- [ ] Matcher patterns are appropriate (not overly broad)

---

## Skills

### SKILL.md Quality

- [ ] Clear, trigger-friendly description
- [ ] Covers primary use cases
- [ ] References to detailed docs where needed
- [ ] Examples of usage

### Organization

- [ ] References folder for detailed docs
- [ ] Logical structure
- [ ] No orphaned files

---

## Agents

- [ ] Each agent has clear purpose
- [ ] Agents are reusable across skills
- [ ] Agent files follow naming convention
- [ ] Agents are documented in plugin.json

---

## Documentation

### Required

- [ ] README.md with quick start
- [ ] CHANGELOG.md with version history
- [ ] License file

### Quality

- [ ] Installation instructions clear
- [ ] Usage examples provided
- [ ] All features documented
- [ ] No stale documentation

---

## Code Quality

### Shell Scripts

- [ ] Use `set -e` for error handling
- [ ] Variables quoted properly
- [ ] Portable across bash/zsh
- [ ] No hardcoded paths

### File Organization

- [ ] No duplicate content between files
- [ ] Traits and commands don't duplicate
- [ ] Clear separation of concerns

---

## Integration

- [ ] Works with other plugins
- [ ] Doesn't conflict with common plugins
- [ ] Integration patterns documented

---

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 9-10 | Excellent - production ready |
| 7-8 | Good - minor improvements needed |
| 5-6 | Adequate - functional but rough edges |
| 3-4 | Needs work - significant issues |
| 1-2 | Poor - fundamental problems |

### Category Weights

| Category | Weight |
|----------|--------|
| Commands | 25% |
| Hooks | 20% |
| Documentation | 20% |
| Skills/Agents | 15% |
| Code Quality | 10% |
| Integration | 10% |
