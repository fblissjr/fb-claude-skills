---
description: "Suspicion that heavily mocked tests exercise nothing real, across a directory, routes to test-audit."
tags: [routing, test-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

A lot of the tests in tests/integration mock the database so heavily I'm not sure they touch anything real. Go through them and tell me which would still pass if the query layer returned garbage.
