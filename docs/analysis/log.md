last updated: 2026-07-21

# analysis log

Append-only narrative log of ingests, updates, and audits across `docs/analysis/`. Complements `.skill-maintainer/state/changes.jsonl` (operational, machine-readable) by capturing the *why* behind significant updates and the human decisions made when reviewing upstream deltas.

## Conventions

Each entry is an `H2` header with a date prefix and a verb classifier:

```
## [YYYY-MM-DD] ingest | <new report or page>
## [YYYY-MM-DD] update | <existing report> — <reason>
## [YYYY-MM-DD] audit  | <scope> — <finding>
```

Verbs:

- **ingest** — first-time addition of a new report, captured doc, or analysis page
- **update** — substantive edit to an existing report (driven by upstream change, internal correction, or new understanding)
- **audit** — a review pass that produced findings (linting, cross-reference check, manual sweep)

Body text: 1–4 sentences explaining what changed and why. Reference upstream commits, PRs, or `changes.jsonl` lines when relevant. Don't restate the diff — the git log has it.

## Entries

## [2026-05-04] audit | wiki layer bootstrapped

`docs/analysis/index.md` and `docs/analysis/log.md` introduced as part of the skill-maintainer 0.7.0 release. Index categorizes existing reports by kind (entity / concept / audit / synthesis) so retrieval is by intent. This log starts here and accumulates forward; historical operational events for source pulls and upstream checks remain in `.skill-maintainer/state/changes.jsonl` (machine-readable) and don't get backfilled into the narrative.

## [2026-05-04] update | upstream Claude Code docs (9 pages changed)

`skill-maintain upstream` produced a 9-page delta touching skills, plugins, plugins-reference, discover-plugins, plugin-marketplaces, hooks-guide, hooks, sub-agents, and memory. Largest deltas: plugins-reference (+173/-82, +10K chars), hooks (+439/-178, +22K chars), sub-agents (+136/-63, +7K chars). Implications for `docs/analysis/` not yet propagated -- domain reports referencing those pages should be reviewed and refreshed in the next maintenance pass. Source: `.skill-maintainer/state/changes.jsonl` 2026-05-04 entry.

## [2026-07-21] audit | docs/ triage: 26 files deleted, 8 bannered, upstream copies retired

Follow-through on the 2026-05-04 entry above, which flagged that domain reports
referencing the changed upstream pages needed review and then sat unactioned for
two and a half months. A fresh `skill-maintain upstream` showed all nine tracked
pages had changed again, far more than in May -- hooks alone went 64KB to 235KB
since the February capture.

Deleted 26 files. All 20 of `docs/claude-docs/`: frozen February copies, roughly
a third of current content, carrying no date header so nothing signalled their
staleness, and wrong in load-bearing ways (`allowed-tools` grants rather than
restricts; hook exit 0 reports no decision rather than success). Plus six
analysis reports -- three of which were the same Anthropic skills-guide PDF
restated three times, all superseded by `.skill-maintainer/best_practices.md`;
`self_updating_system_design.md`, which described a CDC pipeline that was never
built; and two point-in-time snapshots pinned to a pre-reorg layout.

Kept eight analysis reports but added a staleness banner naming the specific
false claims in each, because they share one shape: durable original synthesis
(anti-pattern catalogs, design checklists, comparison matrices, a surface
compatibility matrix) sitting on top of API specifics that rotted.
`subagents_and_agent_teams.md` is the sharpest case -- it asserts three times
that subagents cannot spawn subagents, which the current docs directly reverse,
and that claim is load-bearing for anyone designing delegation.

Upstream docs are no longer copied into the repo at all. Three pages that had
only a frozen copy (settings, permissions, mcp) were added to
`upstream_urls`, bringing tracked pages to twelve; everything else is a link
away. The lesson worth keeping: a copy with no date header cannot be audited,
and a stale copy is worse than no copy, because a clone can refetch in seconds
but cannot know what it is reading is five months old.

## 2026-07-21 (later) — deleted the eight bannered survivors

Earlier today this directory was triaged: 26 files deleted, 8 kept with
permanent banners naming their specific false claims. That compromise is now
reversed, and the reversal is recorded here rather than left to look like churn.

**Why the banners were not enough.** Retrieval in this repo is frequently
grep-based. A grep hit lands mid-file, below the banner, on unbannered stale
prose — so the mitigation only works for a whole-file read, which is not how
these documents are actually consumed. `subagents_and_agent_teams.md` still
asserted "subagents cannot spawn other subagents" as a key constraint in its
body, which is false and load-bearing for anyone designing delegation.

**Deleted (7):** subagents_and_agent_teams, memory_and_rules_system,
marketplace_distribution_patterns, plugin_system_architecture,
mcp_apps_and_ui_development, hooks_system_patterns, cross_surface_compatibility
— the whole 2026-02-19 cohort. Everything durable in them is superseded by
`.skill-maintainer/best_practices.md` (which is *maintained*), duplicated by
tracked upstream snapshots, shipped in `skills/mcp-apps/references/`, or
describes in-repo code that is its own source of truth.

**Also deleted:** `docs/reports/claude_ecosystem_synthesis.md` — 13 of its 15
analysis links were dead. A 706-line synthesis of documents that no longer
exist is worse than no synthesis.

**Kept (3):** `data_centric_agent_state_research.md` (the one genuinely
irreplaceable file — the comparative survey and DuckDB rationale behind
`tools/agent-state`; VISION.md asserts the conclusion but not the comparison),
`mcp_protocol_and_servers.md` (verified current, linked from CLAUDE.md), and
this log.

**Salvaged before deletion:** the hook anti-pattern catalog, into
`docs/internals/plugin-patterns.md` — but only the items that are environmental
or that we verified independently. Importing the unverified remainder into a
maintained document would have moved the problem rather than solved it.

**What is lost, plainly:** the six-surface compatibility matrix, the plugin
readiness checklist, the marketplace source-type table, the memory-vs-skills
comparison tables, and prose write-ups of mece-decomposer and the plugin-toolkit
agent pipeline. All regenerable from tracked sources; none were measurements.

