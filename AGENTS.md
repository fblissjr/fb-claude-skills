last updated: 2026-09-24

# fb-claude-skills

Claude Code plugin marketplace: skills, agents, hooks, MCP servers and MCP Apps,
bundled as installable plugins. Principles: [VISION.md](VISION.md). Layout,
plugin table, install: [README.md](README.md). Every other doc:
[docs/README.md](docs/README.md).

## Commands

```bash
uv sync --all-packages                          # setup from a fresh clone
uv run skill-maintain validate                  # SKILL.md frontmatter, Claude Code schema
uv run skill-maintain test                      # repo gates: token budget, hygiene, path audit
claude plugin validate <plugin-dir> --strict    # per plugin, not only the marketplace root
claude plugin eval <plugin-dir>                 # behaviour, with and without the plugin; suites and run notes: evals/README.md
uv run skill-maintain upstream                  # current Claude Code docs into .skill-maintainer/state/pages/
```

A plugin change is done when `validate` and `test` pass and invariant 1's
cascade is complete.

## Invariants

Other documents cite these by number. Remove an entry; never renumber.

**1. Plugin content change triggers a version cascade:** `plugin.json`, the root
`marketplace.json`, and a `CHANGELOG.md` entry. Add `tools/<plugin>/pyproject.toml`
only when the marketplace `source` ships `tools/`. Plugin content is what `source`
ships *and* changes an installed session: a SKILL.md body, a `references/` file a
skill reads, a hook script. SKILL.md frontmatter, a plugin's own CLAUDE.md, and its
`evals/` are not. Never add `metadata.version`, `metadata.author`, `metadata.last_verified` or
`metadata.review_interval_days` to a SKILL.md. The root `pyproject.toml` has no
version. Detail: [plugin-versioning.md](docs/internals/plugin-versioning.md).

**1b. One changelog, at the repo root.** A copy of anything earns its place only
if something other than the check confirming it is a copy reads it. Otherwise
delete it.

**1c. A rule earns its tier.** Mechanically detectable violation: a `PreToolUse`
block. Detectable condition: a `PostToolUse` notice. Neither: one ambient line
pointing at a skill. Cost is emission, and `SessionStart` emits again on resume,
fork, clear and compact. On each model release, delete rules that compensate
for limits the model no longer has. Measure with `/doctor`, `/skill-doctor`,
`claude plugin details` and `/context`; do not build counters that duplicate them.
Detail: [context-cost.md](docs/internals/context-cost.md).

**2. Every path in repo content is repo-relative, and the git `user.name` full
name never appears** (the GitHub handle and email are fine), including commit
messages and branch names. The path-privacy PreToolUse hook rewrites in-repo
absolute paths to repo-relative on Edit/Write and blocks external paths and the
name; the git hooks hard-block both at commit. Never `--no-verify`. Generic tool
locations (`~/.claude/...`, `$HOME/.config/...`) are not leaks; a named
directory under home is. `skill-maintain test` catches in-repo absolute paths
written any other way.

**3. `best_practices.md` has one copy:**
`skills/skill-maintainer/references/best_practices.md`, which `/maintain` reads
here and in every install. Editing it triggers invariant 1.

## Session end

Update `internal/log/log_YYYY-MM-DD.md`, the README and `pyproject.toml` of each
unit you touched, and this file only if a repo-wide rule changed.

## Where to look first

| Working on | Read |
|---|---|
| A plugin's structure, hooks, agents | [plugin-patterns.md](docs/internals/plugin-patterns.md), then [gotchas.md](docs/internals/gotchas.md) |
| A unit with a design record or postmortem | find it in [docs/README.md](docs/README.md) before changing the unit's shape |
| Which tier a rule belongs in | [context-cost.md](docs/internals/context-cost.md) |
| Upstream drift | [maintenance.md](docs/internals/maintenance.md), [upstream_drift_backlog.md](docs/internals/upstream_drift_backlog.md) |
| `apps/readwise-reader` | its own `CLAUDE.md` |
