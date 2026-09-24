---
description: "A single new threshold about to be relied on routes to adversarial-verify, not test-audit."
tags: [routing, adversarial-verify]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

I just set the similarity cutoff in dedupe.py to 0.82 and the new check passes on the fixtures. Before I rely on it, I want to see that it isn't a check that passes no matter what. Build the case where it should reject something and see if it does.
