last updated: 2026-08-13

# grilling

A design interview that works the problem as a tree instead of asking questions
in the order they occur.

## Skills

| Skill | What it does |
|---|---|
| [grilling](skills/grilling/SKILL.md) | Interview until a plan is fully specified: rounds over a design tree, every question carrying a recommended answer, facts looked up rather than asked |

## Installation

```
/plugin marketplace add fblissjr/fb-claude-skills
/plugin install grilling@fb-claude-skills
```

## The idea in one paragraph

The **frontier** is every decision whose prerequisites are already settled. Ask
that whole set in one round, wait, then recompute it from the answers. A
question whose answer depends on another open question belongs to a later round,
because asking it early produces an answer the user will revise, and revised
answers invalidate whatever was built on them.

Two rules do most of the work. Every question carries your recommended answer,
so the user makes one judgment rather than two. And facts are the agent's job:
anything the filesystem, config, or codebase can settle gets looked up, never
asked. Only decisions go to the user.

## It's working if

- Questions arrive in batches, not one at a time.
- You are answering "which of these" rather than "go and find out".
- Later rounds are about things the earlier rounds made askable, not repeats.
- The session ends because nothing is left, not because it ran long.

## Credit

Adapted from `grilling` in [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT). Emoji stripped per house style, an `AskUserQuestion` path added for small
frontiers, and the fact-finding instruction aligned with this repo's delegation
practice.
