# Advisor consults

A higher-tier advisor model is available in this project through `/advisor`.

## Spending rule

The advisor costs frontier-model tokens. It spawns only when the user runs
`/advisor` — never on your own initiative. A `PreToolUse` hook denies
unauthorized spawns, so attempting one wastes a turn.

When a consult would genuinely help and the user has not asked, say so in one
sentence and say what you would ask. Then continue without it. Do not raise it
repeatedly; a suggestion already declined is noise.

## When a consult is worth suggesting

Two moments carry measured payoff:

- **Early**, once you can describe the problem but before committing to an
  approach. Orientation first — finding files, reading sources — then advice.
- **Late**, after writes and test output exist, on work that turned out hard.

Least useful on short reactive steps where the tool output you just read
dictates the next action.

Concretely: a genuine design fork, an approach that is not converging, or an
interpretation you are about to build on that you cannot cheaply reverse.

## Weighing advice you receive

Give it serious weight. Adapt only on empirical failure or primary-source
evidence contradicting a specific claim. A passing self-test is not evidence
the advice is wrong — it is evidence your test does not check what the advice
checks.

If your own retrieved data points one way and the advisor points another, do
not silently switch. Surface the conflict to the user.

Report advice back close to verbatim. The user paid for those tokens; do not
summarize them away.
