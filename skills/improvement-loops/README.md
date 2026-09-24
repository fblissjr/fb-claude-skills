last updated: 2026-09-24

# improvement-loops

Standing prompts for long, mostly unattended runs, packaged so they are
invoked by name, versioned, and kept in one place. Each is written in XML-tagged
sections: a `<parameters>` block you override, and named sections the steps
refer to.

## Skills

| Skill | What it does |
|---|---|
| [improve](skills/improve/SKILL.md) | Repeatable runs toward the project's north star, its `VISION.md` (purpose, long-term direction, principles; not a spec), without breaking what the README, docs and tests promise today: speed, less code, visibility, rules turned into checks. A ledger, bookmarks and a scoreboard carry state between runs; steady or breakthrough goal; rules for working beside another session |
| [trim-agents-md](skills/trim-agents-md/SKILL.md) | Trims always-loaded agent instructions (`AGENTS.md`, `CLAUDE.md`, unconditional rules) to what an agent needs on its first edit. Finds every doc and check that reads the file before cutting, moves what is still true to the narrowest home, re-points consumers, and has a fresh-context reviewer confirm no rule was lost |
| [optimize](skills/optimize/SKILL.md) | One-session speed campaign against a hard target: base and branch worktrees, exact counts proven against wall-clock time, read-only reviewers, a re-check on the final commit |

All three are user-invoked only (`disable-model-invocation: true`): a run spends hours
and many subagents, so it starts only when someone types it. That also keeps
all of them out of the always-loaded skill listing.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install improvement-loops@fb-claude-skills
```

## Invocation

```
/improve                                          # defaults: steady goal, no focus, about 4 hours
/improve Goal: breakthrough; Focus: the export path
/optimize                                         # defaults: 1.2x on every primary benchmark
/optimize Target: 1.5x; Other sessions: mrblue is refactoring main
/trim-agents-md                                   # defaults: trim AGENTS.md and CLAUDE.md, keep the structure
/trim-agents-md Depth: rebuild; Hub: agents-md    # restructure, and move the content to AGENTS.md
```

Overrides are free text or `Key: value` pairs matching the `<parameters>` block
at the top of each loop file. Edit the parameters, not the body.

**For a run you will not watch, set a goal first.** Opus 5.5 sometimes ends a
turn with a progress report while work is still owed. Both loops tell it not to,
and Claude Code's `/goal` makes the harness hold it to that. Set the loop's done
list as the condition, for example `/goal every item in the improve run's done
list is met, with its evidence printed`, then invoke the skill. The goal's
evaluator reads only what the conversation shows, and both loops print their
evidence in the final report.

**To paste without installing,** copy `skills/improve/references/improvement-loop.md`
or `skills/optimize/references/optimizer-loop.md` into a session and edit its
parameters block.

## Why a skill body is only a router

Each SKILL.md is a few lines that point at the loop file. After auto-compaction
Claude Code re-attaches only the first 5,000 tokens of an invoked skill, and a
full loop sits close to that cut. So the loop lives in `references/`, and the
router's standing instruction is to re-read it, with the run's state files,
after a compaction. The state files are what the loops treat as the source of
truth anyway.

## The two files share text on purpose

The loops repeat some of the same rules: stop conditions, worktrees,
read-only reviewers, and re-checking on the final commit. Each is tuned as a
whole prompt, so the shared rules were left duplicated rather than factored
into a common file. When a shared rule changes, change it in both files.
