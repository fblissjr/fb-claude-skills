---
name: plugin-toolkit
description: Analyze, polish, and manage Claude Code plugins. Use when user wants to evaluate a plugin (/plugin-toolkit:analyze), add standard utility commands (/plugin-toolkit:polish), or add/remove/modify plugin features (/plugin-toolkit:feature). Also use when user mentions "plugin analysis", "plugin review", "add command to plugin", or "improve plugin". Also use when user says "review my plugin", "check plugin quality", "what's wrong with my plugin", "add a help command to my plugin", or "improve my plugin structure".
allowed-tools: "Read, Glob, Grep"
---

# Plugin toolkit

Three modes over a Claude Code plugin directory: analyze it, polish it, or
change one of its features.

<how_to_run>
The modes are arguments to this skill, not separate commands:

```
/plugin-toolkit:plugin-toolkit analyze <path>
/plugin-toolkit:plugin-toolkit polish <path> [--skip-changelog]
/plugin-toolkit:plugin-toolkit feature add|remove|change <path> <component> <name> [...]
```

When the skill loads from phrasing instead ("review my plugin"), take the mode
and path from the request. Both agents below start with a fresh context, so
pass each one the plugin path and whatever it needs from earlier steps.
</how_to_run>

<analyze>
1. Run `claude plugin validate <path> --strict`. Its output settles schema and
   manifest questions; the review cites it rather than re-deriving them.
2. Dispatch `plugin-scanner` for the inventory, then `quality-checker` with
   that inventory and the validate output.
3. Write `analysis/` in the plugin:
   - `ANALYSIS.md`: what the plugin does, its component inventory, how data
     flows between components, strengths and weaknesses.
   - `RECOMMENDATIONS.md`: improvements in priority order, each with the
     problem, its impact, and the fix.
   - `INTEGRATION_WORKFLOWS.md`: how it composes with other plugins, where
     there is anything to say.
   - `SKILL_REVIEW.md`: quality-checker's ratings and the evidence behind each.
</analyze>

<polish>
Add the utilities the plugin lacks, and skip each one already present:

- A help command listing the plugin's skills and commands, only when the
  built-in `/help` listing would not already say enough.
- A status command, when the plugin keeps state.
- Off/on commands, when a hook injects context on every prompt and the user
  may want it quiet without disabling the whole plugin (`/plugin disable`
  already does that).
- `CHANGELOG.md` when missing, unless `--skip-changelog` or the marketplace
  keeps one changelog at its root.
</polish>

<feature>
`add` creates the component (a skill, a flat command, an agent, or a hook
entry plus its script), `remove` deletes it and every reference to it,
`change` edits it in place and updates what refers to it. Before removing,
grep the plugin and its marketplace for references and name what would break.
</feature>

<gotchas>
Harness behaviour a generated plugin gets wrong silently:

- `skills/`, `commands/`, `agents/`, `hooks/hooks.json` and `.mcp.json` are
  auto-discovered. Leave them out of `plugin.json`: a `commands` or `agents`
  path listed there replaces the default directory rather than adding to it
  (`skills` adds).
- `UserPromptSubmit`, `Stop` and several other events have no matcher
  support; a `matcher` on them is silently ignored and the hook fires on every
  prompt. An off/on toggle therefore lives in the injecting script, which reads
  a state file and exits early, with the off/on commands writing that file.
- A hook running a bundled script uses exec form with the interpreter named:
  `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"]`. The
  script path as `command` breaks on a plugin root containing a space and on
  Windows.
- Hook `timeout` is in seconds, and a timed-out hook renders no decision.
- A read-only agent sets `tools` explicitly; omitting it inherits Write and
  Edit. Plugin agents ignore `hooks`, `mcpServers` and `permissionMode`.
</gotchas>

<report>
The files written or changed, with one line each on what changed; for
analyze, the overall rating and the top recommendation.
</report>
