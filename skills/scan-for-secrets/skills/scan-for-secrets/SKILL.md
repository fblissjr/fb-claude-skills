---
name: scan-for-secrets
description: >-
  Pre-share scan for leaked secrets and privacy-sensitive content. Wraps simonw/scan-for-secrets
  for literal matching (with JSON/URL/HTML/backslash/unicode escape variants) and composes a
  ripgrep regex pass for shape-based leaks (other users' home paths, emails, IPv4, MAC, JWTs, API keys).
  Use when user says "scan for secrets", "check for leaked credentials", "pre-share scan",
  "redact home paths", "PII scan", "strip my username from transcripts", "scan logs before publishing",
  "check before sharing", "audit before commit", "find leaked API keys", "scan agent transcript".
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-04-21
allowed-tools: "Bash,Read"
---

# scan-for-secrets

Scan files and directories before sharing. Catches literal secrets you name, privacy-sensitive identity literals pulled from your environment, and shape-based patterns a literal scan can't express.

Wraps [simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) (literal pass) and composes ripgrep (regex pass).

## When to use

- Pre-publish audit of a repo you're about to make public
- Pre-share sweep of an agent transcript, log, or sample output
- Before pasting a file into chat, a blog post, or a support ticket
- CI gate on generated artifacts (optional; read-only mode)

## Core principle

**Literals for identities you can name, regex for shapes you can't.**

- Your home path, username, git email, SSH keys — literal strings. `scan-for-secrets` handles these natively, including all common escape variants.
- Other users' home paths, arbitrary emails in fixtures, API key shapes — you can't enumerate them. Regex pass with `ripgrep`.

The skill composes both into one workflow; no modifications to simonw's tool.

## Decision matrix

| Situation | Command | Notes |
|-----------|---------|-------|
| You know the specific secret(s) | `uvx scan-for-secrets "$KEY" -d <path>` | Direct passthrough |
| Pre-share sweep of your own leakage | Privacy mode (literal + regex) | See Process below |
| Audit a repo / log for any leak | Combined mode | Most thorough |
| Actually strip found secrets | Add `-r` to the literal pass | Prompts before rewriting |
| CI check (read-only) | Privacy or combined, no `-r` | Exit 1 fails the job |

## Process

Command examples below assume you're invoking from the repo root of `fb-claude-skills` (or a repo where this plugin is installed). If invoked from elsewhere, substitute the install path.

### Mode 1 — secrets only (you know what to scan for)

```bash
uvx scan-for-secrets "$OPENAI_API_KEY" "$ANTHROPIC_API_KEY" -d .
```

Positional args, piped stdin, or `-c <config>` all work. Exit 0 = clean, 1 = matches, 2 = no secrets provided. See `uvx scan-for-secrets --help` for the full surface.

### Mode 2 — privacy sweep (auto-assembled from env + regex)

Two commands; run both. Paths assume you invoke from the repo root.

```bash
# Pass A: literals from your environment (HOME, USER, git email, SSH keys, etc.)
uvx scan-for-secrets -d <target> \
  -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh

# Pass B: shape-based patterns (other users' paths, emails, IPv4, MAC, SSH fingerprints)
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -d <target>
```

Add `--api-keys` to pass B to also sweep common API-token shapes (OpenAI, Anthropic, GitHub, AWS, Google, JWT, Slack, PEM private keys).

If you want `scan-for-secrets` to pick up the privacy config without `-c` on every call, copy it once:

```bash
cp skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh \
   ~/.scan-for-secrets.conf.sh
```

Then bare `scan-for-secrets` uses it by default.

### Mode 3 — combined (privacy + named secrets + redact)

```bash
# Literal pass with extra named secrets AND the privacy bundle AND redaction
uvx scan-for-secrets "$KEY1" "$KEY2" \
  -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh \
  -d <target> -r

# Then regex pass (read-only; review output manually)
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -d <target> --api-keys
```

`-r` shows all literal matches first, then prompts `Proceed? [y/N]`. Declining exits 1 without rewriting. Accepting replaces every variant (including escape forms) with `REDACTED` in place.

## Privacy token bundle

`scripts/privacy-tokens.sh` emits one literal per line. Defensive: missing tools fall through silently. Covers: `$HOME`, `$USER`, `whoami`, `id -un`, hostnames (short/FQDN/ComputerName/LocalHostName on macOS), git `user.email`/`user.name`/`github.user`, macOS `dscl` RealName, Linux GECOS full name, macOS Apple ID, `gh`/`npm`/`pnpm`/`yarn`/`aws`/`gcloud` identities if logged in, SSH public keys from `~/.ssh/id_*.pub`.

Opt-in lines (commented) for hardware serial, machine-id, and IOPlatformUUID are in the script; uncomment only if you share raw system logs.

Rationale per token: see `references/privacy_tokens.md`.

## Regex pattern bundle

`scripts/regex-scan.sh` wraps ripgrep. Core patterns (always on): macOS/Linux home paths, email, IPv4, MAC address, SSH key fingerprint. Opt-in `--api-keys` adds: OpenAI-style, Anthropic-style, GitHub tokens, AWS access keys, Google API keys, JWTs, Slack tokens, PEM private keys.

Flags: `-d <dir>` / `-f <file>` (repeatable), `--api-keys`, `--no-default`, `--extra <patterns-file>`.

Full pattern catalog + false-positive notes: see `references/regex_patterns.md`.

## Redaction workflow

`-r` is only available on the literal pass (scan-for-secrets). The regex pass is read-only by design — auto-replacing pattern matches (e.g., stripping every email) risks destroying legitimate content. If you want to redact regex-matched content, either:

1. Copy the matched strings into your secrets list and re-run the literal pass with `-r`, or
2. Use `sed` / your editor with the matched lines as a manual review checklist.

## Limits

- **Regex false positives.** IPv4 matches any four dotted numbers (version strings, build numbers). Email regex matches doc examples (`user@example.com`). Review before acting. Tuning hints: `references/regex_patterns.md`.
- **Literal pass skips binary files.** Detected by null bytes in first 8KB.
- **Skip dirs.** `.git`, `.hg`, `.svn`, `node_modules`, `__pycache__`, `.venv`, `venv`, plus `.mypy_cache`, `.ruff_cache`, `.pytest_cache` in the regex pass.
- **Not a substitute for rotation.** If a real secret appears anywhere (scan output, commit history, shared file), assume it's compromised and rotate it. Redaction only cleans the artifact in your hand.

## References

- Upstream: https://github.com/simonw/scan-for-secrets (Apache 2.0)
- PyPI: https://pypi.org/project/scan-for-secrets/
- Local fork: `~/workspace/scan-for-secrets`
- Examples: `references/examples.md` — pre-share log audit, pre-publish repo, CI integration
