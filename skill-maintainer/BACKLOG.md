# skill-maintainer backlog

Items for future development. Not prioritized -- just captured.

## git log pattern mining

During `/maintain` Phase 1 (after pulling sources), scan recent commits to key repos for patterns relevant to skill authoring:

- `coderef/agentskills`: spec changes, new validation rules, description conventions
- `coderef/skills`: description rewrites, frontmatter pattern evolution, new skill structures
- `coderef/claude-plugins-official`: plugin manifest changes, new hook patterns, agent conventions

Approach: `git log --oneline --since="last maintain date"` + `git diff` on SKILL.md and plugin.json files. Surface commit messages and diffs that touch skill descriptions, frontmatter fields, or validation logic. Feed to Claude in Phase 4 as evidence for best_practices.md updates.

Also consider: scanning merged PRs and issue discussions (via `gh pr list --state merged`) for rationale behind changes. Accepted PRs are a signal of what the ecosystem considers good practice.

Would slot in as a Phase 1.5 in the maintain command.

## hook audit reporting

When run_tests.py audits hooks, generate a summary report showing:
- Every configured hook (settings.json + plugin-provided)
- Trigger frequency (high-frequency events like every tool call vs. low-frequency like commits)
- What context each hook injects
- Whether the hook has a justification documented somewhere

Could also track hook firing frequency over time via changes.jsonl events, if hooks ever get re-enabled.
