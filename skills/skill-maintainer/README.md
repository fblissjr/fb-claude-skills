last updated: 2026-11-04

# skill-maintainer

Maintenance for a skills repo. `/maintain` runs the maintenance pass:
- pull tracked sources and upstream docs;
- check quality;
- audit controls and sample mutations on recently changed subjects.

`/sync-versions` bumps a plugin's version everywhere it lives. The checks themselves are the `skill-maintain` CLI in this repo's `tools/skill-maintainer/`, which the plugin does not ship.

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
| `maintain` | `/skill-maintainer:maintain` | Full maintenance pass: source pulls, upstream checks, quality report, controls audit, mutation sample |
| `sync-versions` | `/skill-maintainer:sync-versions <plugin> <ver>` | Bump a plugin's version across `plugin.json`, `marketplace.json`, and `pyproject.toml` where one ships. A major bump waits for your confirmation |

## usage examples

```
# full maintenance pass (sources + upstream + quality + controls + mutation sample)
/skill-maintainer:maintain

# bump path-privacy's version everywhere it lives
/skill-maintainer:sync-versions path-privacy 0.7.4
```

## relationship to the CLI package

The `skill-maintain` CLI (`tools/skill-maintainer/`) holds the checks: `validate`, `test`, `quality`, `upstream`, `sources`, `lint` and `init`. Install it with `uv tool install ./tools/skill-maintainer` from a clone of this repo. `/maintain` uses it when it is on the PATH and falls back to equivalent manual checks when it is not.

## authoring rules

This repo's house rules for writing skills and plugins live in its own
`.claude/rules/` (`skills.md`, `plugins.md`, `controls.md`), which Claude Code
loads when a matching file is read. They are not shipped with the plugin.
`best_practices.md` was retired on 2026-11-04: nothing read it while a skill was
being written, and its platform half restated Claude Code's docs.
