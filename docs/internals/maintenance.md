last updated: 2026-07-21

# Maintenance

Mechanisms and commands that keep this repo's content current. Most run on demand; a few fire automatically via git or Claude Code hooks.

## Automatic checks

| Concern | Mechanism | Trigger |
|---------|-----------|---------|
| SKILL.md spec compliance | Pre-commit git hook (skills-ref) | On commit |
| Plugin version alignment (per-plugin: plugin.json vs. marketplace.json version string) | Pre-commit git hook | On commit (hard block) |
| Plugin↔marketplace listing alignment (`check_version_alignment`: marketplace entries with no plugin on disk, plugins on disk missing from marketplace) | `skill-maintain quality` / repo-hygiene suite | On demand |
| Unbumped content changes | Pre-commit git hook | On commit (warning only) |
| CLAUDE.md size creep | Pre-commit git hook | On commit (warning only) |
| `claude plugin validate . --strict` | Pre-commit git hook | On commit, only when `marketplace.json` is staged; skipped if the `claude` CLI is absent |
| Plugin behaviour drift across repos (emission rates, unattributable hooks, artifact staleness) | `skill-maintain tune` | Phase 4 of `/skill-maintainer:maintain` |
| Bundled best_practices.md drift | skill-maintainer PostToolUse hook (`skill-maintainer-sync-bundled-ref.sh`) | On Edit/Write of working copy |
| Forgotten session log | skill-maintainer Stop hook (`maybe-draft-session-log.sh`) | On session stop, when ≥3 substantive files touched and today's log not updated |

The pre-commit hook lives at `.git/hooks/pre-commit` and is **not tracked by git** — must be re-applied on fresh clones. See [gotchas.md](gotchas.md) for setup.

## On-demand commands

| What | Command |
|------|---------|
| End-of-session wrap-up (orchestrates drafter → sync → bumps → quality) | `/skill-maintainer:finish-session` |
| Red/green test suite | `skill-maintain test` |
| Full maintenance pass (pulls sources, checks upstream, runs quality, proposes best-practices updates) | `/skill-maintainer:maintain` |
| Quick quality / budget / freshness | `/skill-maintainer:quality` or `skill-maintain quality` |
| Upstream Claude Code doc change detection (per-page snapshots, line/char deltas) | `skill-maintain upstream` |
| Pull tracked source repos, detect changes | `skill-maintain sources` |
| Bump version across plugin.json + marketplace.json + plugin pyproject.toml | `/skill-maintainer:sync-versions <plugin> <ver>` |
| Mirror `.skill-maintainer/best_practices.md` → bundled reference (fallback if hook didn't fire) | `a direct copy (the PostToolUse hook normally handles it)` |
| Append-only audit log query | `skill-maintain log` |
| Wiki sanity (orphans in `docs/analysis/`, count drift in READMEs / CLAUDE.md) | `skill-maintain lint` |
| Per-project dependency vulnerability scan | `/dev-conventions:dep-audit` |
| Promote `agent-state` MCP server from `_available_servers` → `mcpServers` | `/agent-state-mcp:enable` |

## Lower-level CLI

```bash
skill-maintain validate --all                    # validate all skills
skill-maintain measure                           # token budget report
skill-maintain freshness                         # SKILL.md staleness check (uses metadata.last_verified + metadata.review_interval_days)
skill-maintain init                              # initialize .skill-maintainer/ in a new repo
uv run skill-maintain validate path/to/SKILL.md  # validate a single skill against the Claude Code schema (called by pre-commit; add --strict for portability)
```

All commands accept `--dir <path>` to target a different repo.

## State files

- `.skill-maintainer/state/upstream_hashes.json` — page content hashes for upstream change detection (auto-generated, gitignored)
- `.skill-maintainer/state/pages/<slug>.md` — per-page content snapshots for line/char delta computation (v0.4.0+, auto-generated)
- `.skill-maintainer/state/changes.jsonl` — append-only audit log of quality reports, upstream checks, source pulls (consumed by `skill-maintain log`)
- Each `SKILL.md`'s `metadata.last_verified` — date a human last reviewed the skill against its source. Not part of the version cascade: a version bump does not establish that a human checked the content, so nothing bumps this mechanically. Consumed by `skill-maintain freshness` together with `metadata.review_interval_days` (default 30) — the per-skill staleness window, tiered 30 days (content derived from Claude Code docs), 90 days (tracks a third-party SDK or API), or 365 days (methodology, or our own code). Replaces the old single global 30-day window.

### The tiers are now measurable, and the 30-day one checks out

`changes.jsonl` is the only record of how fast each upstream source *actually*
moved, and until 2026-08-02 nothing read it that way — the tiers were set from
intuition while the evidence sat unread in a gitignored file.
`tools/skill-maintainer/queries/upstream_churn.sql` answers it. First run, over
2026-03-03 to 2026-07-21:

| Page | Changes | Roughly |
|---|---|---|
| `docs/en/skills` | 12 | every 11 days |
| `docs/en/hooks`, `plugin-marketplaces`, `discover-plugins`, `memory` | 8 | every 17 days |
| `docs/en/sub-agents`, `hooks-guide`, `plugins` | 7 | every 19 days |
| `docs/en/plugins-reference` | 5 | every 27 days |

So **30 days is defensible for docs-derived content and arguably generous** — the
fastest page moves twice inside that window, and nothing tracked moves slower
than it.

Two cautions before this gets over-read. `changes` counts only checks that *found*
a change, so the interval is an upper bound on quiet periods, not a release
cadence. And `abs_chars` is not comparable across the window: `changed_pages`
holds bare strings before 0.4.0 and structs after, so only struct-era rows carry
`chars_delta`. Rank on `changes`. The three pages showing a single change with
enormous character counts are first-seen-after-the-format-change, not sudden
rewrites.

Deliberately a query file rather than a subcommand. One use does not earn a CLI
surface or a `duckdb` dependency on this tool; if it gets run every maintenance
pass, that is the evidence for promoting it.
- `<HOME>/.claude/agent_state.duckdb` — global DuckDB for run audit and state tracking across all projects (schema in `tools/agent-state/`)

## Workspace members (Python)

Python managed as a uv workspace. The root `pyproject.toml` coordinates members, each declaring its own deps.

| Member | Path | Key dependencies |
|--------|------|-----------------|
| `skill-maintainer` | `tools/skill-maintainer` | orjson, httpx, skills-ref; CLI: `skill-maintain` |
| `agent-state` | `tools/agent-state` | orjson, duckdb; CLI: `agent-state` |
| `agent-state-mcp` | `apps/agent-state-mcp` | mcp, duckdb, orjson, agent-state (workspace); CLI: `agent-state-mcp` |
| `mece-decomposer` | `apps/mece-decomposer` | orjson |
| `readwise-reader` | `apps/readwise-reader` | mcp, httpx, duckdb, pydantic, authlib, skill-maintainer (workspace); opt-in (Python 3.13+, excluded by default) |

JS/TS: `skill-dashboard` at `apps/skill-dashboard/mcp-app` is a TypeScript ext-apps MCP App (gray-matter, react, zod); no Python deps.

Setup: `uv sync --all-packages` installs all member deps into a shared venv. `readwise-reader` is excluded from the default workspace; opt in by removing it from the `exclude` list in root `pyproject.toml`.


## Decision: no local copies of upstream docs (2026-07-21)

`docs/claude-docs/` held frozen copies of the upstream Claude Code pages. They
were deleted, and upstream is now fetched on demand into
`.skill-maintainer/state/pages/` (gitignored) via `skill-maintain upstream`.

**This is a trade, not a pure win, and the trade was made deliberately.** We
accepted an availability risk to remove a staleness risk:

- There is now **no offline fallback**. Working without network access, behind a
  restrictive proxy, or after a page is moved or restructured, there is nothing
  local to read.
- A moved URL fails at fetch time — later and noisier than a stale local file
  would have been.
- Re-fetching is not free: the twelve tracked pages total well over 1MB.

We took that because the failure modes are not symmetric. An absent doc
announces itself and you go read the real one. A stale doc teaches you something
false with total confidence — the February copies asserted that `allowed-tools`
restricts tool access and that hook exit 0 approves a call, both wrong, and
carried no date header to warn anyone. A reader cannot audit what they cannot
date.

**If you hit a fetch failure, do not quietly re-add local copies.** That
reintroduces the exact problem, and the copies will rot again on the same
timeline. Either fix the URL in `.skill-maintainer/config.json`, or if offline
work genuinely needs a pinned snapshot, add one *with a visible capture date in
the file itself* and a tracked expiry — the undated copy is what made the last
set unauditable.

## Designing a new check

Hard-won from building the checks in this repo and the explainer-video smoke
test. Both rules exist because a check was built that looked right and was not.

### A proxy can reject; it cannot approve

A heuristic has a confident region and an uncertain one. Give it authority only
over the confident region, and make it **silent** — not "warn" — everywhere else.

The failing example: a caption-readability check scored characters-per-second.
It correctly rejected 37 CPS as unreadable and was wrong at 27, where one person
watching three seconds of video overturned the whole model. The bug was not the
threshold, it was granting the metric decision authority across its entire range
when it only had authority at one end.

A warning band over the uncertain region is the worst option available. It
trains people to skim past the check's output, which destroys the loud case too
— the permanently-red-board failure in miniature. Exact checks (version
alignment, spec compliance, link-rot) can legitimately gate. Perceptual or
heuristic checks get a floor, silence above it, and nothing in between.

### Build the control

For any claim that a technique or check improves something, build the version
without it and confirm that one is worse. Otherwise you have measured your own
effort rather than the effect. Three forms:

- a **technique** needs a without-it comparison
- a **check** needs a constructed failing case, proving it actually fires
- a **threshold** needs bracketing: one confirmed-bad observation below it and
  one confirmed-fine observation above

This is why `check_version_alignment` was verified by re-injecting the exact
historical `path-privacy` drift, and why the explainer-video blank-frame check
was verified against a deliberately empty scene. A check nobody has seen fail is
not known to work.

### Freshness checks do not catch wrongness

`review_interval_days` and `check_version_alignment` both detect **drift over
time**. Neither catches a document that was wrong on the day it was written.

The worked example: `references/method.md` has stated since day one that 3-4
seconds per beat is the pacing that reads. The example shipped alongside it ran
2.4 / 2.4 / 3.2 — below its own stated floor on two of three beats. Nothing was
stale; the doc and the artifact simply disagreed from the start, and it surfaced
only when a human watched the video and said it felt too fast.

If a document states a numeric threshold that governs an artifact in this repo,
something should compare the two. That is a consistency check, and we do not
currently have a general one.
