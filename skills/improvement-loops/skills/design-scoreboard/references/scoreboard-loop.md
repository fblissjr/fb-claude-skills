Choose what an improvement or optimizer loop should climb for this project and this goal, and what must not get worse while it climbs. The output is a small set of scenarios, each with its measurements. Each measurement has a role, evidence that it tracks the outcome it stands for, and the cheapest way it could be faked, paired with the check that would catch that.

Done means:
- every goal metric is measured on the project's real path, or is shown to track something that is, and its noise is measured;
- every goal metric has guardrails and at least one counter-check aimed at the cheapest way to fake it;
- every proxy has evidence that it tracks its outcome, or is marked unproven and left out of what the loop climbs;
- the scenarios are written as data in the loop state, and the fill for AGENTS.md's Measurement section is proposed, not written;
- the report leads with what needs the owner's decision.

<parameters>
- Goal: from the invocation, such as "faster cold start", "less code in the parser", "fewer silent failures" or "better summaries". (If none is given, draw two or three candidates from the North star and ask which one.)
- Focus: none. (Or name an area, a user journey or a plan item.)
- Loop: improve. (Or "optimize": then the goal is speed, and the primary benchmarks are what you are choosing.)
- Calibration budget: about an hour of measuring.
- Existing scoreboard: extend it. (Or "review": re-check the scenarios already in the loop state for drift, noise and ways to game them, and propose retirements.)
</parameters>

<how_to_run>
When a step doesn't need my input, keep going. Put status notes in the same message as your next action.

Stop and ask only when the goal is ambiguous enough that different readings need different measurements, or before anything destructive or outside the repository. The repo's own rules apply, AGENTS.md's Measurement section above all. Where it and this prompt disagree, follow it and name the conflict under "Needs from me".
</how_to_run>

<principles>
- **No single number.** A loop climbs whatever it is given, including in directions nobody wanted. Every goal metric comes with guardrails, which say what must not get worse, and counter-checks, which show the gain is real rather than gamed.
- **The outcome first, the instrument second.** Name what a user or the owner would notice: a page ready sooner, a bug class that stops recurring, fewer errors a reviewer finds. Then find the cheapest reliable way to measure it.
- **A proxy earns its place by tracking the outcome.** Move it on purpose (a known-slow commit, a deliberate regression, a toy fix) and show the outcome moves with it. Drop a proxy that doesn't track, however convenient it is to climb.
- **Exact counts where they are proven to track.** Instruction, allocation and call counts, and the project's own counters, give a clean signal in one run. Wall-clock time is what users feel, and it is noisy.
- **Know the noise.** Repeat each measurement enough times to see its spread; a difference inside it is zero.
- **Frozen once used.** A scenario with scoreboard rows is never edited. Add a new one instead; retiring one is the owner's call.
- **Metrics follow the goal.** Record which goal each scenario was chosen for and the condition that retires it. When the goal changes, run this again in review mode.
</principles>

<orient>
Read AGENTS.md: the North star, Where things live, Commands and Measurement. Then read what the project already measures: tests, benchmarks, CI timings, its own reports, counters and logs, and the sharp-edges record. If the loop state has scenarios, a scoreboard or a ledger, read them too. Name the real path: how users actually run the project.
</orient>

<candidates>
Gather candidates from four sources:
1. What users feel on the real path: latency, errors, output quality, steps to finish a task.
2. What the project already counts: tests, CI results, its own reports and counters, logs.
3. What the goal implies. Use <patterns> as a starting point.
4. What the loop could fake. For each candidate, write the cheapest change that would move the number without improving the outcome.

When the project has several distinct journeys or components, give each to its own read-only subagent, and ask for candidates with the file and line, how each is measured, and its cheapest cheat. Check each one's evidence before adopting it.
</candidates>

<patterns>
A starting point for thinking, not a menu:

| Goal | Goal metric | Guardrails | Counter-check against gaming |
|---|---|---|---|
| Speed | Wall-clock time on the real path, plus exact counts proven to track it | Tests pass; outputs identical; peak memory; startup time | Cold really is cold; inputs aren't special-cased; the benchmark and its harness are unchanged |
| Less code | Lines, files and dependencies removed, per layer | Tests pass; public API unchanged; behaviour on the real path | Tests weren't deleted to make code look dead; logic didn't move into config or strings |
| Reliability | Silent failures turned loud; error rate on the real path | Tests pass; latency | Errors weren't reclassified, muted or caught and dropped |
| Output quality (models, rendering, search) | A graded eval set with held-out cases | Cost; latency | The grader agrees with a human-graded sample; held-out cases were never seen while tuning |
| User experience | Time to a usable screen; layout shifts; steps to finish a task | Accessibility checks; visual regressions | Taste calls go to the owner as before-and-after pairs, never to a number |
| Cost | Tokens or money per task | The quality eval | Quality holds on the held-out set |
</patterns>

<validate>
For each metric you intend to keep:
1. Run it on the base commit enough times to see its spread, and record the conditions.
2. For a proxy, show that it tracks its outcome with a deliberate move.
3. Estimate what one run costs in time and money.
4. List its hazards: caches, editable installs, thermal throttling, shared machines.
5. Where it is cheap, try the cheapest cheat in a scratch worktree and confirm that a counter-check catches it. `/postmortem:adversarial-verify` is this move, if it is installed.

Leave out anything you couldn't validate, and say why.
</validate>

<write>
- **Scenarios.** Write one file per scenario in the loop state's `scenarios/` folder (its location is under AGENTS.md's Where things live). If no folder is named, use `.loops/` in the main checkout, list it in `.git/info/exclude`, and ask the owner to name one. Each file holds:
  - its name, and the command that runs it on the real path;
  - its start state, cold or warm, and how that state is ensured;
  - each metric with its role (goal, guardrail or counter-check), unit, direction and measured noise;
  - the validity evidence, and the cheapest cheat with the check that catches it;
  - the goal it was chosen for, and its retirement condition.
- **AGENTS.md.** Propose the fill for its Measurement section (real path, primary benchmarks, instruments, hazards) under "Needs from me". Don't edit the tracked file yourself.
- **Existing scenarios.** Never edit a scenario that has scoreboard rows. Propose retirements to the owner.
</write>

<report>
Your last message starts with these headings, in this order:
- Needs from me: approval of the metric set, the proposed AGENTS.md fill, and any retirements, each with your recommendation.
- The scoreboard: a table of metric, scenario, role, unit, direction, noise, validity evidence, and cheapest cheat with its check.
- Left out: candidates you rejected and why (didn't track, too noisy, too costly, gameable with no check).
- Not confirmed: anything you couldn't measure or verify, and where you looked.
</report>
