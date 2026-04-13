last updated: 2026-04-13

# dep-audit-scan

Standalone bash script that scans directories for Python and JavaScript projects, runs dependency vulnerability audits on each, and produces a summary report. No installation required -- just needs `uv` and/or `bun` on `PATH`.

## Prerequisites

- `uv` (for Python projects) -- `brew install uv`
- `bun` (for JavaScript projects) -- `curl -fsSL https://bun.sh/install | bash`

Both are optional. The script skips project types whose tool is missing.

## Usage

### Standalone (terminal)

```bash
# scan default directories (~/claude, ~/workspace, ~/projects, ~/code, ~/dev, ~/src)
./tools/dep-audit-scan.sh

# scan specific directories
./tools/dep-audit-scan.sh ~/work ~/my-projects

# JSON output for downstream processing
./tools/dep-audit-scan.sh --json

# auto-fix by upgrading vulnerable packages in lock files
./tools/dep-audit-scan.sh --fix

# combine flags
./tools/dep-audit-scan.sh --fix --json ~/workspace

# help
./tools/dep-audit-scan.sh --help
```

### From Claude Code

Ask Claude to run it directly:

```
> Run the dep audit scan on my workspace
> Scan ~/projects for dependency vulnerabilities
> Run tools/dep-audit-scan.sh --fix on ~/workspace
```

Or use the dep-audit skill for per-project auditing:

```
> /dev-conventions:dep-audit
```

The skill covers single-project workflows (audit, interpret, remediate, record). The script covers cross-project scanning.

## What it does

1. Finds `pyproject.toml` and `package.json` files up to 3 levels deep
2. Skips non-project directories (node_modules, .venv, .git, dist, build, etc.)
3. Skips uv workspace members (audited from root)
4. Runs `uv audit` (Python) or `bun audit` (JavaScript) on each project
5. Reports per-project status: clean, vulnerable (with CVE details), or skipped
6. Produces a summary with total counts and a list of vulnerable projects

## Output

```
=== Dependency Audit Scan ===
Scanning: /Users/you/claude /Users/you/workspace
Tools: uv=/opt/homebrew/bin/uv bun=/Users/you/.bun/bin/bun

[1] ~/claude/my-project (python)
  clean
[2] ~/workspace/old-app (python)
  VULNERABLE (3 issues)
    requests 2.31.0 has 1 known vulnerability:
      Fixed in: 2.33.0
      Advisory information: https://nvd.nist.gov/vuln/detail/CVE-2026-25645

=== Summary ===
Projects scanned: 2
Clean: 1
Vulnerable: 1 (3 total vulnerabilities)
Skipped: 0
```

## Flags

| Flag | Effect |
|------|--------|
| `--json` | Append JSON array of results after the text summary |
| `--fix` | For each vulnerable Python project with a lock file, upgrade vulnerable packages via `uv lock --upgrade-package` and re-audit |
| `--help` | Show usage |
| `dir ...` | Override default scan directories |

## Exit code

- `0` if no vulnerabilities found across all projects
- `1` if any vulnerabilities found (useful for CI gating)

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `UV` | auto-detected | Path to `uv` binary |
| `BUN` | auto-detected | Path to `bun` binary |

## Skipped projects

Projects are skipped when:
- No `uv.lock` and dependencies can't be resolved (Python)
- No `node_modules` directory (JavaScript -- run `bun install` first)
- The project is a uv workspace member (audited from the workspace root)
