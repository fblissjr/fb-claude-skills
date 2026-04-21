# scan-for-secrets

*Last updated: 2026-04-21*

> **Built on [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets)** by Simon Willison, Apache 2.0. This plugin wraps that tool and composes a ripgrep regex pass on top. All literal-matching and escape-variant logic is Simon's work; credit and upstream fixes belong there.

Pre-share scanner. Finds leaked secrets and privacy-sensitive content in files you're about to share, commit, or publish. Two complementary passes:

- **Literal pass** — `scan-for-secrets` (upstream): finds exact strings you name, plus JSON / URL / HTML / backslash-doubled / unicode-escape variants of those strings. Use for secrets you can enumerate (API keys) and identities you can pull from the environment (your username, home path, git email, SSH keys).
- **Regex pass** — `ripgrep`: finds shape-based leaks you can't enumerate (other users' home paths, emails, IPv4, MAC addresses, SSH fingerprints, common API-token shapes).

## Installation

```bash
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install scan-for-secrets@fb-claude-skills
```

Runtime dependencies (on-demand, no pre-install required beyond these):

- `uv` — for `uvx scan-for-secrets` (one-shot invocation, no install)
- `ripgrep` (`rg`) — for the regex pass. `brew install ripgrep` / `apt install ripgrep`.

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `scan-for-secrets` | "scan for secrets", "pre-share scan", "redact home paths", "leaked credentials", "PII scan", "check before sharing" | Two-pass audit: literal secrets/identities + regex shapes |

## Invocation

```
/scan-for-secrets:scan-for-secrets
```

Or trigger automatically by asking about leaked secrets, pre-share audits, or privacy scans.

## Modes

1. **Secrets only** — you name the secret(s) to scan for:
   ```bash
   uvx scan-for-secrets "$OPENAI_API_KEY" -d .
   ```
2. **Privacy sweep** — auto-assembled from env + regex:
   ```bash
   uvx scan-for-secrets -d . \
     -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh
   bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -d . --api-keys
   ```
3. **Combined + redact** — literal pass with `-r`, then regex pass for manual review.

## What gets scanned for

Literal pass (via `privacy-tokens.sh`):

- `$HOME`, `$USER`, `whoami`, `id -un`
- Hostname variants (short, FQDN, macOS ComputerName / LocalHostName / HostName)
- Git `user.email`, `user.name`, `github.user`
- macOS full name (`dscl`), Linux GECOS full name, macOS Apple ID
- `gh` / `npm` / `pnpm` / `yarn` / `aws` / `gcloud` identities (if logged in)
- SSH public keys from `~/.ssh/id_*.pub`
- Opt-in: hardware serial, machine-id, IOPlatformUUID (commented out)

Regex pass (via `regex-scan.sh`):

- Core: macOS/Linux home paths (any user), emails, IPv4, MAC addresses, SSH fingerprints
- `--api-keys` adds: OpenAI / Anthropic / GitHub / AWS / Google / JWT / Slack / PEM private key shapes

## Background

`scan-for-secrets` does one thing perfectly: literal string matching with pre-computed escape variants. That's exactly what's needed for identity literals pulled from the environment. The regex pass is a thin ripgrep wrapper that handles the shape-based cases literal matching can't express. Two tools, one skill, no modifications to upstream.

## Credits

- Simon Willison — [`simonw/scan-for-secrets`](https://github.com/simonw/scan-for-secrets) (the literal pass and all its escape-variant logic)
- Andrew Gallant (BurntSushi) — [`ripgrep`](https://github.com/BurntSushi/ripgrep) (the regex pass engine)

## License

This plugin: same as the parent repo ([fb-claude-skills](https://github.com/fblissjr/fb-claude-skills)).

Upstream `scan-for-secrets`: Apache 2.0, © Simon Willison.
