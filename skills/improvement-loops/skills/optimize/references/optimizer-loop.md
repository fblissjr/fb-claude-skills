Make this project as fast as it can go, in one session: its core library and every public interface or binding (Python, Node, C ABI, etc.), without making correctness, output quality, or safety worse.

Done means: every primary benchmark is at least 1.2× faster than the base commit, nothing regresses beyond the tolerances below, all tests pass, and a final review finds no significant untried ideas. The 1.2× target is a floor, not the finish line. Keep going while ideas are still paying off.

<parameters>
- Target: every primary benchmark at least 1.2× faster than the base commit.
- Speed regressions: no benchmark, including small-input and edge-case sizes, more than 3% slower beyond measured noise.
- Quality regressions: all tests pass; no quality or accuracy metric more than 0.1% (relative) worse; deterministic outputs stay the same.
- Memory: flag any peak-memory increase over 10%.
- Safety: no new memory-unsafe code (Rust `unsafe`, unchecked pointer arithmetic in C/C++, ctypes or buffer tricks in Python).
- Landing: a branch `perf/<date>` from main's HEAD at the start (the base commit), in its own git worktree, one commit per kept change. Don't merge or push.
- Other sessions: none. (Or name them. Then read only committed history, never touch the main checkout, don't message them, use your own processes, and discard any timing pair where the machine's load changed partway through.)
- Reviewers: 7–12 read-only subagents.
</parameters>

<context>
This codebase is already heavily optimized, so the easy wins are mostly gone. Reaching the target will probably take structural changes: better algorithmic complexity, different data layouts, fewer copies across boundaries, parallelism, vectorization, or new algorithms built for this specific problem. Draw on what's new: techniques and upstream capabilities from the last year that apply here. When an idea is promising but large, try it instead of logging it for later. Measurements decide what stays.
</context>

<how_to_run>
When a step doesn't need my input, keep going. Put status notes and results in the same message as your next action. Don't end your turn with a summary that announces the next step, an offer to continue, or a list of decisions that don't block the work. Stop and ask only when you can't continue without me, or before anything destructive: deleting data, merging, pushing, rewriting history, or changing anything outside the repository.

Keep `PERF_LOG.md` in your worktree, uncommitted (stage files explicitly), as the source of truth: the baseline, the backlog as a checklist, what was kept or rejected and why, and the latest table. Older turns get summarized as your context fills, so resume from this file, not from memory.
</how_to_run>

<baseline>
1. Read the README, contributing docs, CLAUDE.md/AGENTS.md, and the build and CI config to learn how to build, test, and benchmark each part. Include competitor benchmarks if the repo has any.
2. Set up two worktrees at the base commit: `base`, which you never edit, and your branch. Give each its own environment and its own copies of any untracked local config the project needs. Before trusting a run, confirm it is running that worktree's code, because an editable install can silently point somewhere else.
3. Build the release configuration users install. On `base`, run the tests and every benchmark at least 5 times, and record the median and spread. A difference inside the spread counts as zero.
4. Record the baseline in `PERF_LOG.md` with the commit, machine, and exact commands. Show it to me as a table and a chart.
</baseline>

<hypotheses>
Launch the reviewers in parallel, each read-only with its own lens: what's new in the last year (search the web; cite source and date); algorithmic complexity and scaling; memory layout and allocation; parallelism and concurrency; SIMD and branch behavior; boundary crossings (FFI, copies, locks, per-call overhead); I/O and serialization; the shipped artifact's build configuration; bespoke algorithms for this problem; numerical approach within the quality tolerance; security and robustness. Tell each one:
- Don't build, run tests or benchmarks, or start processes. Parallel runs make timings meaningless.
- For each idea, cite the file and line, say how the speedup works, estimate the gain and the risk, and mark each claim as measured, read in the source, or reported. Where a claim needs data you don't have, write "verify:" instead of guessing.
- Return at most 5 ideas, ranked by expected gain × confidence ÷ effort, leading with the single biggest change you would bet on.
Read the code each reviewer cites and check its claim before you add the idea to the backlog.
</hypotheses>

<optimize>
Work the backlog, highest expected value first. For each item:
1. Profile the path and confirm it's hot.
2. Make sure tests cover its current behavior. If they don't, add tests first.
3. Change the code. Iterate against exact counts where you can: instruction counts (cachegrind `Ir`, `perf stat`), allocation counts, or call counts. One run gives a clean signal. Before relying on a count, show that driving it down also lowers wall-clock time.
4. Run the tests, then the benchmarks, alternating runs with `base`.
5. Keep the change only if it moves toward the target, stays within every tolerance, and is worth the code it adds. Commit it on its own with the measured difference in the message. Otherwise revert it and log the result so it isn't retried.
6. Where a count backs the win, add a test that fails if the count rises above the new value.
7. Update the table in `PERF_LOG.md`, render the chart from it with a small script, and look at the chart before you describe it. Put both in your next message with a line on what to look at, then move on.
</optimize>

<rules>
- Optimize only library code. You may add benchmarks, tests, and instrumentation, but don't change existing benchmarks, their inputs, iteration counts, or harness config, and don't special-case benchmark inputs.
- Every iteration starts from the state its benchmark declares. Cold means cold in every cache on the path. Nothing may persist between iterations and make later ones faster: no process-global memo tables, no caches keyed on inputs, no indexes reused across calls. Caches scoped to a single call or object are fine.
- A build setting counts only if it applies to the artifact users install. Keep that artifact portable: prefer runtime CPU-feature detection over native-CPU targeting.
- New general-purpose dependencies (SIMD, hashing, allocators, parallelism) are fine. Don't add or copy in a library that already implements the core algorithm. Size-adaptive strategies are encouraged.
- If the target can't be reached without breaking one of these rules, stop and tell me what you found.
</rules>

<finish>
When the backlog is empty, relaunch the reviewers with the diff against `base` and `PERF_LOG.md`. Ask each one to (a) check that the code correctly carries out the ideas that were adopted, (b) list only the problems they would block the merge for, each with the file and line, why it's wrong, and how to show it fails, and (c) suggest ideas not already in the log. Send new ideas back through <optimize>.

Stop when the reviewers have no significant untried ideas and the last two rounds together gained less than 2%. Re-run every headline benchmark on the branch's final commit, because later commits can undo earlier wins, and report only what holds. End with these headings, in this order:
- Needs from me: decisions or approvals you're waiting on.
- Results: the final table and chart against `base`.
- Changed: what was kept, and why it's faster.
- Tried and rejected: each with its measured result.
- Not confirmed: anything you couldn't verify, and where you looked.
- Next ideas: what's still worth trying.
</finish>
