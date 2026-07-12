# pyright-autoconfig

Last updated: 2026-07-12

A one-hook plugin that makes the Claude Code **Pyright LSP** quiet and useful in
every Python project, on every machine, without per-repo setup.

## The problem

The official `pyright-lsp` plugin is a thin launcher (`pyright-langserver
--stdio`). Pyright has **no global/user config file by design** — its settings
are strictly per-project (`pyrightconfig.json` or `[tool.pyright]` in
`pyproject.toml`, resolved by walking up from each file). So with no per-project
config:

- Pyright can't reliably find the `uv` `.venv`, so **every** import fails with
  `reportMissingImports` — a wall of red on every file edit.
- Claude Code surfaces **all** diagnostic severities back into the model's
  context, so that wall is injected into the session every time, burying the
  genuinely useful diagnostics (real type errors, arg-type mismatches).
- It's worst on files Pyright can't root: sibling repos you edit from another
  repo's session, and scratch dirs under `/tmp`.

There is no Claude Code-level severity filter (only an all-or-nothing
`"diagnostics": false`), so the fix has to live in Pyright's own per-project
config — which means materializing that config everywhere. That's what this
plugin automates.

## What it does

On **SessionStart**, if the session's cwd is a Python project
(`pyproject.toml` / `setup.py` / `setup.cfg` / a `.venv`) that has **no** Pyright
config yet, it writes:

```json
{
  "venvPath": ".",
  "venv": ".venv",
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}
```

- `venvPath`/`venv` → Pyright resolves the uv venv → imports resolve → real
  cross-file type intelligence, go-to-definition, and accurate type errors start
  working (the **more useful** half). Written only when a local `.venv` exists.
- `reportMissingImports`/`reportMissingModuleSource` → `none` kills the dominant
  noise (the **less noisy** half). With the venv resolved, real missing-imports
  are near-zero anyway, so this costs almost nothing.

Then it registers `pyrightconfig.json` in the repo's `.git/info/exclude`, so the
file is **never committed** and **never shows in `git status`** — it's a personal
dev-env artifact, not a project decision. No global git config, nothing to
replicate by hand on another machine.

### Guarantees

- **Idempotent** — exits early once a config exists; safe to fire every session.
- **Non-destructive** — never overwrites an existing `pyrightconfig.json` or a
  `[tool.pyright]` block in `pyproject.toml` (respects shared/team configs).
- **Silent** — emits no stdout, so it injects nothing into context.
- **Scoped** — a fast no-op outside Python projects (a few `stat`s, then exit).

## Install

```
/plugin marketplace update fb-claude-skills
/plugin install pyright-autoconfig@fb-claude-skills
```

New projects are configured on their first session; existing projects are
configured the next time you open a session in them (lazy retrofit). Requires
`jq` and `git` on PATH (both standard here).

### Configure a repo right now (without waiting for the next session)

```sh
printf '{"cwd":"%s"}' "$PWD" | \
  ~/.claude/plugins/*/fb-claude-skills/*/skills/pyright-autoconfig/hooks/session-start.sh
```

(or just start a fresh session in that repo.)

## Tuning

The default `reportMissingImports: "none"` trades away the "you typo'd an import
name" catch for silence. If you'd rather keep that signal, edit
`hooks/session-start.sh` to write `"warning"` instead — but note Claude Code
surfaces warnings too, so that will **not** reduce what the model sees; `"none"`
is the only value that actually removes the diagnostic. To also silence unused
variable/import hints (the `DiagnosticTag.Unnecessary` spam, upstream issue
anthropics/claude-code#26634), add `"reportUnusedImport": "none"` and
`"reportUnusedVariable": "none"`.

## Known limitation

Files with **no config above them** — throwaway `.py` under `/tmp`, or a sibling
repo you edit but never `cd` into — can't be reached by a per-project config, so
they'll still show `reportMissingImports`. They're throwaway; ignore them, or do
that work in a session rooted at that repo.

## Prerequisite

The `pyright-lsp` plugin itself must be installed and its `pyright-langserver`
on PATH. Keep Pyright current (`uv tool upgrade pyright`) — newer Pyright has
better `.venv` auto-detection, which complements this plugin.
