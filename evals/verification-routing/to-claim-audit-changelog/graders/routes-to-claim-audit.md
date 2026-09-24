---
# claim: the request routes to claim-audit; scored in both arms so a run where nothing fires cannot pass.
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?claim-audit"'
arm: both
---
