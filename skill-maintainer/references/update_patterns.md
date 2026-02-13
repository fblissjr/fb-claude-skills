last updated: 2026-02-13

# update patterns

How to apply different types of changes detected by the monitoring system.

## change classification

### breaking changes
- **examples**: Required field removed/renamed, validation rule tightened, API endpoint changed
- **action**: Flag for human review. Never auto-apply.
- **in report**: Marked with `BREAKING` label, appears first

### additive changes
- **examples**: New optional field added, new feature documented, new pattern recommended
- **action**: Can be auto-applied if change is well-understood. Default: report + suggest.
- **in report**: Marked with `ADDITIVE` label

### cosmetic changes
- **examples**: Typo fix in docs, reformatting, reworded explanation
- **action**: Usually ignore unless it changes meaning. Report only.
- **in report**: Marked with `COSMETIC` label

## update types

### frontmatter field changes
- **trigger**: New field added to spec, field renamed, validation rule changed
- **automated patch**: Parse current frontmatter, apply change, re-serialize
- **validation**: Run skills-ref validate after patch
- **example**: If spec adds a new required field `compatibility`, patch all skills to include it

### description best practice changes
- **trigger**: New guidance on description structure, trigger phrases, length recommendations
- **Claude-assisted**: Generate prompt with old description + new guidelines, ask for rewrite
- **validation**: Check new description against best_practices.md checklist
- **example**: If guide now recommends including file types in description, suggest edits

### api/spec field changes
- **trigger**: Validation limits changed (max name length, allowed characters)
- **automated check**: Run validator, see if existing skills still pass
- **if pass**: No action needed, just note in report
- **if fail**: Generate fix suggestion, flag for review

### documentation pattern changes
- **trigger**: New recommended skill structure, new testing approach, new distribution method
- **action**: Update references/best_practices.md, note in report
- **no auto-apply to skills**: These are informational updates

### upstream code changes (source repos)
- **trigger**: Commits to watched files in monitored repos
- **analysis**: Extract changed APIs, check for deprecations
- **action**: Update reference docs if skill references those APIs
- **breaking detection**: Keyword scan of commit messages + AST comparison

## apply modes

### report-only
1. Collect all changes from monitors
2. Classify each change
3. Generate markdown report
4. Write to stdout / file
5. No file modifications

### apply-local (default)
1. Generate report (as above)
2. For each applicable change:
   a. Create backup of affected file
   b. Apply patch or generate edit suggestion
   c. Validate with skills-ref
   d. If validation fails, revert and report failure
3. User reviews git diff and commits manually

### create-pr (ci mode)
1. Generate report (as above)
2. Apply changes (as above)
3. Create git branch: `skill-maintenance/YYYY-MM-DD`
4. Commit changes with structured message
5. Create PR with change report as body
6. Run validation in CI

## validation workflow

Every update, regardless of mode, runs this validation:

1. `skills-ref validate <skill-path>` - Structural validation
2. Check against best_practices.md checklist - Best practice conformance
3. Verify no regressions in other tracked skills
4. Report any validation failures prominently
