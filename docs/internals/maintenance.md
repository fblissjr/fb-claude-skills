last updated: 2026-05-04

# Maintenance

Mechanisms and commands that keep this repo's content current. Most run on demand; a few fire automatically via git or Claude Code hooks.

## Automatic checks

| Concern | Mechanism | Trigger |
|---------|-----------|---------|
| SKILL.md spec compliance | Pre-commit git hook (skills-ref) | On commit |
| Plugin version alignment | Pre-commit git hook | On commit (hard block) |
| Unbumped content changes | Pre-commit git hook | On commit (warning only) |
| CLAUDE.md size creep | Pre-commit git hook | On commit (warning only) |
| Bundled best_practices.md drift | skill-maintainer PostToolUse hook (`sync-bundled-ref.sh`) | On Edit/Write of working copy |
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
| Bump version across plugin.json + marketplace.json + primary SKILL.md + plugin pyproject.toml | `/skill-maintainer:sync-versions <plugin> <ver>` |
| Mirror `.skill-maintainer/best_practices.md` → bundled reference (fallback if hook didn't fire) | `/skill-maintainer:sync-bundled-ref` |
| Append-only audit log query | `skill-maintain log` |
| Wiki sanity (orphans in `docs/analysis/`, count drift in READMEs / CLAUDE.md) | `skill-maintain lint` |
| Per-project dependency vulnerability scan | `/dev-conventions:dep-audit` |
| Cross-project dependency scan (macOS) | `./tools/dep-audit-scan.sh` |
| Promote `agent-state` MCP server from `_available_servers` → `mcpServers` | `/agent-state-mcp:enable` |

## Lower-level CLI

```bash
skill-maintain validate --all                    # validate all skills
skill-maintain measure                           # token budget report
skill-maintain freshness                         # SKILL.md staleness check (uses metadata.last_verified)
skill-maintain init                              # initialize .skill-maintainer/ in a new repo
uv run agentskills validate path/to/SKILL.md     # validate a single skill (low-level, called by pre-commit)
```

All commands accept `--dir <path>` to target a different repo.

## State files

- `.skill-maintainer/state/upstream_hashes.json` — page content hashes for upstream change detection (auto-generated, gitignored)
- `.skill-maintainer/state/pages/<slug>.md` — per-page content snapshots for line/char delta computation (v0.4.0+, auto-generated)
- `.skill-maintainer/state/changes.jsonl` — append-only audit log of quality reports, upstream checks, source pulls (consumed by `skill-maintain log`)
- Each `SKILL.md`'s `metadata.last_verified` — date the skill was last reviewed; consumed by `skill-maintain freshness`
- `<HOME>/.claude/agent_state.duckdb` — global DuckDB for run audit and state tracking across all projects (schema in `tools/agent-state/`)

## Workspace members (Python)

Python managed as a uv workspace. The root `pyproject.toml` coordinates members, each declaring its own deps.

| Member | Path | Key dependencies |
|--------|------|-----------------|
| `skill-maintainer` | `tools/skill-maintainer` | orjson, httpx, skills-ref; CLI: `skill-maintain` |
| `agent-state` | `tools/agent-state` | orjson, duckdb; CLI: `agent-state` |
| `agent-state-mcp` | `apps/agent-state-mcp` | mcp, duckdb, orjson, agent-state (workspace); CLI: `agent-state-mcp` |
| `env-forge` | `apps/env-forge` | orjson, huggingface-hub |
| `mece-decomposer` | `apps/mece-decomposer` | orjson |
| `readwise-reader` | `apps/readwise-reader` | mcp, httpx, duckdb, pydantic, authlib, skill-maintainer (workspace); opt-in (Python 3.13+, excluded by default) |

JS/TS: `skill-dashboard` at `apps/skill-dashboard/mcp-app` is a TypeScript ext-apps MCP App (gray-matter, react, zod); no Python deps.

Setup: `uv sync --all-packages` installs all member deps into a shared venv. `readwise-reader` is excluded from the default workspace; opt in by removing it from the `exclude` list in root `pyproject.toml`.
