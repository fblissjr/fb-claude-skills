---
description: "Outcome: plain-language-us front-loads the conclusion (impact and cause before chronology) and turns the draft's actorless passives into active voice, keeping the certificate cause and the 40 percent figure."
tags: [plain-language-us, outcome]
max_turns: 6
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

Tidy this up before I send it to the whole org. Just give me the revised version.

At 09:14 on Tuesday, an alert was received by the on-call engineer indicating elevated error rates on the sign-in service. Initially it was thought that the issue was related to the deploy that had gone out that morning, and a rollback was performed, but the errors continued. After further investigation it was determined that requests to the internal auth proxy were failing. Eventually, at 11:02, it was discovered that the TLS certificate on the auth proxy had expired overnight. The certificate was renewed — after some back and forth about who owned it — and service was restored at 11:20. As a result of this incident, approximately 40% of sign-in attempts failed for roughly two hours. A monitor for certificate expiry will be added.
