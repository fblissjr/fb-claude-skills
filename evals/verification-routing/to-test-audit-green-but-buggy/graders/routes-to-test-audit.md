---
# claim: the request routes to test-audit; scored in both arms so a run where nothing fires cannot pass.
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?test-audit"'
arm: both
---
