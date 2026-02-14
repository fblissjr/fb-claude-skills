last updated: 2026-02-14

# skills guide analysis

Gap analysis comparing the Anthropic skills guide recommendations against what exists in this repo, with actionable findings for the skill-maintainer system.

## gap analysis: guide recommendations vs. repo state

### structure and naming

| Recommendation | plugin-toolkit | skill-maintainer | web-tdd | cogapp-markdown |
|---|---|---|---|---|
| Folder in kebab-case | PASS | PASS | PASS (web-tdd) | PASS |
| SKILL.md exists (exact case) | PASS | PASS | PASS | PASS |
| YAML frontmatter with --- | PASS | PASS | PASS | PASS |
| name matches folder | PASS | PASS | PASS | PASS |
| No README.md in skill folder | N/A (has README at plugin level, not skill level) | PASS | PASS | PASS |
| SKILL.md under 500 lines | ~214 lines: PASS | ~120 lines: PASS | needs check | needs check |

### frontmatter quality

| Recommendation | plugin-toolkit | skill-maintainer |
|---|---|---|
| name: kebab-case | PASS | PASS |
| description includes WHAT | PASS | PASS |
| description includes WHEN (triggers) | PASS | PASS |
| description under 1024 chars | PASS | PASS |
| No XML tags in description | PASS | PASS |
| No "claude"/"anthropic" in name | PASS | PASS |
| metadata field present | missing | PASS (author, version) |
| license field | missing | missing |

### instruction quality

| Recommendation | plugin-toolkit | skill-maintainer |
|---|---|---|
| Specific and actionable steps | PASS | PASS |
| Error handling section | partial (delegates to agents) | N/A (orchestrator) |
| Examples provided | PASS | PASS |
| References linked | PASS | PASS |
| Progressive disclosure used | PASS (4 reference files) | PASS (3 reference files) |
| Under 5000 words | PASS | PASS |

### testing readiness

| Recommendation | Status |
|---|---|
| Triggering test suite defined | not yet |
| Functional tests defined | not yet |
| Performance baseline captured | not yet |

## plugin structure compliance (v0.4.0)

Per the official Claude Code plugin docs, plugin manifests belong at `.claude-plugin/plugin.json` (not `plugin.json` at root). Multi-plugin repos should expose a `.claude-plugin/marketplace.json` at the repo root.

| Requirement | Status |
|---|---|
| Manifests at `.claude-plugin/plugin.json` | PASS (migrated in v0.4.0) |
| Root `marketplace.json` for distribution | PASS (created in v0.4.0) |
| No non-standard fields in manifests | PASS (removed `skills`/`agents` arrays, auto-discovery handles these) |
| `repository` field in manifests | PASS (added in v0.4.0) |
| Installation docs use correct CLI commands | PASS (fixed in v0.4.0) |
| config.yaml watches discover-plugins + plugin-marketplaces pages | PASS (added in v0.4.0) |

## actionable findings for skill-maintainer

### high priority

1. **Add metadata.version to plugin-toolkit**: The guide recommends `metadata` with `author` and `version`. plugin-toolkit is missing this. The skill-maintainer should detect and suggest adding it.

2. ~~**web-tdd has README.md in skill folder**~~: RESOLVED -- README.md removed from skill folder.

3. **No license field on any skill**: For open-source distribution, the guide recommends including `license: MIT` or similar. Should be flagged but not auto-added (requires user decision).

### medium priority

4. **No testing infrastructure**: The guide recommends trigger tests, functional tests, and performance baselines. The skill-maintainer should provide templates or scripts for testing.

5. **cogapp-markdown lacks trigger phrases**: Its description should include phrases users would say to trigger it (e.g., "keep docs in sync", "auto-generate markdown").

6. **No negative triggers**: The guide recommends adding "Do NOT use for..." to prevent overtriggering. None of the skills have negative triggers.

### low priority

7. **No compatibility field**: Could be useful for skills that require specific environments (e.g., cogapp-markdown requires Python + cogapp).

8. **No asset directory used**: The guide mentions an `assets/` directory for templates. Not currently needed but good to know the pattern exists.

## best practices checklist (machine-parseable)

Extracted from the guide for use by the skill-maintainer validation system. See `skill-maintainer/references/best_practices.md` for the complete machine-parseable version.

### critical (must have)

```yaml
checks:
  - id: skill-md-exists
    description: SKILL.md file exists with exact case
    severity: error

  - id: frontmatter-delimiters
    description: YAML frontmatter wrapped in --- markers
    severity: error

  - id: name-kebab-case
    description: name field uses kebab-case (lowercase, hyphens only)
    severity: error

  - id: name-matches-folder
    description: name field matches containing folder name
    severity: error

  - id: description-present
    description: description field is non-empty
    severity: error

  - id: description-no-xml
    description: description contains no angle brackets
    severity: error

  - id: name-no-reserved
    description: name does not contain "claude" or "anthropic"
    severity: error
```

### recommended (should have)

```yaml
checks:
  - id: description-has-what
    description: description explains what the skill does
    severity: warning

  - id: description-has-when
    description: description includes trigger conditions
    severity: warning

  - id: description-under-1024
    description: description under 1024 characters
    severity: warning

  - id: skill-md-under-500-lines
    description: SKILL.md under 500 lines
    severity: warning

  - id: skill-md-under-5000-words
    description: SKILL.md under 5000 words
    severity: warning

  - id: no-readme-in-skill
    description: no README.md inside skill directory
    severity: warning

  - id: references-linked
    description: all files in references/ are linked from SKILL.md
    severity: warning

  - id: instructions-specific
    description: instructions include specific commands/actions
    severity: warning

  - id: error-handling-present
    description: error handling or troubleshooting section exists
    severity: warning
```

## what to incorporate into skill-maintainer

1. The `validate_skill.py` script already implements most critical checks via skills-ref. Add the "recommended" checks as warnings.

2. The `best_practices.md` reference file should be kept in sync with the guide. When the guide PDF changes (detected by hash), regenerate this analysis.

3. The description quality heuristics (WHAT + WHEN pattern) should be part of the validation warnings.

4. The "no README.md in skill folder" check is not in skills-ref but should be in our extended validation.

5. The testing infrastructure gap should be addressed in a future phase - the skill-maintainer could generate test templates.
