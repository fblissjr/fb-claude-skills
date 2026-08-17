---
mode: session
scope: doctor-health-check
date: 2026-08-13
summary: Ten checks against an already-tight setup yielded only two actions — six unused claude.ai connectors disabled per-project and 54 derivable lines cut from a nested CLAUDE.md; the scan's one real hazard was that "50 most recent transcripts" was 80% subagent files until they were excluded.
artifacts:
  - apps/readwise-reader/CLAUDE.md
  - CLAUDE.md
  - .claude/rules/general.md
  - .claude/rules/plugins.md
  - .claude/rules/skills.md
  - <HOME>/.claude.json
  - <HOME>/.claude.json.doctor-backup
  - <HOME>/.claude/settings.json
  - <HOME>/.claude/projects/
  - claude --version
  - curl downloads.claude.ai/claude-code-releases/latest
---

# Postmortem: /doctor health-check run

## 1. What went well

**The transcript window was corrected before any verdict depended on it.** The
first pass at "the 50 most recently modified `.jsonl` files" under
`<HOME>/.claude/projects/` returned 40 subagent transcripts out of 50, spanning
only three days. Re-listing with `*/subagents/*` excluded produced 50 main
sessions over ten days (2026-08-04 to 2026-08-13) across 15 project
directories — the base every usage, denial, and hook verdict then rested on.
The structural version: "N most recently modified files" samples whatever
writes files fastest, not what is representative; filter for the population
you actually mean before aggregating.

**Deferral-awareness kept the connector recommendation honest.** Every MCP
tool in the session was deferred (names-only in context), so the six-connector
disable written to `disabledMcpServers` in `<HOME>/.claude.json` was framed as
decluttering with zero claimed token savings, rather than the reflexive
"save context by disabling servers" a naive report would emit.

**The name reconstruction was validated against a known specimen before
writing.** Connector names had to be reversed out of a lossy normalization
(`mcp__claude_ai_Hugging_Face__` → `claude.ai Hugging Face`). The existing
`disabledMcpServers` entry for Hugging Face in `<HOME>/.claude.json` — already
disabled, and correspondingly absent from this session's tool list — confirmed
both the naming pattern and that the mechanism works, before six reconstructed
names were written by the same rule. Structural version: when writing names
recovered from a lossy transform, find one known-good pair already in the
target store and check the rule against it first.

**Checks 8 and 9 resolved to no-ops from data, not to reflexive proposals.**
`permissions.defaultMode` was already `auto` at user scope with nothing
shadowing it (`<HOME>/.claude/settings.json`), and the denial join over the
transcript window found 29 denials with no repeated read-only pattern — mostly
Edit/Write permission-rule blocks and declined questions. The entire second
confirmation gate (permission changes) was skipped, as the protocol directs
when nothing is proposed.

## 2. What did not go well

**Three shell portability stumbles each cost a re-run.** `npm -g config get
prefix` aborted the first diagnostics batch (the user's npm shim errors on
`_nvm_load` in non-interactive zsh); `cd <HOME>/.claude/projects && ls -t */*.jsonl`
matched nothing and reset the shell cwd; and `awk strftime` does not exist in
BSD awk. Each was rewritten (`find | xargs stat | sort`, `date -r`). The
structural version: on macOS, diagnostic batches should assume BSD userland
and avoid interactive-shell shims from the first draft, not after the first
failure.

**The first draft of the transcript-scan jq program referenced a variable that
was never set** (`env.DENKIND` where `.toolDenialKind` was meant). Caught on
re-read before execution and rewritten; cost one edit, but it was the kind of
bug that would have silently produced zero denial rows rather than erroring.

## 3. Deviations from the plan

| Planned | Shipped | Verdict |
|---|---|---|
| /doctor's ten checks with up to two confirmation gates | All ten checks ran; one gate — checks 8/9 proposed nothing, so the permission question was skipped per the protocol | As designed |
| Scan the ~50 most recently modified transcripts across all projects | 50 most recent with `*/subagents/*` excluded, after the literal reading produced 80% subagent files over three days | Better than planned |
| Checks 2–4: dedup, trim, and migrate across all loaded CLAUDE.md files | One trim: 54 lines from `apps/readwise-reader/CLAUDE.md`. Root `CLAUDE.md`, `.claude/rules/general.md`, and the global file judged already lean; `.claude/rules/plugins.md` and `.claude/rules/skills.md` already lazy via `paths` frontmatter; nothing left to migrate | Scoped down honestly |
| Check 9's free-text fallback for old transcripts lacking `toolDenialKind` | `toolDenialKind` only — the window (2026-08-04..13) is all recent versions | Scoped down honestly |
| Check 3's scan covers nested CLAUDE.md files | `coderef/*` CLAUDE.md files skipped — third-party clones, not this repo's to trim | Scoped down honestly |

## 4. Escapes (tests)

Nothing. This was a diagnostic run over configuration and transcripts; no code
was under test, no tests were added, and the one bug (the jq variable, section
2) was caught before execution rather than escaping anything.

## 5. Forward items

1. **The typescript-lsp keep verdict is refutable.** Its `pluginUsage` counter
   in `<HOME>/.claude.json` (1,337 lifetime, `lastUsedAt` ~2026-07-26)
   predates the scan window. If a later check shows the counter still unmoved
   after sessions in TypeScript projects, the keep was wrong-premise —
   disable it then.
2. **Delete `<HOME>/.claude.json.doctor-backup`** once a next session confirms
   the six connectors no longer appear in the tool list. If they still appear,
   the reconstructed names were wrong and the backup is the rollback.

   > **2026-08-13 (same session):** Done, resolved by a structural check
   > instead of the next-session one: a key-level diff showed the live file
   > parses, carries exactly the six intended additions, and otherwise differs
   > from the backup only in session-state churn Claude Code had written
   > since. That churn made the backup worse than no backup — restoring it
   > would revert live state — while `/mcp enable <name>` undoes the connector
   > change surgically. Backup deleted; the next-session tool-list check still
   > stands as the confirmation the names were right.
3. **The `apps/readwise-reader/CLAUDE.md` trim is an uncommitted working-tree
   edit.** Done when it is either committed after `git diff` review or
   reverted. No version cascade applies — CLAUDE.md is not shipped plugin
   content.

   > **2026-08-13 (same session):** Reviewed and staged. Each of the four
   > removed convention bullets was verified present in
   > `.claude/rules/general.md`, which loads unconditionally, so nothing was
   > lost rather than moved.
   >
   > The conclusion holds but **the stated reason is wrong**, and the wrong
   > reason generalises badly. `apps/readwise-reader` *is* a marketplace plugin
   > (`source: ./apps/readwise-reader`, version 1.1.4), so that file does sit
   > inside shipped plugin content by the letter of invariant 1. The bump is
   > still not owed because a plugin's `CLAUDE.md` has no runtime effect for an
   > installer: Claude Code loads a plugin's skills, agents, hooks, commands and
   > MCP servers, never its memory files. That distinction now lives in
   > `docs/internals/plugin-versioning.md` under "Inside the source, but inert
   > for installers", phrased as a behavioural test — does an installed session
   > behave differently after `marketplace update` — with the counter-examples
   > named so it is not over-applied to `SKILL.md` bodies or hook scripts.

*Redacted 2026-08-17, on publication: an addendum here recorded the root cause
and same-day fix for the npm shim noted in section 2. It described a personal
shell configuration in enough detail to reconstruct it, so it is kept out of the
published record. Nothing else depended on it — the BSD-userland lesson in
section 2 was always the transferable half and stands unchanged.*
