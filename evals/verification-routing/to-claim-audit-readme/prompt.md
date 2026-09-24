---
description: "Verifying a README's factual statements by running things routes to claim-audit."
tags: [routing, claim-audit]
plugins: ["../../../skills/postmortem", "../../../skills/claim-audit"]
max_turns: 4
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Our README says the CLI supports four output formats and that every subcommand takes --json. Is any of that still true? Run things, don't just read the docs back to me.
