#!/usr/bin/env bash
# pyright-autoconfig SessionStart hook.
#
# If cwd is a Python project with no Pyright configuration, drop a personal
# pyrightconfig.json that:
#   1. points Pyright at the local uv .venv (venvPath/venv) so third-party and
#      local-package imports RESOLVE -> real cross-file type intelligence, and
#   2. sets reportMissingImports/reportMissingModuleSource to "none" so the
#      residual missing-import flood (worst on files pyright can't root, e.g.
#      sibling repos and scratch dirs) stops polluting the session.
#
# The file is registered in the repo's .git/info/exclude, so it is never
# committed and never appears in `git status` -- this is a personal dev-env
# artifact, not a project decision, and needs no global git config.
#
# Guarantees: idempotent (exits once a config exists), silent (no stdout ->
# no injected context), and a fast no-op outside Python projects. It never
# overwrites an existing pyrightconfig.json or a [tool.pyright] pyproject block.
#
# Reads the session cwd from the SessionStart hook's JSON stdin (.cwd).

CWD=$(jq -r '.cwd // ""' 2>/dev/null)
[ -n "$CWD" ] || exit 0
[ -d "$CWD" ] || exit 0
cd "$CWD" 2>/dev/null || exit 0

# --- Python project? (pyproject / setup / a local venv) ------------------------
if [ ! -f pyproject.toml ] && [ ! -f setup.py ] && [ ! -f setup.cfg ] && [ ! -d .venv ]; then
  exit 0
fi

# --- Respect any existing Pyright config (personal file or shared pyproject) ---
if [ -f pyrightconfig.json ]; then
  exit 0
fi
if [ -f pyproject.toml ] && grep -q '^\[tool\.pyright\]' pyproject.toml 2>/dev/null; then
  exit 0
fi

# --- Write the config ----------------------------------------------------------
# Include the venv pointer only when a local .venv exists, so conda/pyenv
# projects (no local .venv) get the noise-reduction without a wrong interpreter.
if [ -d .venv ]; then
  cat > pyrightconfig.json <<'JSON'
{
  "venvPath": ".",
  "venv": ".venv",
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}
JSON
else
  cat > pyrightconfig.json <<'JSON'
{
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}
JSON
fi

# --- Keep it out of version control without touching the tracked .gitignore ----
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  excl=$(git rev-parse --git-path info/exclude 2>/dev/null)
  if [ -n "$excl" ]; then
    mkdir -p "$(dirname "$excl")" 2>/dev/null
    if [ ! -f "$excl" ] || ! grep -qxF 'pyrightconfig.json' "$excl" 2>/dev/null; then
      printf '%s\n' 'pyrightconfig.json' >> "$excl"
    fi
  fi
fi

exit 0
