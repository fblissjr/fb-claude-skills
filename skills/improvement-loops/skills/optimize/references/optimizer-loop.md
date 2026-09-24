Find a breakthrough in this project's performance in one session, and measure every step.

Done means:
- the target below is met,
- nothing regresses beyond the tolerances,
- the before-committing checks in AGENTS.md's Commands section pass,
- every headline result was re-checked on the branch's final commit, and
- a final review finds no significant untried idea.

The target is a floor, not the finish line. Keep going while ideas are still paying off.

This prompt works with the repo's AGENTS.md. Its North star says what speed matters for and breaks ties; it is not a spec. The rest of AGENTS.md applies as written: how to work, other sessions, engineering rules, measurement (including the project's real path, primary benchmarks, instruments and hazards), reporting, and the loop state, which this loop shares with the improvement loop. If AGENTS.md lacks a section named here, or leaves a placeholder unfilled, list it under "Needs from me" and use the nearest thing the repo has. The plugin's `common.md` covers the worktrees, the loop state, the stop guard and the reviewers; this prompt refers to its sections by name.

<parameters>
- Target: the primary benchmarks at least 1.2× faster than the base commit. (Or name the metric that matters, such as latency on one path, peak memory, or throughput at a given size.)
- Focus: none. (Or name a path or a component.)
- Other sessions: none. (Or name them. Then the rules for staying independent in AGENTS.md's Other sessions section apply.)
- Run budget: about 6 hours. See `common.md` <budget>.
- Landing: a branch `perf/<run id>` from the base commit, entered as `common.md` <worktrees> describes, one commit per kept change. State each commit's evidence as a relationship plus a pointer to its scoreboard rows. Don't merge or push.
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
1. Start the run with `loop_state.py start`, registering this prompt's done list, then enter the branch worktree (`common.md` <loop_state>, <worktrees>). In your worktree, read AGENTS.md and the status and plans it points to. In the loop state, read the scoreboard and the ledger. Ideas the ledger already rejected aren't worth retrying blind. Check that the commands and instruments AGENTS.md names still work on the base commit.
2. Set up the `base` worktree beside your branch (`common.md` <worktrees>, and AGENTS.md's Measurement section). Never edit `base`.
3. Build the release configuration. On `base`, run the tests, then run every benchmark at least 5 times. Record the median and spread, with their conditions, with `loop_state.py score`.
4. Pick the exact counts you'll iterate on for the hot paths. Before relying on each one, show that it tracks wall-clock time.
5. Show me the baseline as a table and a chart.
</baseline>

<hypotheses>
Launch the reviewers as `common.md` <reviewers> describes, one per lens:
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

Tell each one to lead with the single biggest change it would bet on. Work the ideas in order of expected value.
</hypotheses>

<optimize>
Start with the biggest bet. Before you start it, write in the run record what result, by what point, would make you drop it. Then prototype its riskiest part first. If the bet dies, log why with the evidence and move to the next one. Take the quick wins between bets.

For each change:
1. Profile the path and confirm it's hot.
2. Make sure tests cover its behaviour, following AGENTS.md's Tests section.
3. For a structural change, sketch the before and after first.
4. Change the code, iterating on the exact counts.
5. Run the tests, then the benchmarks, alternating with `base`.
6. Keep the change only if it moves toward the target, stays within every tolerance, and is worth the code it adds, and commit it on its own. A correctness fix you find along the way is kept too. Otherwise revert the change. Either way, record it with `loop_state.py ledger`.
7. Where a count backs the win, add a test that fails if the count rises above the new value.
8. Record the rows with `loop_state.py score` and redraw the chart. Look at the chart, then put the table and the chart in the same message as your next action, with a line on what to look at.
</optimize>

<rules>
- Optimize the project's code. You may add benchmarks, tests and instrumentation. AGENTS.md's Measurement section says what you may not change.
- New general-purpose dependencies are fine. What AGENTS.md's North star lists as owned here is written here, not imported. Size-adaptive strategies (different code paths for small and large inputs) are encouraged.
- A build setting counts only if it ships in the artifact users install. Keep that artifact portable: prefer runtime CPU-feature detection to native-CPU targeting.
- If the target can't be reached without breaking a rule, stop and report what you found.
</rules>

<finish>
When the backlog is empty, relaunch the reviewers in review mode with the diff against `base` and the ledger (`common.md` <reviewers>). Fix whatever blocks the merge, and send new ideas back through <optimize>.

Stop when the reviewers have no significant untried ideas and the last two rounds together gained less than 2%, or when the budget is spent. Re-run every headline benchmark on the branch's final commit, and report only what holds. Mark the done items met, append your session-log section, tidy the ledger if `loop_state.py can-tidy` allows it, and finish the run with `loop_state.py finish`. End with these headings, in this order:
- Needs from me: decisions and approvals waiting on me, each with its picture and your recommendation.
- Results: the final table and chart against `base`.
- Changed: what was kept, and why it's faster.
- Tried and rejected: each with its measured result, including the bets that died and what ended them.
- Not confirmed: anything you couldn't verify or run, and where you looked.
- Next ideas: what's still worth trying.
</finish>
