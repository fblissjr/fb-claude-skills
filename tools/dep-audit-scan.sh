#!/usr/bin/env bash
# dep-audit-scan.sh -- Scan macOS for projects with dependency vulnerabilities
#
# Searches common project directories for pyproject.toml and package.json,
# then runs uv audit / bun audit on each. Produces a summary report.
#
# Usage:
#   ./tools/dep-audit-scan.sh                    # scan default dirs
#   ./tools/dep-audit-scan.sh ~/work ~/projects  # scan specific dirs
#   ./tools/dep-audit-scan.sh --json             # JSON output
#   ./tools/dep-audit-scan.sh --fix              # attempt auto-fix via lock upgrade

set -euo pipefail

# --- Configuration ---
DEFAULT_SCAN_DIRS=(
  "$HOME/claude"
  "$HOME/workspace"
  "$HOME/projects"
  "$HOME/code"
  "$HOME/dev"
  "$HOME/src"
)

SKIP_DIRS="node_modules|.venv|venv|.git|__pycache__|dist|build|.next|.output|.tox|.mypy_cache|.ruff_cache|site-packages"
MAX_DEPTH=3

UV="${UV:-$(command -v uv 2>/dev/null || true)}"
BUN="${BUN:-$(command -v bun 2>/dev/null || true)}"

# --- Parse args ---
SCAN_DIRS=()
JSON_OUTPUT=false
AUTO_FIX=false

for arg in "$@"; do
  case "$arg" in
    --json)    JSON_OUTPUT=true ;;
    --fix)     AUTO_FIX=true ;;
    --help|-h)
      echo "Usage: dep-audit-scan.sh [--json] [--fix] [dir ...]"
      echo ""
      echo "Scans directories for Python and JS/TS projects, runs dependency"
      echo "vulnerability audits on each, and produces a summary report."
      echo ""
      echo "Options:"
      echo "  --json    Output results as JSON"
      echo "  --fix     Attempt to fix vulnerabilities by upgrading lock files"
      echo "  dir ...   Directories to scan (default: ~/claude ~/workspace ~/projects ~/code ~/dev ~/src)"
      exit 0
      ;;
    *)         SCAN_DIRS+=("$arg") ;;
  esac
done

if [ ${#SCAN_DIRS[@]} -eq 0 ]; then
  for d in "${DEFAULT_SCAN_DIRS[@]}"; do
    [ -d "$d" ] && SCAN_DIRS+=("$d")
  done
fi

if [ ${#SCAN_DIRS[@]} -eq 0 ]; then
  echo "error: no scan directories found. Pass directories as arguments." >&2
  exit 1
fi

# --- State ---
TOTAL_PROJECTS=0
TOTAL_VULNS=0
CLEAN_PROJECTS=0
VULN_PROJECTS=0
SKIPPED_PROJECTS=0

declare -a RESULTS_JSON=()
declare -a VULN_SUMMARY=()

# --- Helpers ---
should_skip() {
  local path="$1"
  echo "$path" | grep -qE "/($SKIP_DIRS)/"
}

audit_python() {
  local project_dir="$1"
  local project_name
  project_name=$(basename "$project_dir")

  if [ -z "$UV" ]; then
    echo "  [skip] uv not found" >&2
    return 2
  fi

  # Check if there's a uv.lock or we can generate one
  local output exit_code
  if [ -f "$project_dir/uv.lock" ]; then
    output=$("$UV" audit --preview-features audit --directory "$project_dir" 2>&1) && exit_code=0 || exit_code=$?
  else
    # No lock file -- try a dry-run lock first
    if "$UV" lock --directory "$project_dir" --dry-run >/dev/null 2>&1; then
      output=$("$UV" audit --preview-features audit --directory "$project_dir" 2>&1) && exit_code=0 || exit_code=$?
    else
      echo "  [skip] cannot resolve dependencies" >&2
      return 2
    fi
  fi

  if [ "$AUTO_FIX" = true ] && [ $exit_code -ne 0 ] && [ -f "$project_dir/uv.lock" ]; then
    echo "  [fix] upgrading vulnerable packages..." >&2
    local pkgs
    pkgs=$(echo "$output" | grep "has .* known vulnerabilit" | awk '{print $1}')
    if [ -n "$pkgs" ]; then
      local upgrade_args=()
      while IFS= read -r pkg; do
        upgrade_args+=(--upgrade-package "$pkg")
      done <<< "$pkgs"
      "$UV" lock --directory "$project_dir" "${upgrade_args[@]}" 2>/dev/null || true
      output=$("$UV" audit --preview-features audit --directory "$project_dir" 2>&1) && exit_code=0 || exit_code=$?
      if [ $exit_code -eq 0 ]; then
        echo "  [fix] all vulnerabilities resolved" >&2
      fi
    fi
  fi

  # Count vulnerabilities from the "Found N known vulnerabilities" summary line
  local vuln_count=0
  if [ $exit_code -ne 0 ]; then
    vuln_count=$(echo "$output" | grep -oE "Found [0-9]+ known vulnerabilit" | grep -oE "[0-9]+" || echo "0")
    [ -z "$vuln_count" ] && vuln_count=0
  fi

  echo "$vuln_count"
  if [ $exit_code -ne 0 ]; then
    echo "$output"
  fi
  return $exit_code
}

audit_javascript() {
  local project_dir="$1"

  if [ -z "$BUN" ]; then
    echo "  [skip] bun not found" >&2
    return 2
  fi

  # bun audit needs node_modules
  if [ ! -d "$project_dir/node_modules" ]; then
    echo "  [skip] no node_modules (run bun install first)" >&2
    return 2
  fi

  local output exit_code
  output=$(cd "$project_dir" && "$BUN" audit 2>&1) && exit_code=0 || exit_code=$?

  # Count distinct advisory entries (lines with severity labels)
  local vuln_count=0
  if [ $exit_code -ne 0 ]; then
    vuln_count=$(echo "$output" | grep -cE "^\s+(high|moderate|low|critical):" 2>/dev/null || echo "0")
    [ -z "$vuln_count" ] && vuln_count=0
    if [ "$vuln_count" -eq 0 ] && [ $exit_code -ne 0 ]; then
      vuln_count=1
    fi
  fi

  echo "$vuln_count"
  if [ $exit_code -ne 0 ]; then
    echo "$output"
  fi
  return $exit_code
}

# --- Main scan ---
echo "=== Dependency Audit Scan ==="
echo "Scanning: ${SCAN_DIRS[*]}"
echo "Tools: uv=${UV:-missing} bun=${BUN:-missing}"
echo ""

for scan_dir in "${SCAN_DIRS[@]}"; do
  # Find Python projects
  while IFS= read -r pyproject; do
    project_dir=$(dirname "$pyproject")

    should_skip "$project_dir" && continue

    # Skip if it's a workspace member's pyproject but the root has one too
    # (uv audit from root covers workspace members)
    parent=$(dirname "$project_dir")
    if [ -f "$parent/pyproject.toml" ] && grep -q "workspace" "$parent/pyproject.toml" 2>/dev/null; then
      continue
    fi

    TOTAL_PROJECTS=$((TOTAL_PROJECTS + 1))
    rel_path="${project_dir/#$HOME/~}"
    echo "[$TOTAL_PROJECTS] $rel_path (python)"

    result=$(audit_python "$project_dir" 2>/dev/null) && audit_exit=0 || audit_exit=$?

    if [ $audit_exit -eq 2 ]; then
      SKIPPED_PROJECTS=$((SKIPPED_PROJECTS + 1))
      echo "  skipped"
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"python\",\"status\":\"skipped\",\"vulns\":0}")
    elif [ $audit_exit -eq 0 ]; then
      CLEAN_PROJECTS=$((CLEAN_PROJECTS + 1))
      echo "  clean"
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"python\",\"status\":\"clean\",\"vulns\":0}")
    else
      vuln_count=$(echo "$result" | head -1)
      details=$(echo "$result" | tail -n +2)
      VULN_PROJECTS=$((VULN_PROJECTS + 1))
      TOTAL_VULNS=$((TOTAL_VULNS + vuln_count))
      echo "  VULNERABLE ($vuln_count issues)"
      echo "$details" | grep -E "(has .* known|Fixed in:|Advisory)" | sed 's/^/    /'
      VULN_SUMMARY+=("$rel_path (python): $vuln_count vulnerabilities")
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"python\",\"status\":\"vulnerable\",\"vulns\":$vuln_count}")
    fi
  done < <(find "$scan_dir" -maxdepth "$MAX_DEPTH" -name "pyproject.toml" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/.git/*" 2>/dev/null)

  # Find JavaScript projects
  while IFS= read -r pkgjson; do
    project_dir=$(dirname "$pkgjson")

    should_skip "$project_dir" && continue

    TOTAL_PROJECTS=$((TOTAL_PROJECTS + 1))
    rel_path="${project_dir/#$HOME/~}"
    echo "[$TOTAL_PROJECTS] $rel_path (javascript)"

    result=$(audit_javascript "$project_dir" 2>/dev/null) && audit_exit=0 || audit_exit=$?

    if [ $audit_exit -eq 2 ]; then
      SKIPPED_PROJECTS=$((SKIPPED_PROJECTS + 1))
      echo "  skipped"
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"javascript\",\"status\":\"skipped\",\"vulns\":0}")
    elif [ $audit_exit -eq 0 ]; then
      CLEAN_PROJECTS=$((CLEAN_PROJECTS + 1))
      echo "  clean"
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"javascript\",\"status\":\"clean\",\"vulns\":0}")
    else
      vuln_count=$(echo "$result" | head -1)
      details=$(echo "$result" | tail -n +2)
      VULN_PROJECTS=$((VULN_PROJECTS + 1))
      TOTAL_VULNS=$((TOTAL_VULNS + vuln_count))
      echo "  VULNERABLE ($vuln_count issues)"
      echo "$details" | head -20 | sed 's/^/    /'
      VULN_SUMMARY+=("$rel_path (javascript): $vuln_count vulnerabilities")
      RESULTS_JSON+=("{\"path\":\"$rel_path\",\"type\":\"javascript\",\"status\":\"vulnerable\",\"vulns\":$vuln_count}")
    fi
  done < <(find "$scan_dir" -maxdepth "$MAX_DEPTH" -name "package.json" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null)
done

# --- Summary ---
echo ""
echo "=== Summary ==="
echo "Projects scanned: $TOTAL_PROJECTS"
echo "Clean: $CLEAN_PROJECTS"
echo "Vulnerable: $VULN_PROJECTS ($TOTAL_VULNS total vulnerabilities)"
echo "Skipped: $SKIPPED_PROJECTS"

if [ ${#VULN_SUMMARY[@]} -gt 0 ]; then
  echo ""
  echo "=== Vulnerable Projects ==="
  for entry in "${VULN_SUMMARY[@]}"; do
    echo "  - $entry"
  done
fi

if [ "$JSON_OUTPUT" = true ]; then
  echo ""
  echo "=== JSON ==="
  echo "["
  for i in "${!RESULTS_JSON[@]}"; do
    if [ $i -lt $((${#RESULTS_JSON[@]} - 1)) ]; then
      echo "  ${RESULTS_JSON[$i]},"
    else
      echo "  ${RESULTS_JSON[$i]}"
    fi
  done
  echo "]"
fi

# Exit non-zero if any vulnerabilities found
[ "$TOTAL_VULNS" -eq 0 ]
