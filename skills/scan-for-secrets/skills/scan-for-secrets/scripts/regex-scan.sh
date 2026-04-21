#!/usr/bin/env bash
# regex-scan.sh - shape-based privacy/secret sweep using ripgrep.
# Companion to scan-for-secrets. Read-only. Exit 1 on any match (parity with scan-for-secrets).
#
# Usage:
#   regex-scan.sh [-d <dir>]... [-f <file>]... [--api-keys] [--no-default] [--extra <patterns-file>]
#
# Defaults to scanning the current directory. --api-keys adds common token shapes.
# --no-default disables the core privacy pattern set (useful when combining with --extra).

set -u

if ! command -v rg >/dev/null 2>&1; then
  echo "regex-scan: ripgrep (rg) not found. Install via 'brew install ripgrep' or equivalent." >&2
  exit 127
fi

DIRS=()
FILES=()
API_KEYS=0
NO_DEFAULT=0
EXTRA=""

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--directory)  DIRS+=("$2"); shift 2 ;;
    -f|--file)       FILES+=("$2"); shift 2 ;;
    --api-keys)      API_KEYS=1; shift ;;
    --no-default)    NO_DEFAULT=1; shift ;;
    --extra)         EXTRA="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,9p' "$0"
      exit 0 ;;
    *) echo "regex-scan: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ ${#DIRS[@]} -eq 0 ] && [ ${#FILES[@]} -eq 0 ]; then
  DIRS=(".")
fi

# Shared skip globs (mirror scan-for-secrets SKIP_DIRS)
SKIPS=(
  --glob '!.git/**'
  --glob '!.hg/**'
  --glob '!.svn/**'
  --glob '!node_modules/**'
  --glob '!__pycache__/**'
  --glob '!.venv/**'
  --glob '!venv/**'
  --glob '!.mypy_cache/**'
  --glob '!.ruff_cache/**'
  --glob '!.pytest_cache/**'
)

# name|pattern  (| as delimiter; patterns must not contain it)
CORE_PATTERNS=(
  'mac-home-path|(?:^|[^\w/])/Users/[^/\s"'"'"'`]+/'
  'linux-home-path|(?:^|[^\w/])/home/[^/\s"'"'"'`]+/'
  'email|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  'ipv4|(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)'
  'mac-address|\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'
  'ssh-fingerprint|SHA256:[A-Za-z0-9+/]{43}=?'
)

API_KEY_PATTERNS=(
  'openai-style|sk-[A-Za-z0-9]{20,}'
  'anthropic-style|sk-ant-[A-Za-z0-9_-]{20,}'
  'github-token|gh[pousr]_[A-Za-z0-9]{36,}'
  'aws-access-key|A(?:KIA|SIA)[0-9A-Z]{16}'
  'google-api|AIza[0-9A-Za-z_-]{35}'
  'jwt|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
  'slack-token|xox[baprs]-[A-Za-z0-9-]{10,}'
  'pem-private-key|-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----'
)

PATTERNS=()
if [ $NO_DEFAULT -eq 0 ]; then
  PATTERNS+=("${CORE_PATTERNS[@]}")
fi
if [ $API_KEYS -eq 1 ]; then
  PATTERNS+=("${API_KEY_PATTERNS[@]}")
fi
if [ -n "$EXTRA" ]; then
  if [ ! -r "$EXTRA" ]; then
    echo "regex-scan: extra patterns file not readable: $EXTRA" >&2
    exit 2
  fi
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    PATTERNS+=("$line")
  done < "$EXTRA"
fi

if [ ${#PATTERNS[@]} -eq 0 ]; then
  echo "regex-scan: no patterns enabled (did you pass --no-default without --api-keys/--extra?)" >&2
  exit 2
fi

TARGETS=("${DIRS[@]+"${DIRS[@]}"}" "${FILES[@]+"${FILES[@]}"}")

FOUND=0
for entry in "${PATTERNS[@]}"; do
  name="${entry%%|*}"
  pat="${entry#*|}"
  # -P = PCRE2, -n = line numbers, -H = with-filename. Binary files are skipped by default.
  out=$(rg -PnH --no-heading --color=never "${SKIPS[@]}" -e "$pat" "${TARGETS[@]}" 2>/dev/null || true)
  if [ -n "$out" ]; then
    FOUND=1
    printf '\n== %s ==\n%s\n' "$name" "$out"
  fi
done

if [ $FOUND -eq 1 ]; then
  exit 1
fi
exit 0
