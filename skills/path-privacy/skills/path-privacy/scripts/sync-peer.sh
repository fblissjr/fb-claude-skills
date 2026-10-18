#!/usr/bin/env bash
# path-privacy: skip-file
# sync-peer.sh - verify and synchronize the unified dual-harness path-privacy
# plugin across peer checkouts (e.g. fb-gemini-plugins <-> Claude skills repo)
# and local installed caches (~/.gemini/config/plugins/path-privacy and
# ~/.claude/plugins/cache/*/path-privacy/*).
#
# Usage:
#   sync-peer.sh [--check] [--peer <peer-plugin-dir>]
#   sync-peer.sh --apply --peer <peer-plugin-dir>
#   sync-peer.sh --install [--peer <peer-plugin-dir>]
#
# Modes:
#   --check    Read-only (default). Verifies:
#                1. Dual-manifest parity (plugin.json == .claude-plugin/plugin.json,
#                   hooks.json + hooks/hooks.json valid JSON).
#                2. Byte-for-byte identity with --peer <dir> (or $PATH_PRIVACY_PEER_DIR)
#                   when supplied.
#                3. Installed cache parity across Antigravity (~/.gemini/...) and
#                   Claude Code (~/.claude/plugins/cache/...).
#              Exits 0 when everything inspected is aligned, 1 on any drift.
#   --apply    Copies this canonical plugin directory into --peer <dir> so both
#              repositories are 100% byte-for-byte identical.
#   --install  Updates local installed copies (~/.gemini/config/plugins/path-privacy,
#              ~/.gemini/antigravity-cli/plugins/path-privacy if present, and
#              ~/.claude/plugins/cache/*/path-privacy/*) from this checkout so both
#              agents immediately run the same version and wrapper template.

set -eu

MODE="check"
PEER_DIR="${PATH_PRIVACY_PEER_DIR:-}"

usage() { awk 'NR>2 { if (/^#/) print; else exit }' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --check)        MODE="check"; shift ;;
    --apply)        MODE="apply"; shift ;;
    --install)      MODE="install"; shift ;;
    --peer)         PEER_DIR="$2"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "sync-peer: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SELF_DIR/../../.." && pwd)"

redact_home() {
  local p="$1"
  if [ -n "${HOME:-}" ]; then
    p="${p/#$HOME/~}"
  fi
  printf '%s' "$p"
}

read_ver() {
  local f="$1"
  [ -r "$f" ] || { printf ''; return 0; }
  sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" 2>/dev/null | head -1
}

read_template() {
  local root="$1"
  local inst="$root/skills/path-privacy/scripts/install-git-hooks.sh"
  [ -r "$inst" ] || { printf 'unknown'; return 0; }
  sed -n 's/^WRAPPER_TEMPLATE_VERSION=\(.*\)$/t\1/p' "$inst" 2>/dev/null | head -1
}

AGY_MANIFEST="$PLUGIN_ROOT/plugin.json"
CLAUDE_MANIFEST="$PLUGIN_ROOT/.claude-plugin/plugin.json"
AGY_HOOKS="$PLUGIN_ROOT/hooks.json"
CLAUDE_HOOKS="$PLUGIN_ROOT/hooks/hooks.json"

AGY_VER=$(read_ver "$AGY_MANIFEST")
CLAUDE_VER=$(read_ver "$CLAUDE_MANIFEST")
TEMPLATE_VER=$(read_template "$PLUGIN_ROOT")

RC=0

check_internal_manifests() {
  echo "Source plugin: $(redact_home "$PLUGIN_ROOT") (version=${AGY_VER:-unknown}, template=${TEMPLATE_VER:-unknown})"
  if [ -z "$AGY_VER" ]; then
    echo "  [FAIL] Missing or unreadable version in plugin.json"
    RC=1
  fi
  if [ -z "$CLAUDE_VER" ]; then
    echo "  [FAIL] Missing or unreadable version in .claude-plugin/plugin.json"
    RC=1
  fi
  if [ -n "$AGY_VER" ] && [ -n "$CLAUDE_VER" ]; then
    if [ "$AGY_VER" = "$CLAUDE_VER" ]; then
      echo "  [OK]   Dual manifests match: plugin.json ($AGY_VER) == .claude-plugin/plugin.json ($CLAUDE_VER)"
    else
      echo "  [FAIL] Dual manifest version mismatch: plugin.json ($AGY_VER) != .claude-plugin/plugin.json ($CLAUDE_VER)"
      RC=1
    fi
  fi
  for hf in "$AGY_HOOKS" "$CLAUDE_HOOKS"; do
    local rel="${hf#"$PLUGIN_ROOT"/}"
    if [ ! -r "$hf" ]; then
      echo "  [FAIL] Missing hook manifest: $rel"
      RC=1
    elif command -v jq >/dev/null 2>&1 && ! jq -e . "$hf" >/dev/null 2>&1; then
      echo "  [FAIL] Invalid JSON in $rel"
      RC=1
    else
      echo "  [OK]   Hook manifest valid: $rel"
    fi
  done
}

# Compare two plugin roots, ignoring .DS_Store, .git, and .claude runtime state
trees_identical() {
  local src="$1" dst="$2"
  diff -ru -x '.DS_Store' -x '.git' -x '.claude' "$src" "$dst" >/dev/null 2>&1
}

sync_tree_to() {
  local dst="$1" src_real dst_real
  mkdir -p "$dst"
  src_real=$(cd "$PLUGIN_ROOT" && pwd -P)
  dst_real=$(cd "$dst" && pwd -P)
  if [ "$src_real" = "$dst_real" ]; then
    return 0
  fi
  rm -rf "${dst:?}"/* "${dst:?}"/.[!.]* "${dst:?}"/..?* 2>/dev/null || true
  cp -pR "$PLUGIN_ROOT/." "$dst/"
  rm -rf "$dst/.git" 2>/dev/null || true
  find "$dst" -name '.DS_Store' -delete 2>/dev/null || true
}

verify_is_path_privacy_dir() {
  local d="$1"
  if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    if [ ! -f "$d/plugin.json" ] && [ ! -f "$d/.claude-plugin/plugin.json" ] && [ ! -d "$d/skills/path-privacy" ]; then
      echo "sync-peer: target directory exists but does not look like a path-privacy plugin: $(redact_home "$d")" >&2
      echo "  Refusing to overwrite an unrelated directory." >&2
      exit 2
    fi
  fi
}

check_internal_manifests

if [ "$MODE" = "apply" ]; then
  if [ -z "$PEER_DIR" ]; then
    echo "sync-peer: --apply requires --peer <peer-plugin-dir> (or PATH_PRIVACY_PEER_DIR)." >&2
    exit 2
  fi
  verify_is_path_privacy_dir "$PEER_DIR"
  sync_tree_to "$PEER_DIR"
  if trees_identical "$PLUGIN_ROOT" "$PEER_DIR"; then
    echo "  [OK]   Synced canonical plugin tree -> $(redact_home "$PEER_DIR") (100% byte-identical)"
  else
    echo "  [FAIL] Differences remain after syncing to $(redact_home "$PEER_DIR")"
    exit 1
  fi
  exit "$RC"
fi

if [ "$MODE" = "install" ]; then
  if [ -n "$PEER_DIR" ]; then
    verify_is_path_privacy_dir "$PEER_DIR"
    sync_tree_to "$PEER_DIR"
    echo "  [OK]   Synced peer checkout -> $(redact_home "$PEER_DIR")"
  fi
  if [ -n "${HOME:-}" ]; then
    for agy_dst in \
      "$HOME/.gemini/config/plugins/path-privacy" \
      "$HOME/.gemini/antigravity-cli/plugins/path-privacy"; do
      if [ -d "$agy_dst" ] || [ "$agy_dst" = "$HOME/.gemini/config/plugins/path-privacy" ]; then
        verify_is_path_privacy_dir "$agy_dst"
        sync_tree_to "$agy_dst"
        echo "  [OK]   Updated Antigravity install -> $(redact_home "$agy_dst") (v${AGY_VER}, ${TEMPLATE_VER})"
      fi
    done

    for mp in "$HOME/.claude/plugins/cache"/*/path-privacy; do
      [ -d "$mp" ] || continue
      # Update both the versioned directory matching AGY_VER and any existing cached version directories
      # so running Claude Code sessions and future sessions both resolve v${AGY_VER} / ${TEMPLATE_VER}.
      target_ver_dir="$mp/$AGY_VER"
      sync_tree_to "$target_ver_dir"
      echo "  [OK]   Updated Claude cache -> $(redact_home "$target_ver_dir") (v${AGY_VER}, ${TEMPLATE_VER})"
      for existing_ver_dir in "$mp"/*; do
        [ -d "$existing_ver_dir" ] || continue
        [ "$existing_ver_dir" = "$target_ver_dir" ] && continue
        verify_is_path_privacy_dir "$existing_ver_dir"
        sync_tree_to "$existing_ver_dir"
        echo "  [OK]   Refreshed legacy Claude cache slot -> $(redact_home "$existing_ver_dir") (v${AGY_VER}, ${TEMPLATE_VER})"
      done
    done
  fi
  exit "$RC"
fi

# --- MODE="check" ------------------------------------------------------------
if [ -n "$PEER_DIR" ]; then
  echo ""
  echo "Peer checkout: $(redact_home "$PEER_DIR")"
  if [ ! -d "$PEER_DIR" ]; then
    echo "  [FAIL] Peer directory does not exist: $(redact_home "$PEER_DIR")"
    RC=1
  elif trees_identical "$PLUGIN_ROOT" "$PEER_DIR"; then
    echo "  [OK]   100% byte-identical with source plugin"
  else
    peer_v=$(read_ver "$PEER_DIR/plugin.json")
    [ -z "$peer_v" ] && peer_v=$(read_ver "$PEER_DIR/.claude-plugin/plugin.json")
    peer_t=$(read_template "$PEER_DIR")
    echo "  [FAIL] Drift detected (peer version=${peer_v:-unknown}, template=${peer_t:-unknown})"
    diff -rq -x '.DS_Store' -x '.git' -x '.claude' "$PLUGIN_ROOT" "$PEER_DIR" 2>/dev/null | sed "s|$PLUGIN_ROOT|<source>|g; s|$PEER_DIR|<peer>|g; s|^|    |" || true
    echo "  Run: bash skills/path-privacy/skills/path-privacy/scripts/sync-peer.sh --apply --peer $(redact_home "$PEER_DIR")"
    RC=1
  fi
fi

if [ -n "${HOME:-}" ]; then
  echo ""
  echo "Installed harness copies:"
  FOUND_INSTALLED=0
  for d in \
    "$HOME/.gemini/config/plugins/path-privacy" \
    "$HOME/.gemini/antigravity-cli/plugins/path-privacy"; do
    [ -d "$d" ] || continue
    FOUND_INSTALLED=1
    if trees_identical "$PLUGIN_ROOT" "$d"; then
      echo "  [OK]   $(redact_home "$d") (v${AGY_VER}, ${TEMPLATE_VER}, byte-identical)"
    else
      iv=$(read_ver "$d/plugin.json")
      [ -z "$iv" ] && iv=$(read_ver "$d/.claude-plugin/plugin.json")
      it=$(read_template "$d")
      echo "  [DRIFT] $(redact_home "$d") (ver=${iv:-unknown}, template=${it:-unknown}) != source (ver=${AGY_VER}, template=${TEMPLATE_VER})"
      RC=1
    fi
  done
  for mp in "$HOME/.claude/plugins/cache"/*/path-privacy; do
    [ -d "$mp" ] || continue
    latest=$(printf '%s\n' "$mp"/* 2>/dev/null | awk -F/ 'NF>1 {print $NF"\t"$0}' | sort -rV 2>/dev/null | head -1 | cut -f2-)
    [ -n "$latest" ] && [ -d "$latest" ] || continue
    FOUND_INSTALLED=1
    if trees_identical "$PLUGIN_ROOT" "$latest"; then
      echo "  [OK]   $(redact_home "$latest") (v${AGY_VER}, ${TEMPLATE_VER}, byte-identical)"
    else
      iv=$(read_ver "$latest/.claude-plugin/plugin.json")
      [ -z "$iv" ] && iv=$(read_ver "$latest/plugin.json")
      it=$(read_template "$latest")
      echo "  [DRIFT] $(redact_home "$latest") (ver=${iv:-unknown}, template=${it:-unknown}) != source (ver=${AGY_VER}, template=${TEMPLATE_VER})"
      RC=1
    fi
  done
  if [ "$FOUND_INSTALLED" -eq 0 ]; then
    echo "  (no global ~/.gemini or ~/.claude cache installs found)"
  elif [ "$RC" -ne 0 ]; then
    echo ""
    echo "To align all installed harness copies on this machine, run:"
    echo "  bash skills/path-privacy/skills/path-privacy/scripts/sync-peer.sh --install"
  fi
fi

exit "$RC"
