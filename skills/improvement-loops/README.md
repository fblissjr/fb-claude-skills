last updated: 2026-09-24

# improvement-loops

Standing prompts for long, mostly unattended runs, packaged so they are
invoked by name, versioned, and kept in one place. Each is written in
XML-tagged sections: a `<parameters>` block you override, and named sections
the steps refer to.

## How the pieces fit

```
templates/AGENTS.md ── the repo's hub: North star, Where things live, Commands,
        │               How to work, Other sessions, Measurement, Reporting, Loop state
        │
/design-scoreboard ──── chooses what to climb and what must not get worse
        │               → scenarios/ in the loop state, Measurement fill proposed
        ▼
/improve  /optimize ─── climb it; state in the loop folder; report leads with
                        "Needs from me"
/trim-agents-md ─────── keeps the hub short as it grows
```

The loops cite the AGENTS.md sections by name and keep only what a run adds.
A repo without those sections gets them listed under "Needs from me", with the
template as the starting point. The North star is a direction, not a spec: the
loops use it to choose a direction and break ties, never as requirements.

## Skills

| Skill | What it does |
|---|---|
| [improve](skills/improve/SKILL.md) | Repeatable runs in the direction the North star points, without breaking what the project does today: speed, less code, visibility, rules turned into checks. A ledger, bookmarks and a scoreboard carry state between runs; steady or breakthrough goal; rules for working beside another session |
| [optimize](skills/optimize/SKILL.md) | One-session speed campaign against a hard target: base and branch worktrees, exact counts proven against wall-clock time, read-only reviewers, a re-check on the final commit |
| [design-scoreboard](skills/design-scoreboard/SKILL.md) | Chooses what a loop climbs for this project and goal: goal metrics on the real path, guardrails, and counter-checks aimed at the cheapest way to fake each gain, so no single number can be reward-hacked. Proves each proxy tracks its outcome and measures its noise. Rerun in review mode when the goal changes |
| [trim-agents-md](skills/trim-agents-md/SKILL.md) | Tightens always-loaded agent instructions: every line must prevent a mistake, the rest moves to where it loads when it matters (path-scoped rule, skill, hook or test, status doc) or goes. Fills the gaps a newcomer falls into (commands, done criteria, stops, hazards, settled decisions), re-points consumers, and verifies with a fresh-context review and spot-tested tasks |

All four are user-invoked only (`disable-model-invocation: true`). A run
spends time and many subagents, so it starts only when someone types it, and
none of them costs anything in the always-loaded skill listing.

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install improvement-loops@fb-claude-skills
```

## Invocation

```
/design-scoreboard Goal: faster cold start; Focus: the CLI
/design-scoreboard Existing scoreboard: review    # re-check for drift and gaming when the goal changes
/improve                                          # defaults: steady goal, no focus, about 4 hours
/improve Goal: breakthrough; Focus: the export path
/optimize                                         # defaults: 1.2x on every primary benchmark
/optimize Target: 1.5x; Other sessions: mrblue is refactoring main
/trim-agents-md                                   # defaults: trim AGENTS.md and CLAUDE.md, keep the structure
/trim-agents-md Depth: rebuild; Hub: agents-md    # restructure, and move the content to AGENTS.md
```

Overrides are free text or `Key: value` pairs matching the `<parameters>` block
at the top of each prompt file. Edit the parameters, not the body.

**For a run you will not watch, set a goal first.** Opus 5.5 sometimes ends a
turn with a progress report while work is still owed. The loops tell it not
to, and Claude Code's `/goal` makes the harness hold it to that. Set the loop's
done list as the condition, for example `/goal every item in the improve run's
done list is met, with its evidence printed`, then invoke the skill. The goal's
evaluator reads only what the conversation shows, and the loops print their
evidence in the final report.

**To paste without installing,** copy a prompt from its skill's `references/`
into a session, and give the repo the sections of `templates/AGENTS.md` it
cites.

## Why a skill body is only a router

Each SKILL.md is a few lines that point at its prompt file. After
auto-compaction, Claude Code re-attaches only the first 5,000 tokens of an
invoked skill, and a full prompt sits near that cut. So the prompt lives in
`references/`. The router's standing instruction is to re-read it, with the
run's state files, after a compaction. The state files are what the loops
treat as the source of truth anyway.

## The template costs every session

`templates/AGENTS.md` carries general rules (how to work, measurement,
reporting, loop state) as well as the project facts, because the loops cite
those rules by section. A repo that adopts it pays for every line in every
session. Run `/trim-agents-md` on the filled-in result. In a repo that rarely
runs a loop, move the sections only a loop needs (Loop state, most of
Measurement and Reporting) behind a one-line pointer.
