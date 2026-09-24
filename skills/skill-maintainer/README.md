last updated: 2026-09-24

# skill-maintainer

Keeps a skills repo's rules current. `/maintain` runs the maintenance pass:
- pull tracked sources and upstream docs;
- check quality;
- review `references/best_practices.md` against what moved, proposing changes for your approval.

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
| `maintain` | `/skill-maintainer:maintain` | Full maintenance pass: source pulls, upstream checks, quality report, controls audit, mutation sample, best practices review. The one stop is your approval before `best_practices.md` changes |
| `sync-versions` | `/skill-maintainer:sync-versions <plugin> <ver>` | Bump a plugin's version across `plugin.json`, `marketplace.json`, and `pyproject.toml` where one ships. A major bump waits for your confirmation |

## usage examples

```
# full maintenance pass (sources + upstream + quality + best practices review)
/skill-maintainer:maintain

# bump path-privacy's version everywhere it lives
/skill-maintainer:sync-versions path-privacy 0.7.4
```

## relationship to the CLI package

The `skill-maintain` CLI (`tools/skill-maintainer/`) holds the checks: `validate`, `test`, `quality`, `upstream`, `sources`, `lint` and `init`. Install it with `uv tool install ./tools/skill-maintainer` from a clone of this repo. `/maintain` uses it when it is on the PATH and falls back to equivalent manual checks when it is not.

## references

- `references/best_practices.md` -- portable best practices for building skills and plugins for Claude, in three parts: constraints (what must not happen), gates (each naming the command that measures it), and reference (lookup tables). Read by the `/maintain` skill's review phase and by authors directly; **not** parsed by any code. Each section states its evidence class and what enforces it, and "nothing" is a common and deliberate answer -- the hook and agent constraints have no mechanical check anywhere
