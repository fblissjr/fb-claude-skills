# Privacy tokens — catalog and rationale

*Last updated: 2026-04-21*

Every line in `scripts/privacy-tokens.sh` emits one literal string (or nothing, if the command is absent or unauthenticated). `scan-for-secrets` consumes those literals and finds each one — plus its escape variants — in the scanned target.

This doc explains what each token catches and when to customize.

## Shell user identity

| Command | What it catches |
|---------|-----------------|
| `echo "$HOME"` | `/Users/<you>` or `/home/<you>` wherever it's embedded |
| `echo "$USER"` | Bare username in logs, config files, user-agent strings |
| `id -un` | Same as `$USER`; fallback if env unset |
| `whoami` | Same; another fallback path |
| `echo "/Users/$USER"` | macOS home path even when `$HOME` was resolved elsewhere |
| `echo "/home/$USER"` | Linux home path ditto |

The dual emissions (`$HOME` + `/Users/$USER` + `/home/$USER`) are intentional. A log generated on macOS, pasted into a file on Linux, should still match against the macOS form.

## Hostname variants

| Command | What it catches |
|---------|-----------------|
| `hostname` | Whatever your shell reports (short or long) |
| `hostname -s` | Short form only (`laptop` vs `laptop.local`) |
| `hostname -f` | FQDN |
| `scutil --get ComputerName` | macOS "friendly" name (the name shown in System Settings → General → About) — shows in AirDrop, system logs |
| `scutil --get LocalHostName` | macOS Bonjour-advertised hostname (the computer's `.local` name on the LAN) |
| `scutil --get HostName` | macOS network hostname (often unset) |

Hostnames leak into shell prompts embedded in pasted terminal output, `uname -a` dumps, and many daemons' logs.

## Real-name / account identity

| Command | What it catches |
|---------|-----------------|
| `git config --global user.email` | Commit email if it appears inline in docs / generated content |
| `git config --global user.name` | Commit display name ditto |
| `git config --global github.user` | Configured GitHub username |
| `dscl . -read "/Users/$USER" RealName` | macOS full name from directory service |
| `getent passwd "$USER"` \| `cut -d: -f5` | Linux GECOS field (often full name) |
| `defaults read MobileMeAccounts` (macOS) | Apple ID email if signed in to iCloud |

## Dev tool identities

Each line is gated on `command -v <tool>`, so uninstalled tools are no-ops.

| Tool | Emits |
|------|-------|
| `gh` | GitHub login via `gh api user -q .login` |
| `npm` | npm registry username |
| `pnpm` | pnpm username (proxies to npm) |
| `yarn` | yarn berry username |
| `aws` | AWS account ID (from `sts get-caller-identity`) |
| `gcloud` | Active account email + project ID |

AWS account ID isn't a "secret" per se but is an identifier that ties generated logs / sample URLs / resource ARNs back to you. Worth scrubbing from shareable artifacts.

## Machine identity

SSH public keys (`~/.ssh/id_*.pub`) are emitted in full. A published pubkey isn't a security risk on its own, but its contents are a high-quality fingerprint: searching a public pubkey against your handles reveals "this user posted this log." Scrubbing them from pastes is standard privacy hygiene.

## Opt-in (commented out in the script)

These are disabled by default because they're rarely present in content you'd share, and enabling them adds scan noise:

| Command | Emits | When to enable |
|---------|-------|----------------|
| `system_profiler SPHardwareDataType ... Serial Number` | Mac serial (e.g. `C02XX...`) | Sharing raw system logs, hardware-report JSON |
| `cat /etc/machine-id` | Linux systemd machine ID | Sharing systemd journal excerpts |
| `ioreg -rd1 -c IOPlatformExpertDevice ... IOPlatformUUID` | macOS hardware UUID | Sharing ioreg / IOKit output |

Uncomment in your local copy if needed.

## Customizing

Two options:

1. **Project-scoped**: copy `privacy-tokens.sh` to `./privacy-tokens.sh` in the repo you're scanning, edit, pass it via `-c`.
2. **Machine-scoped**: copy once to `~/.scan-for-secrets.conf.sh`. `scan-for-secrets` uses that as the default config when run with no arguments or piped input.

Add additional literals with any shell command that writes to stdout. Examples:

```sh
# Your default SSH user@host for a specific bastion
echo "you@bastion.internal"

# A specific project slug that identifies you
echo "youruser/private-repo"

# Machine-specific env vars you regularly echo in commands
echo "$WORK_ACCOUNT_ID"
```

Blank lines and `#` comments are ignored. The script runs with `sh` by default; add a shebang (`#!/bin/bash`) if you need non-POSIX features.

## What this does NOT catch

Literal matching only finds strings whose exact form appears in the scanned content (or one of the five escape variants). It will **not** catch:

- Other users' home paths (e.g., `/Users/alice/...` in a fixture you copied) → use the regex pass
- Arbitrary emails in sample data → regex
- Rotated versions of your old username / hostname → add them explicitly
- Paraphrased or partial matches (e.g., "Alice's Mac" if you only tokenized the literal username)

The literal + regex passes are complementary. Run both for pre-share audits.
