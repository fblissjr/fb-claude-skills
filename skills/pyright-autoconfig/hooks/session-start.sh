#!/usr/bin/env bash
# pyright-autoconfig SessionStart hook.
#
# If cwd is a Python project with no Pyright configuration, drop a personal
# pyrightconfig.json that (1) points Pyright at the local uv .venv so imports
# resolve, and (2) silences the reportMissingImports flood. The file is
# registered in the repo's .git/info/exclude, so it is never committed and
# never appears in `git status`.
#
# Self-healing: if a venv-less config was written before `.venv` existed (the
# clone-then-`uv sync` order), a later session adds the venv pointer once
# `.venv` appears. It never overwrites a config it did not write, and never
# shadows a project's own [tool.pyright] -- bare header OR any subtable.
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

# --- Desired config, built once (venv pointer only when a local .venv exists) --
if [ -d .venv ]; then
  desired='{
  "venvPath": ".",
  "venv": ".venv",
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}'
else
  desired='{
  "reportMissingImports": "none",
  "reportMissingModuleSource": "none"
}'
fi

# --- Decide whether to (re)write -----------------------------------------------
if [ -f pyrightconfig.json ]; then
  # Not ours (lacks our marker) -> respect it, do nothing.
  grep -q 'reportMissingModuleSource' pyrightconfig.json 2>/dev/null || exit 0
  # Ours and already up to date -> nothing to do.
  [ "$(cat pyrightconfig.json 2>/dev/null)" = "$desired" ] && exit 0
  # Ours but stale (e.g. .venv appeared after `uv sync`) -> fall through, rewrite.
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
