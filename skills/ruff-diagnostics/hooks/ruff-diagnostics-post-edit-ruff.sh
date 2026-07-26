#!/usr/bin/env bash
# ruff-diagnostics PostToolUse hook.
#
# After Claude edits or writes a .py/.pyi file, run Ruff on that one file and
# report the findings back as additionalContext. This exists because Claude Code
# registers at most ONE language server per file extension: pyright-lsp claims
# .py and .pyi, so a second LSP declaring those extensions never starts (see
# plugins-reference, "Multiple servers for the same extension"). Ruff therefore
# cannot ride in as `ruff server` alongside Pyright the way it does in VS Code
# or Neovim. A hook reconstructs the same division of labour from outside:
# Pyright owns types and navigation, Ruff owns lint.
#
# Astral independently arrived at the same split -- their own Claude Code plugin
# (astral-sh/claude-code-plugins) ships a `ty` LSP server and deliberately does
# NOT register ruff as one.
#
# Design constraints, each of which cost something to learn:
#
#   * Never mutate the project. `uv run ruff` SYNCS THE ENVIRONMENT before it
#     runs -- observed installing 24 packages in a project that merely lacked
#     ruff. A diagnostic hook that silently rewrites your venv is unacceptable,
#     so every probe here uses `uv run --no-sync`, which fails cleanly instead.
#
#   * Never write config. Ruff's config lives in tracked files (pyproject.toml,
#     ruff.toml). Unlike pyright-autoconfig -- which can drop a git-excluded
#     pyrightconfig.json -- there is no untracked place to put ruff settings,
#     so this hook only ever reads.
#
#   * Treat E902 as a harness failure, not a finding. Ruff reports an unreadable
#     path as a single E902 io-error, so a naive "count the findings" reading of
#     a broken invocation returns a plausible-looking 1 rather than crashing.
#     Any E902 aborts silently rather than reporting fiction.
#
#   * Say nothing when there is nothing to say. Zero findings emits no context
#     at all: an always-on hook that narrates its own success is pure token cost.
#
# Silent and non-blocking throughout: every failure path exits 0 with no output.

set -u

MAX_SHOWN=12

IN=$(cat 2>/dev/null) || exit 0
[ -n "$IN" ] || exit 0

command -v jq >/dev/null 2>&1 || exit 0

FILE=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
[ -n "$FILE" ] || exit 0
SESSION=$(printf '%s' "$IN" | jq -r '.session_id // "nosession"' 2>/dev/null)

# --- Python file that still exists? -------------------------------------------
case "$FILE" in
  *.py|*.pyi) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

FILE_DIR=$(dirname "$FILE")
cd "$FILE_DIR" 2>/dev/null || exit 0

# --- Walk up to the project root ----------------------------------------------
# Stop at the first pyproject.toml / ruff.toml / .git. Ruff resolves its own
# config by walking up from the file, but the ruff BINARY has to be chosen
# relative to the project, and `uv run` needs to be invoked from inside it.
ROOT=""
d=$(pwd -P)
while [ "$d" != "/" ]; do
  if [ -f "$d/pyproject.toml" ] || [ -f "$d/ruff.toml" ] || [ -f "$d/.ruff.toml" ] || [ -d "$d/.git" ]; then
    ROOT="$d"
    break
  fi
  d=$(dirname "$d")
done
[ -n "$ROOT" ] || exit 0
cd "$ROOT" 2>/dev/null || exit 0

# --- Resolve a ruff binary, preferring the project's pinned one ---------------
# Order follows Astral's own guidance (project-pinned > ephemeral > global),
# adapted so that no rung can mutate the environment.
RUFF=""
PROVENANCE=""
if command -v uv >/dev/null 2>&1 && uv run --no-sync ruff --version >/dev/null 2>&1; then
  RUFF="uv run --no-sync ruff"
  PROVENANCE="project-pinned"
elif command -v ruff >/dev/null 2>&1; then
  RUFF="ruff"
  PROVENANCE="global"
elif command -v uvx >/dev/null 2>&1; then
  RUFF="uvx ruff@latest"
  PROVENANCE="unpinned"
else
  exit 0
fi

# --- Check the one file ---------------------------------------------------------
# --force-exclude makes ruff honour the project's own exclude list even though
# we are handing it an explicit path, so generated/vendored files stay quiet.
OUT=$($RUFF check --output-format json --force-exclude -- "$FILE" 2>/dev/null) || true
[ -n "$OUT" ] || exit 0
printf '%s' "$OUT" | jq -e 'type == "array"' >/dev/null 2>&1 || exit 0

# E902 means ruff could not read what we gave it. Report nothing rather than
# reporting an io-error as if it were a lint finding.
if printf '%s' "$OUT" | jq -e 'any(.[]; .code == "E902")' >/dev/null 2>&1; then
  exit 0
fi

TOTAL=$(printf '%s' "$OUT" | jq 'length' 2>/dev/null) || exit 0
TOTAL=${TOTAL:-0}

REL=${FILE#"$ROOT"/}

# --- Does this project opt out of ruff 0.16 defaults? --------------------------
# `select` REPLACES the default rule set; `extend-select` adds to it. Since 0.16
# the defaults are 413 rules (up from 59), so a curated `select` written before
# that release is now NARROWER than having no config at all -- and silently so.
#
# This has to fire independently of whether the edited file has findings: a
# project pinned to a narrow `select` reports every file clean, which is exactly
# the state the note is warning about. Emitted at most once per session per
# project root, so the advice lands without repeating on every edit.
SELECT_NOTE=""
for cfg in "$ROOT/pyproject.toml" "$ROOT/ruff.toml" "$ROOT/.ruff.toml"; do
  [ -f "$cfg" ] || continue
  if grep -qE '^[[:space:]]*select[[:space:]]*=' "$cfg" 2>/dev/null \
     && ! grep -qE '^[[:space:]]*extend-select[[:space:]]*=' "$cfg" 2>/dev/null; then
    stamp_dir="${TMPDIR:-/tmp}/ruff-diagnostics"
    stamp_key=$(printf '%s|%s' "$SESSION" "$ROOT" | cksum 2>/dev/null | tr -d ' \t')
    stamp="$stamp_dir/${stamp_key:-fallback}"
    if [ ! -f "$stamp" ]; then
      mkdir -p "$stamp_dir" 2>/dev/null && : > "$stamp" 2>/dev/null
      SELECT_NOTE="Ruff config note: this project sets \`select\`, which REPLACES Ruff's defaults (413 rules since 0.16) rather than extending them, so it may be enabling fewer checks than no config at all. \`extend-select\` keeps the defaults and adds to them. Raise it with the user; do not change their lint config unprompted."
    fi
  fi
  break
done

# Nothing wrong with the file. Stay silent unless the config note is due.
if [ "$TOTAL" -eq 0 ]; then
  if [ -n "$SELECT_NOTE" ]; then
    printf '%s' "$SELECT_NOTE" | jq -Rs '{
      hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: . }
    }' 2>/dev/null
  fi
  exit 0
fi

FIXABLE=$(printf '%s' "$OUT" | jq '[.[] | select(.fix != null)] | length' 2>/dev/null)
FIXABLE=${FIXABLE:-0}

LINES=$(printf '%s' "$OUT" | jq -r --argjson n "$MAX_SHOWN" '
  .[:$n][]
  | "  L\(.location.row // 0) \(.code // "?") \(.message)\(if .fix != null then "  [fixable]" else "" end)"
' 2>/dev/null)
[ -n "$LINES" ] || exit 0

PROV_NOTE=""
if [ "$PROVENANCE" = "unpinned" ]; then
  PROV_NOTE=" (ran an unpinned \`uvx ruff@latest\`; this project has no ruff installed, so results may not match its CI)"
fi

SUMMARY="Ruff on ${REL}: ${TOTAL} finding(s), ${FIXABLE} auto-fixable${PROV_NOTE}.
${LINES}"

if [ "$TOTAL" -gt "$MAX_SHOWN" ]; then
  SUMMARY="${SUMMARY}
  ... and $((TOTAL - MAX_SHOWN)) more"
fi

if [ "$FIXABLE" -gt 0 ]; then
  SUMMARY="${SUMMARY}

Apply the mechanical ones with: ruff check --fix -- ${REL}
Fix the rest by hand -- do not suppress them without a reason."
fi

if [ -n "$SELECT_NOTE" ]; then
  SUMMARY="${SUMMARY}

${SELECT_NOTE}"
fi

printf '%s' "$SUMMARY" | jq -Rs '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: .
  }
}' 2>/dev/null || exit 0

exit 0
