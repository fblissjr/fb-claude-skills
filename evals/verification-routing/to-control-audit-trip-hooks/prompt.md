---
description: "Checking whether the repo's hooks and CI validator still fire, by tripping them, routes to control-audit."
tags: [routing, control-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

We have a pre-commit hook that's meant to block secrets, a couple of Claude Code hooks, and a validator that runs in CI. I honestly don't know if any of them still work. Go through them and actually try to set each one off.
