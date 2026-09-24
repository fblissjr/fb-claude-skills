---
description: "Checking that a changed flow works in the running app belongs to the built-in verify; no verification-family skill fires."
tags: [routing, none]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

I changed the login redirect. Start the app and walk through the login flow to make sure it actually works now.
