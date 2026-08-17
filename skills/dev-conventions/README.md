last updated: 2026-08-17

# dev-conventions

Three on-demand references. Each carries only what a repo cannot state by being
read — a house preference, a structural choice, or a failure that reliably gets
misdiagnosed. Everything that was already default behaviour has been removed.

**No hooks, no ambient injection.** Earlier versions shipped a PreToolUse hook
that blocked `pip` in uv projects and a SessionStart hook that injected
convention prose. Both were retired in 0.17.0: across 4,700 transcripts, every
denial that could be identified was either a command *searching* for the banned
string or a deliberate test of the hook itself — never an attempt to run the
banned command. Conventions belong in a repo's own always-loaded files, where
they also reach collaborators who never installed a plugin.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install dev-conventions@fb-claude-skills
```

For development without installing:

```bash
claude --plugin-dir ./skills/dev-conventions
```

## skills

| Skill | Invocation | What it carries |
|-------|------------|-----------------|
| `python-tooling` | `/dev-conventions:python-tooling` | The house pinning policy (apps exact, libraries floors), the two mechanical mistakes behind most Pydantic/Pyright diagnostic walls, Pyright config precedence, and the one behavioural override worth stating: do not auto-run linters, formatters, or tests after an edit unless asked |
| `doc-conventions` | `/dev-conventions:doc-conventions` | Last-updated dates, where unshared notes and session logs live, the dependency-change record format, and the rule against decorative counts in prose |
| `dep-audit` | `/dev-conventions:dep-audit` | That `uv` and `bun` both ship a native CVE audit subcommand at all — without which the reflex is `pip-audit` or `safety` — plus reachability-before-upgrade and report-the-delta |
| `doc-architecture` | `/dev-conventions:doc-architecture` | Where a project's writing lives: a slow-clock home for principles, and `CLAUDE.md` shaped as a routing index rather than an accumulating pile. Creates the slot and the criteria for what earns a line in it; ships no principles of its own |

## invocation examples

```
/dev-conventions:python-tooling
/dev-conventions:doc-conventions
/dev-conventions:dep-audit
/dev-conventions:doc-architecture
```

They also load on their own phrasing — "pyright reports a wall of errors",
"update the README", "session log", "numbers in prose", "check for CVEs",
"is this dependency safe", "vulnerability scan".

## what is deliberately not here

Lowercase filenames, organising docs into subfolders, "explain the why not just
the what", and the uv-over-pip and bun-over-npm preferences themselves. The
first three are already default behaviour; the last two are visible from a
`uv.lock` or `bun.lock` sitting in the repo. Restating any of them costs context
to change nothing.

Per-repo scaffolding is also gone. `/dev-conventions:init` wrote conventions
into a repo's own files and `/dev-conventions:configure` managed a
`.dev-conventions.json` read only by the retired hooks; both went with them.
Write the conventions into `CLAUDE.md` or `.claude/rules/` directly.
