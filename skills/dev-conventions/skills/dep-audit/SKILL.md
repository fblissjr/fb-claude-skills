---
name: dep-audit
description: >-
  Audit project dependencies for known vulnerabilities using uv audit (Python) and bun audit (JS/TS).
  Use when user says "audit dependencies", "check for vulnerabilities", "security audit",
  "check deps", "are my packages safe", "CVE check", "dependency security", "vulnerability scan".
  Invoke with /dev-conventions:dep-audit.
metadata:
  author: Fred Bliss
  version: 0.5.0
  last_verified: 2026-04-13
---

# Dependency Security Audit

## Quick audit

Run the appropriate command for the detected project type:

| Project type | Command | What it checks |
|-------------|---------|---------------|
| Python (uv) | `uv audit` | All deps + extras against OSV database |
| Python (frozen) | `uv audit --frozen` | Audit without updating lock |
| JavaScript (bun) | `bun audit` | Installed packages against npm advisory database |
| JavaScript (filtered) | `bun audit --audit-level high` | Only high/critical severity |

## Interpreting results

### Python (uv audit)

uv audit checks against the OSV (Open Source Vulnerabilities) database. It reports:
- Package name and installed version
- Vulnerability ID (GHSA-xxxx, PYSEC-xxxx)
- Severity and affected version range
- Whether a fix version is available

To ignore a known/accepted vulnerability: `uv audit --ignore GHSA-xxxx-xxxx-xxxx`

### JavaScript (bun audit)

bun audit checks the npm advisory database. Use `--json` for machine-readable output.

## Transitive dependency analysis

Direct dependencies are only part of the attack surface. Inspect the full tree:

| Task | Python | JavaScript |
|------|--------|------------|
| Full dependency tree | `uv tree` | `bun pm ls --all` |
| Why is X installed? | `uv tree --package X --invert` | `bun pm why X` |
| Direct deps only | `uv tree --depth 1` | `bun pm ls` |

## Remediation workflow

1. **Audit**: `uv audit` / `bun audit`
2. **Assess each vulnerability**:
   - Check who depends on it: `uv tree --package <pkg> --invert`
   - Determine if the vulnerable code path is reachable
3. **Upgrade** (if fix available):
   - `uv add <pkg>==<fix-version>` / `bun add <pkg>@<fix-version>`
   - Run tests after each upgrade
4. **Accept risk** (if no fix):
   - Document with `--ignore` flag
   - Note the rationale in a comment or the session log
5. **Record**: include all changes in the session log dependency changes section (see /dev-conventions:doc-conventions)

## CI integration

Use strict mode that fails the build on any vulnerability:

```bash
# Python -- exits non-zero if vulnerabilities found
uv audit --frozen

# JavaScript -- exits non-zero if moderate+ found
bun audit --audit-level moderate
```

## When to audit

- After adding or upgrading any dependency
- Before releases or deployments
- Periodically (weekly or on CI schedule)
- When notified of a new CVE affecting your stack
