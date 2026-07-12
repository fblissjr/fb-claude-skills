#!/usr/bin/env bash
# pyright-autoconfig SessionStart hook.
#
# If cwd is a Python project with no Pyright configuration, drop a personal
# pyrightconfig.json that (1) points Pyright at the local uv .venv so imports
# resolve, and (2) silences the reportMissingImports flood. The file is
# registered in the repo's .git/info/exclude, so it is never committed and
# never appears in `git status`.
#
# Ownership is exact: the hook only ever writes, recognizes, or rewrites its
# OWN byte-for-byte output (the two templates below). Any other pyrightconfig.json
# -- hand-written or shared, even one that happens to set the same keys -- is
# left completely untouched. It also never shadows a project's own
# [tool.pyright] (bare header OR any subtable).
#
# Self-healing: if it wrote the venv-less template before `.venv` existed (the
# clone-then-`uv sync` order), a later session upgrades THAT exact file to the
# venv template once `.venv` appears.
#
# Idempotent, silent (no stdout -> no injected context), a fast no-op outside
# Python projects. Reads the session cwd from the hook's JSON stdin (.cwd);
# requires jq (a missing jq is reported once to stderr, then skipped).

CWD=$(jq -r '.cwd // ""' 2>/dev/null)
if [ -z "$CWD" ]; then
  command -v jq >/dev/null 2>&1 || echo "pyright-autoconfig: jq not on PATH; skipping" >&2
  exit 0
fi
[ -d "$CWD" ] || exit 0
cd "$CWD" 2>/dev/null || exit 0

# --- Python project? (pyproject / setup / a local venv) ------------------------
if [ ! -f pyproject.toml ] && [ ! -f setup.py ] && [ ! -f setup.cfg ] && [ ! -d .venv ]; then
  exit 0
fi

# --- Respect a project's own Pyright config ------------------------------------
# Match a bare [tool.pyright] header OR any [tool.pyright.<subtable>] (e.g.
# executionEnvironments) -- a subtable alone is valid TOML, and our
# pyrightconfig.json would otherwise silently shadow it.
if [ -f pyproject.toml ] && grep -qE '^[[:space:]]*\[tool\.pyright(\]|\.)' pyproject.toml 2>/dev/null; then
  exit 0
fi

# --- Our exact config templates (used to WRITE and to recognize our own output).
# The venv pointer is included only when a local .venv exists, so conda/pyenv
# projects avoid a "venv not found" diagnostic.
tmpl_novenv='{
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}'
tmpl_venv='{
  "venvPath": ".",
  "venv": ".venv",
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}'
if [ -d .venv ]; then desired="$tmpl_venv"; else desired="$tmpl_novenv"; fi

# --- Decide whether to (re)write -----------------------------------------------
if [ -f pyrightconfig.json ]; then
  cur="$(cat pyrightconfig.json 2>/dev/null)"
  # Already exactly what we want -> nothing to do.
  [ "$cur" = "$desired" ] && exit 0
  # Self-heal ONLY our own exact venv-less output once .venv appears. Anything
  # else -- a user/shared config, or one we can't positively identify as ours --
  # is left untouched.
  if ! { [ "$cur" = "$tmpl_novenv" ] && [ -d .venv ]; }; then
    exit 0
  fi
fi

# Write; only touch version control if the write actually succeeded.
printf '%s\n' "$desired" > pyrightconfig.json 2>/dev/null || exit 0

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
