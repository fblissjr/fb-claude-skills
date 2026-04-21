# Regex patterns — catalog and tuning

*Last updated: 2026-04-21*

`scripts/regex-scan.sh` runs ripgrep with a curated pattern set. This doc catalogs each pattern, its intent, known false positives, and tuning hints.

## Core patterns (always on)

### mac-home-path
```
(?:^|[^\w/])/Users/[^/\s"'`]+/
```
Matches `/Users/<anyuser>/...` not immediately preceded by a word character or slash. Guards against matching inside longer identifiers or relative paths.

**False positives:** macOS system paths like `/Users/Shared/...` match. If you regularly share content referencing `/Users/Shared`, exclude with `--extra` negative hints or grep-pipe the output.

### linux-home-path
```
(?:^|[^\w/])/home/[^/\s"'`]+/
```
Matches `/home/<anyuser>/...`. Same guard logic.

**False positives:** Some distro paths (`/home/linuxbrew`, `/home/travis`) will match. Review before acting.

### email
```
[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
```
Classic email regex. Catches most real addresses plus a lot of doc examples.

**False positives:** `user@example.com`, `test@localhost`, GitHub issue references with `@username` (only if preceded by a domain-like form), version suffixes like `foo@1.2.3`. The regex is intentionally permissive; prune output during review.

### ipv4
```
(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)
```
Four dot-separated numbers 0-999, not adjacent to other digits.

**False positives:** Semver strings (`1.2.3.4`), date-like patterns, large version codes. Worth keeping because real leaked IPs often appear in network logs.

Tuning: if you want to scope to likely-public IPs, combine with an inverted match for RFC 1918 ranges (`10.`, `172.16-31.`, `192.168.`, `127.`) and link-local. The shipped pattern is deliberately broad — redaction decisions should stay manual.

### mac-address
```
\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b
```
Six colon-separated hex pairs. Word-boundary anchored.

**False positives:** Embedded checksums that happen to share the shape (rare).

### ssh-fingerprint
```
SHA256:[A-Za-z0-9+/]{43}=?
```
Matches modern SSH key fingerprints (`ssh-keygen -lf <key>` output style). Hex MD5 fingerprints (`aa:bb:cc...`) overlap the mac-address pattern; review output if you see matches there.

## Opt-in API-key shapes (`--api-keys`)

These are intentionally off by default because the shapes are broad and produce false positives in documentation / examples. Enable when auditing content you believe *should not* contain any token-shaped strings.

### openai-style
```
sk-[A-Za-z0-9]{20,}
```
Catches `sk-` prefixed tokens 20+ chars. Matches many doc examples. OpenAI's real keys are significantly longer; tighten to `sk-[A-Za-z0-9]{40,}` if noise is a problem.

### anthropic-style
```
sk-ant-[A-Za-z0-9_-]{20,}
```

### github-token
```
gh[pousr]_[A-Za-z0-9]{36,}
```
Matches `ghp_` (personal), `gho_` (OAuth), `ghu_` (user-to-server), `ghs_` (server-to-server), `ghr_` (refresh). GitHub's canonical length for PATs is 36 chars after the prefix.

### aws-access-key
```
A(?:KIA|SIA)[0-9A-Z]{16}
```
Matches `AKIA` (long-lived) and `ASIA` (STS/temporary) prefixes. GitHub's own secret scanning uses the same shape.

### google-api
```
AIza[0-9A-Za-z_-]{35}
```
Google API keys (Maps, Firebase, etc.).

### jwt
```
eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}
```
Matches the `header.payload.signature` shape with plausible base64url-ish segments. Requires all three dot-separated base64url segments starting with `eyJ` (matches the canonical `{"alg":"..."` and `{"sub":"..."` JSON headers when b64-encoded).

**False positives:** Sample JWTs in tutorials. Real leaked JWTs are still worth finding.

### slack-token
```
xox[baprs]-[A-Za-z0-9-]{10,}
```
Legacy Slack token shapes (`xoxb-`, `xoxa-`, `xoxp-`, `xoxr-`, `xoxs-`). Newer Slack tokens may not match.

### pem-private-key
```
-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----
```
Header line of every PEM-encoded private key variant. A positive match here is almost always a real leak.

## Adding custom patterns

Pass `--extra <patterns-file>`. One pattern per line in `name|regex` form. Blank lines and `# ...` ignored. Example:

```
# Company-internal identifiers
employee-id|EMP-\d{6}
internal-ticket|(?:INC|CR)-\d{6,8}
vpn-dns|.*\.corp\.example\.com
```

Combine with `--no-default` if you want only your custom patterns.

## Performance

ripgrep's PCRE2 engine is fast but slower than its default Rust engine. On very large trees (10 GB+), the regex pass takes meaningful time. To cut scope:

- Narrow with `-f <specific-file>` instead of `-d <whole-repo>`
- Use `--no-default --extra <narrow.patterns>` for targeted sweeps
- Pipe filename allowlists via shell (`find ... | xargs bash regex-scan.sh -f ... -f ...`)

## What this does NOT catch

- Obfuscated secrets (base64 or hex-encoded, split across lines, concatenated at runtime) — these need the literal pass with the raw secret as input
- Shape-matching is probabilistic; a valid-looking token-shaped string may be test data, and a real token may have an unusual shape
- Non-text formats (images of terminals, PDFs without OCR) — neither pass reads them

Always treat scan output as a starting point for manual review, not a final verdict.
