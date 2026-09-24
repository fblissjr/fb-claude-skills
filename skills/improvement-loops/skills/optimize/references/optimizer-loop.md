Find a breakthrough in this project's performance in one session, and measure every step.

Done means:
- the target below is met,
- nothing regresses beyond the tolerances,
- the before-committing checks in AGENTS.md's Commands section pass,
- every headline result was re-checked on the branch's final commit, and
- a final review finds no significant untried idea.

The target is a floor, not the finish line. Keep going while ideas are still paying off.

This prompt works with the repo's AGENTS.md. Its North star says what speed matters for and breaks ties; it is not a spec. The rest of AGENTS.md applies as written: how to work, other sessions, engineering rules, measurement (including the project's real path, primary benchmarks, instruments and hazards), reporting, and the loop state, which this loop shares with the improvement loop. If AGENTS.md lacks a section named here, or leaves a placeholder unfilled, list it under "Needs from me" and use the nearest thing the repo has.

<parameters>
- Target: the primary benchmarks at least 1.2× faster than the base commit. (Or name the metric that matters, such as latency on one path, peak memory, or throughput at a given size.)
- Focus: none. (Or name a path or a component.)
- Other sessions: none. (Or name them. Then the rules for staying independent in AGENTS.md's Other sessions section apply.)
- Run budget: about 6 hours. Record the start time and check `date` against it.
- Landing: a branch `perf/<run id>` from the base commit, in its own git worktree, one commit per kept change. State each commit's evidence as a relationship plus a pointer to its scoreboard rows. Don't merge or push.
- Speed: no benchmark slower than the base commit beyond its noise, including small-input and edge sizes, and never more than 3% slower.
- Quality: all tests pass; no quality or accuracy metric more than 0.1% (relative) worse; deterministic outputs unchanged.
- Memory: flag any peak-memory increase over 10%.
- Reviewers: one read-only subagent per lens.
</parameters>

<context>
Assume the easy wins are gone. A breakthrough usually changes the shape of the work rather than tuning it:
- a better algorithm or data layout,
- work removed entirely, because it is reused, batched, or never needed,
- fewer copies across boundaries,
- parallelism or vectorization where the work allows it, or
- a new algorithm built for this specific problem.

Draw on what's new: techniques and upstream capabilities from the last year. Be bold by default. When a promising idea is large, prototype it instead of logging it for later. Measurements decide what stays, and a well-measured dead end is still a result.
</context>

<baseline>
1. Create the run id and the branch worktree, and start the run record. In your worktree, read AGENTS.md and the status and plans it points to. In the loop state, read the scoreboard and the ledger. Ideas the ledger already rejected aren't worth retrying blind. Check that the commands and instruments AGENTS.md names still work on the base commit.
2. Set up the `base` worktree beside your branch, as AGENTS.md's Measurement section describes. Never edit `base`.
3. Build the release configuration. On `base`, run the tests, then run every benchmark at least 5 times. Append the median and spread, with their conditions, to the scoreboard.
4. Pick the exact counts you'll iterate on for the hot paths. Before relying on each one, show that it tracks wall-clock time.
5. Show me the baseline as a table and a chart.
</baseline>

<hypotheses>
Launch the reviewers in parallel. Each one is read-only and gets one lens:
- What's new: techniques and upstream capabilities from the last year. Search the web, and cite the source and date.
- Algorithmic complexity and scaling at large inputs.
- Work that could be removed: recomputation, repeated parsing, redundant passes, missed reuse.
- Memory layout, allocation and copies.
- Parallelism and concurrency.
- Vectorization and branch behaviour.
- Boundaries: FFI, serialization, processes, network round trips.
- I/O.
- The shipped artifact's build configuration.
- A bespoke algorithm for this specific problem.
- The numerical approach, within the quality tolerance.
- Correctness and robustness risks the other ideas carry.

Tell each one:
- Read code and the web only. Don't build, run tests or benchmarks, or start processes. Those compete for the machine and make timings meaningless.
- For each idea, cite the file and line, say how the speedup works, and estimate the gain and the risk. Mark each claim as measured, read in the source, or reported elsewhere. Where a claim needs data you don't have, write "verify:" instead of guessing.
- Return at most 5 ideas, leading with the single biggest change you would bet on.

Before an idea goes into the ledger, check its claim against the code and check whether the ledger already rejected it. Work the ideas in order of expected value.
</hypotheses>

<optimize>
Start with the biggest bet. Before you start it, write in the run record what result, by what point, would make you drop it. Then prototype its riskiest part first. If the bet dies, log why with the evidence and move to the next one. Take the quick wins between bets.

For each change:
1. Profile the path and confirm it's hot.
2. Make sure tests cover its behaviour, following AGENTS.md's Tests section.
3. For a structural change, sketch the before and after first.
4. Change the code, iterating on the exact counts.
5. Run the tests, then the benchmarks, alternating with `base`.
6. Keep the change only if it moves toward the target, stays within every tolerance, and is worth the code it adds, and commit it on its own. A correctness fix you find along the way is kept too. Otherwise revert the change. Either way, append it to the ledger.
7. Where a count backs the win, add a test that fails if the count rises above the new value.
8. Append the rows to the scoreboard and redraw the chart. Look at the chart, then put the table and the chart in the same message as your next action, with a line on what to look at.
</optimize>

<rules>
- Optimize the project's code. You may add benchmarks, tests and instrumentation. AGENTS.md's Measurement section says what you may not change.
- New general-purpose dependencies are fine. What AGENTS.md's North star lists as owned here is written here, not imported. Size-adaptive strategies (different code paths for small and large inputs) are encouraged.
- A build setting counts only if it ships in the artifact users install. Keep that artifact portable: prefer runtime CPU-feature detection to native-CPU targeting.
- If the target can't be reached without breaking a rule, stop and report what you found.
</rules>

<finish>
When the backlog is empty, relaunch the reviewers with the diff against `base` and the ledger. Ask each one for:
a. whether the code correctly carries out the ideas that were adopted,
b. only the problems they would block the merge for, each with the file and line, why it's wrong, and how to show it fails, and
c. ideas the ledger doesn't already have.
Fix whatever blocks the merge, and send new ideas back through <optimize>.

Stop when the reviewers have no significant untried ideas and the last two rounds together gained less than 2%, or when the budget is spent. Re-run every headline benchmark on the branch's final commit, and report only what holds. Finish the run record, append your session-log section, and tidy the ledger if AGENTS.md's Loop state section allows it. End with these headings, in this order:
- Needs from me: decisions and approvals waiting on me, each with its picture and your recommendation.
- Results: the final table and chart against `base`.
- Changed: what was kept, and why it's faster.
- Tried and rejected: each with its measured result, including the bets that died and what ended them.
- Not confirmed: anything you couldn't verify or run, and where you looked.
- Next ideas: what's still worth trying.
</finish>
