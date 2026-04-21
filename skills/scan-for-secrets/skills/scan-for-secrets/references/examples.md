# Usage examples

*Last updated: 2026-04-21*

Concrete invocations for common situations.

## Pre-share an agent transcript

You just finished a long Claude Code session and want to share the transcript. The transcript contains your full home paths, environment variable dumps, and possibly an API key you echoed to stderr.

```bash
# From the repo root of wherever the transcript lives
uvx scan-for-secrets -d ./session-logs \
  -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh

bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh \
  -d ./session-logs --api-keys
```

Review both outputs. If clean, share. If not:

```bash
# Add -r to the literal pass for interactive redaction
uvx scan-for-secrets -d ./session-logs \
  -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh -r
```

Accepting the prompt writes `REDACTED` in place of every matched literal (and every escape variant). The regex pass is read-only — for regex matches, use your editor.

## Pre-publish a repo

Before `git push` to a public repo for the first time:

```bash
# From the repo root
uvx scan-for-secrets \
  "$(llm keys get openai)" \
  "$(llm keys get anthropic)" \
  -c skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh \
  -d .

bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -d . --api-keys
```

If the literal pass finds anything in committed files, **do not redact and push** — those secrets are already in your local git history. Rotate them, purge history (`git filter-repo` or BFG), then scan again.

## Audit a specific file before pasting

Quickest possible invocation:

```bash
uvx scan-for-secrets -c ~/.scan-for-secrets.conf.sh -f ./output.log
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -f ./output.log --api-keys
```

(Assumes you've copied `privacy-tokens.sh` to `~/.scan-for-secrets.conf.sh` as a one-time setup.)

## CI check on build artifacts

Exit code parity between the two passes lets you gate a job cheaply. Example `.github/workflows/` snippet:

```yaml
- name: Privacy scan of build output
  run: |
    set -e
    uvx scan-for-secrets -c ci/ci-privacy-tokens.sh -d ./dist
    bash ci/regex-scan.sh -d ./dist --api-keys
```

For CI use, ship a `ci-privacy-tokens.sh` that emits only CI-appropriate literals (service account emails from secrets, known internal hostnames) — NOT the dev-machine script, which would leak the CI runner's identity.

## First-time setup (machine default)

```bash
cp skills/scan-for-secrets/skills/scan-for-secrets/scripts/privacy-tokens.sh \
   ~/.scan-for-secrets.conf.sh
chmod +x ~/.scan-for-secrets.conf.sh
```

Now bare `scan-for-secrets` (with no args, no pipes) reads that config by default in any directory.

## Combining with manual review

The regex pass can be noisy. A common pattern is to pipe its output through `less` for scroll-review:

```bash
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh \
  -d . --api-keys 2>&1 | less -R
```

Or filter to a single pattern category:

```bash
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh -d . \
  | awk '/^== /{section=$2} section=="email"{print}'
```

## Custom patterns (work / org identifiers)

Drop a file at `./extra.patterns`:

```
employee-id|EMP-\d{6}
ticket|(?:INC|CR|BUG)-\d{6,}
internal-host|.*\.corp\.internal
```

Run with:

```bash
bash skills/scan-for-secrets/skills/scan-for-secrets/scripts/regex-scan.sh \
  -d . --extra ./extra.patterns
```
