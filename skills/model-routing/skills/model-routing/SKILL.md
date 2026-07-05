---
name: model-routing
description: Opt the current project into down-tier model delegation by installing a .claude/rules/model-delegation.md rule. The rule tells Claude to route well-specified data and coding tasks to a cheaper model in a subagent, keeping judgment-heavy work in the main loop. Use when the user says "set up model routing", "set up model delegation", "use cheaper models for subagents", "delegate to a lower-power model", or wants to remove or update that rule.
metadata:
  author: Fred Bliss
  version: 0.1.0
  last_verified: 2026-07-05
---

Install, update, or remove a per-project model-delegation rule. The rule is a plain `.claude/rules/` file: it loads at session start in that project only, needs no plugin installed to keep working, and is removed by deleting the file.

Design rationale: [VISION.md "route to the cheapest capable model"](https://github.com/fblissjr/fb-claude-skills/blob/main/VISION.md) — decomposition quality and model tiering are complements; well-scoped leaf tasks don't need the frontier model.

## Install

1. Determine the project root: the git repository root, or the working directory if not in a git repo. If the user names a different target project, use that.
2. Read `references/model-delegation.md` (relative to this skill) and write its content **verbatim** to `<project-root>/.claude/rules/model-delegation.md`, creating `.claude/rules/` if needed. Verbatim copy keeps installs identical across projects — do not regenerate or paraphrase the rule text.
3. If the target file already exists and differs, show the user the diff and ask before overwriting — it may carry local edits.
4. Tell the user: the rule loads automatically at the next session start in that project. For the current session, adopt the rule's behavior immediately since you have just read it.

## Update

Same as install; step 3's diff-and-confirm handles the existing file.

## Remove

Delete `<project-root>/.claude/rules/model-delegation.md`. Nothing else to clean up.

## What the rule says

Delegation criteria in brief (full text in `references/model-delegation.md`): route tasks that are well-specified, mechanical, and verifiable to the cheapest capable model in a subagent; keep design, ambiguity, user interaction, and verification of returned work in the main loop on the strongest model. Tiers are named only as examples so the rule survives model-lineup changes.
