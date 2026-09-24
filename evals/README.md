last updated: 2026-09-24

# evals

`claude plugin eval` suites that span plugins live here. Suites for one plugin
live in that plugin's own `evals/`, such as `skills/writing/evals/`.

| Suite | Pins | Where |
|---|---|---|
| verification-routing | Each request lands on exactly one of postmortem, test-audit, control-audit, adversarial-verify, postmortem-index or claim-audit, or on none of them when it belongs to the built-in `/code-review` or `/verify` | `evals/verification-routing/` |
| writing | The `writing` plugin's house rules, graded by regex (one `llm` grader, for front-loading), plus its trigger and must-not-trigger routing | `skills/writing/evals/` |

Each case states the rule or route it pins in the `description:` field of its
`prompt.md`, and each grader states its claim in a `# claim:` comment.

## Run

Real runs call models on your account and must run outside the sandbox.

```bash
# routing: single arm, because without the plugins nothing in the family can fire
claude plugin eval . --tag routing --trust-plugin --ablation none --runs 1 --model claude-opus-5-5 --no-publish --json out.json
# writing: with and without the plugin
claude plugin eval skills/writing --trust-plugin --runs 1 --model claude-opus-5-5 --no-publish --json out.json
```

`--tag routing` is required from the repo root: discovery is recursive, so `.`
also finds `skills/writing/evals/`. Add `--max-cost-usd 0` to load and validate
every case without running one. Results land in `<eval dir>/results/`, which is
gitignored.

## Check the graders before spending

```bash
bun evals/check_graders.ts .
```

The eval CLI does not compile grader regexes, so a broken pattern loads fine
and fails silently at run time. This script compiles every pattern and checks
three things:
- each `not_contains` grader goes red on its case's original draft;
- every grader goes green on a hand-written compliant reply;
- each routing pattern matches exactly its intended skill and neither
  built-in.

It exits non-zero on any failure. When you add a case, add its compliant reply
to the script's `GREEN` table.
