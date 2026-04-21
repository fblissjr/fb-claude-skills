#!/bin/sh
# privacy-tokens.sh - emit privacy-sensitive identity literals for scan-for-secrets
#
# Use as: scan-for-secrets -c <this-script> [-d <dir>]
# Format:  one literal per line; blank lines and '# ...' ignored.
#
# Every command is defensive: missing tools / unset keys fall through silently.
# Copy to ~/.scan-for-secrets.conf.sh to make this the default config.

# --- Shell user identity ---
echo "$HOME"
echo "$USER"
id -un 2>/dev/null
whoami 2>/dev/null
echo "/Users/$USER"
echo "/home/$USER"

# --- Hostname variants ---
hostname 2>/dev/null
hostname -s 2>/dev/null
hostname -f 2>/dev/null
scutil --get ComputerName  2>/dev/null
scutil --get LocalHostName 2>/dev/null
scutil --get HostName      2>/dev/null

# --- Git identity ---
git config --global user.email 2>/dev/null
git config --global user.name  2>/dev/null
git config --global github.user 2>/dev/null

# --- Real-name / account identity ---
# macOS: directory service
dscl . -read "/Users/$USER" RealName 2>/dev/null | awk 'NR==2{$1=$1;print}'
# Linux: GECOS field
getent passwd "$USER" 2>/dev/null | cut -d: -f5 | cut -d, -f1
# macOS: Apple ID (if signed in to iCloud)
defaults read MobileMeAccounts 2>/dev/null \
  | awk -F'"' '/AccountID/{print $2}' \
  | head -1

# --- Dev tool identities (only if installed + logged in) ---
command -v gh     >/dev/null 2>&1 && gh api user -q .login 2>/dev/null
command -v npm    >/dev/null 2>&1 && npm whoami 2>/dev/null
command -v pnpm   >/dev/null 2>&1 && pnpm whoami 2>/dev/null
command -v yarn   >/dev/null 2>&1 && yarn npm whoami 2>/dev/null
command -v aws    >/dev/null 2>&1 && aws sts get-caller-identity --query Account --output text 2>/dev/null
command -v gcloud >/dev/null 2>&1 && gcloud config get-value account 2>/dev/null
command -v gcloud >/dev/null 2>&1 && gcloud config get-value project 2>/dev/null

# --- SSH public keys (each key's full content becomes a literal) ---
for f in "$HOME"/.ssh/id_*.pub; do
  [ -r "$f" ] && cat "$f"
done

# --- Opt-in: hardware / machine identifiers (uncomment if you share raw system logs) ---
# system_profiler SPHardwareDataType 2>/dev/null | awk -F': ' '/Serial Number/{print $2}'
# cat /etc/machine-id 2>/dev/null
# ioreg -rd1 -c IOPlatformExpertDevice 2>/dev/null | awk -F'"' '/IOPlatformUUID/{print $4}'
