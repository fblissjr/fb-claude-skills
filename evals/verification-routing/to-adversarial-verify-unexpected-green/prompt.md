---
description: "One test that stayed green after a deliberate break routes to adversarial-verify."
tags: [routing, adversarial-verify]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Weird one: I deliberately broke the date parser and its test still passed. I expected it to fail. Figure out whether that test is even reaching the parser.
