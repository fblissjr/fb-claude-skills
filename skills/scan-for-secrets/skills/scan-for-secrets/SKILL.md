---
name: scan-for-secrets
argument-hint: "[paths to scan, default whole repo]"
description: >-
  Pre-share scan for leaked secrets and privacy-sensitive content. Wraps simonw/scan-for-secrets
  for literal matching (with JSON/URL/HTML/backslash/unicode escape variants) and composes a
  ripgrep regex pass for shape-based leaks (other users' home paths, emails, IPv4, MAC, JWTs, API keys).
  Use when user says "scan for secrets", "check for leaked credentials", "pre-share scan",
  "redact home paths", "PII scan", "strip my username from transcripts", "scan logs before publishing",
  "check before sharing", "audit before commit", "find leaked API keys", "scan agent transcript".
allowed-tools: "Read, Bash(uvx scan-for-secrets *), Bash(bash ${CLAUDE_SKILL_DIR}/scripts/regex-scan.sh *)"
---

# scan-for-secrets

Scan files before sharing them: a repo about to go public, an agent transcript,
a log, a file about to be pasted somewhere.

Literals for identities you can name, regex for shapes you can't. Your home
path, username, git email and SSH keys are literal strings, which
[simonw/scan-for-secrets](https://github.com/simonw/scan-for-secrets) finds
along with every common escape variant. Other users' home paths, arbitrary
emails and API-key shapes cannot be enumerated, so a ripgrep pass covers them.

<how_to_run>
Targets come from `$ARGUMENTS` (`-d <dir>` or `-f <file>`, repeatable); the
default is the whole repo.

Named secrets only:

```bash
uvx scan-for-secrets "$OPENAI_API_KEY" "$ANTHROPIC_API_KEY" -d <target>
```

Privacy sweep, both passes:

```bash
# literals from the environment: HOME, USER, hostnames, git and account identities, SSH keys
uvx scan-for-secrets -d <target> -c ${CLAUDE_SKILL_DIR}/scripts/privacy-tokens.sh

# shapes: other users' home paths, emails, IPv4, MAC, SSH fingerprints
bash ${CLAUDE_SKILL_DIR}/scripts/regex-scan.sh -d <target>
```

- `--api-keys` on the regex pass adds OpenAI, Anthropic, GitHub, AWS, Google,
  JWT, Slack and PEM private-key shapes. `--extra <file>` adds `name|pattern`
  lines; `--no-default` drops the core set.
- Named secrets and `-c` combine in one literal pass.
- `-r` on the literal pass redacts: it lists every match, prompts
  `Proceed? [y/N]`, and on yes replaces each variant with `REDACTED` in place.
  The prompt needs a terminal, so give the user the `-r` command to run
  rather than running it through Bash.
- Both passes exit 0 when clean and 1 on a match (2 means nothing to scan for,
  or a usage error), so either can gate CI read-only.
- Copying `privacy-tokens.sh` to `<HOME>/.scan-for-secrets.conf.sh` makes it
  the default config for a bare `scan-for-secrets`.
</how_to_run>

<gotchas>
- The regex pass is read-only, because auto-replacing a shape (every email)
  destroys legitimate content. To redact a regex hit, add the matched string
  to the literal pass with `-r`, or edit it by hand.
- Regex false positives: IPv4 matches version strings, and the email pattern
  matches doc examples like `user@example.com`. Review before acting.
- The literal pass skips binary files (a null byte in the first 8KB).
- Both passes skip `.git`, `.hg`, `.svn`, `node_modules`, `__pycache__`,
  `.venv` and `venv`; the regex pass also skips `.mypy_cache`, `.ruff_cache`
  and `.pytest_cache`.
- A secret found anywhere (scan output, commit history, a shared file) is
  compromised: it gets rotated. Redaction cleans only the artifact in hand,
  and a secret in committed files is already in git history.
</gotchas>

<report>
Each hit by file and line, grouped by pass and pattern, with likely false
positives marked as such, then what the user should rotate or redact.
</report>

References, read when a call needs them: `references/privacy_tokens.md` (what
each literal catches, opt-in lines for hardware identifiers),
`references/regex_patterns.md` (pattern catalog, false positives, tuning),
`references/examples.md` (transcript, pre-publish, CI and custom-pattern
recipes).
