What `/improve` and `/optimize` share. Read this before the loop file; the loop file refers to these sections by name.

<worktrees>
- **Your branch.** Enter it with the `EnterWorktree` tool, on a branch named as the loop's Landing parameter says. Once you are inside, Claude Code moves the session's working directory and project configuration to the worktree, and blocks edits and git commands aimed at the main checkout. The same checks cover every subagent you launch.
- **The `base` worktree** for measuring: create it with `git worktree add` at the base commit (the default branch's HEAD when the run starts). Never edit it.
- **Untracked config** a worktree needs, such as `.env` or a local models file, is copied in by a `.worktreeinclude` file at the project root, in `.gitignore` syntax. If one is missing, list what it should name under "Needs from me".
- **Before trusting a measurement,** confirm each arm runs its own worktree's code. An editable install can silently point at the main checkout.
- **Worktrees from a `-p` run are not cleaned up** automatically. Remove `base` when the run ends.
</worktrees>

<loop_state>
Every write to the loop state goes through the plugin's script, run from your worktree:

`python3 <plugin root>/scripts/loop_state.py <command>`, with the plugin root the skill gave you

Under isolation, the Write and Edit tools can't reach the main checkout, where the loop state lives; the script can. The script also enforces the loop state's rules, so you don't have to remember them.

| When | Command |
|---|---|
| The run starts | `start --loop <improve or optimize> --base <sha> --session <session id> --budget-minutes <n>`, with one `--done "<item>"` per item of the loop's done list. It prints the run id |
| A done item is met | `check --run <id> --item <n> --evidence "<where it shows>"` |
| Every so often during a long step | `heartbeat --run <id>` |
| A measurement | `score --run <id> --row '<json>'`. A row without its conditions (commit, scenario, inputs, deps, machine, load, samples, median, spread) is refused |
| An idea is tried, kept or rejected | `ledger --run <id> --lens <lens> --idea "<idea>" --ev <number> --status <open, kept, rejected or died> --evidence "<evidence>"` |
| A lens or dependency was reviewed | `bookmark --lens <lens> --commit <sha>` or `bookmark --dep <name> --release <version>` |
| Tidying the ledger | `can-tidy --run <id>`, then `tidy --run <id> --from <file>`. A refusal lists the runs in the way; an abandoned-looking one goes under "Needs from me" |
| Your session-log section | `log --run <id> --path <session log path from AGENTS.md> --from <file>` |
| The run ends | `finish --run <id> --status done`, refused while a done item is unmet, or `--status stopped --reason "<reason>"` |
| Where things stand | `status` |

Write the text for `tidy` and `log` to a scratch file in your worktree or the temp directory first.

The state folder is the one AGENTS.md names under Where things live. If none is named, the script uses `.loops/` in the main checkout and excludes it from git. Pass `--state <folder>` to use the named one.
</loop_state>

<stop_guard>
While a run started in this session is `running`, the plugin's Stop hook holds it to its done list. It is silent in every other session and every other turn. If you end a turn with done items still open and budget left, the hook sends them back to you. Carry on with them. If one is genuinely blocked, say what blocks it and end the run with `finish --status stopped`. The hook stands down after three continuations without progress, so a stuck run still ends.
</stop_guard>

<reviewers>
- **Finding ideas.** Launch one `improvement-loops:loop-reviewer` agent per lens, in parallel. Give each its lens, the base commit and its time, and, in breakthrough mode, that it should lead with its biggest bet. Its tools are read-only by construction.
- **Reviewing the diff.** Relaunch reviewers in review mode, with the run's diff and the ledger.
- **Checking a report.** Before an idea goes into the ledger, read the code it cites and check its claim, and check whether the ledger already rejected it. A reviewer's report is a claim, not a result.
- **Grading.** At the end, give the `improvement-loops:loop-grader` agent the paths to the done list, the run record, the report and the north star.
</reviewers>

<budget>
Record the start time in the run with `--budget-minutes`, and check `date` against it before starting each new idea.
</budget>
