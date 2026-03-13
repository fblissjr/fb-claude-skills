last updated: 2026-03-13

# skill-maintainer

Maintenance tools for any Claude Code skills repo. Validates skills against the Agent Skills spec, checks token budgets, tracks freshness, detects upstream doc changes, and reviews best practices.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install skill-maintainer@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/skills/skill-maintainer
```

## skills

| Skill | Invocation | What it does |
|-------|------------|--------------|
| `maintain` | `/skill-maintainer:maintain` | Full maintenance pass: upstream checks, source pulls, quality report, best practices review |
| `quality` | `/skill-maintainer:quality` | Quick quality check: spec compliance, token budget, freshness, description quality |
| `init-maintenance` | `/skill-maintainer:init-maintenance` | Set up persistent maintenance config and state in a repo |
| `sync-versions` | `/skill-maintainer:sync-versions <plugin> <ver>` | Bump a plugin's version across all sources atomically |

## usage examples

```
# quick health check on all skills in the repo
/skill-maintainer:quality

# full maintenance pass (upstream + sources + quality + best practices review)
/skill-maintainer:maintain

# set up maintenance config in a new skills repo
/skill-maintainer:init-maintenance

# bump tui-design to 0.3.0 across plugin.json, marketplace, SKILL.md, pyproject
/skill-maintainer:sync-versions tui-design 0.3.0
```

## relationship to the CLI package

The `skill-maintainer` Python package at `tools/skill-maintainer/` provides the `skill-maintain` CLI for CI/headless use. This plugin is the primary interface for interactive use within Claude Code -- it embeds the same knowledge (thresholds, rules, checks) directly in the skills so no Python package installation is required. If the CLI is available, the `/maintain` skill will use it for upstream and source checks; otherwise it performs equivalent checks using WebFetch and Bash.

## references

- `references/best_practices.md` -- machine-parseable checklist used by the quality checks
