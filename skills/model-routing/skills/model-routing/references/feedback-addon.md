## Record outcomes (agent-state)

After verifying a delegated result, record the outcome so delegation criteria can be tuned from data. If the `agent-state` CLI is not on PATH, skip silently — never block work on recording.

```
agent-state delegation record --task "<short summary>" --model <tier> \
  --outcome <accepted|revised|redone|escalated> \
  --verification <tests|diff_review|schema_validation|spot_check|none> \
  --domain <coding|data|docs|...> --orchestrator-model <your tier>
```

Review with `agent-state delegation stats`: a model/domain pair with a low acceptance rate means tasks of that shape should stay up-tier.
