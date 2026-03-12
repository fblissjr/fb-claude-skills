# agent-state backlog

Items for future development. Not prioritized -- just captured.

## CLI subcommands for routing and lifecycle

The `domain`, `task_type`, and `status` columns are queryable via the Python API but have no CLI exposure yet. Candidates:

- `agent-state skills` -- list tracked skill versions with domain/status filters (`--domain extraction`, `--status active`)
- `agent-state deprecate <skill_version_id>` -- mark a skill version as deprecated from the command line
- `agent-state domains` -- show distinct domains and their skill counts

Low priority: the Python API covers programmatic use, and ad-hoc queries via `duckdb` CLI work for exploration.

## populate domain/task_type from SKILL.md frontmatter

When `get_or_create_skill_version()` is called during migration or maintenance runs, auto-extract `domain` and `task_type` from SKILL.md frontmatter if not explicitly provided. Would require:

- A convention for where domain/task_type live in frontmatter (e.g., `metadata.domain`, `metadata.task_type`)
- Agreement on the taxonomy (what are the valid domains?)
- Integration with skill-maintainer's `discover_skills()` path

Blocked on: defining the domain taxonomy. The columns exist but the vocabulary is open.

## bridge to freudagent meta-framework schema

The `dim_skill_version` columns (`domain`, `task_type`, `status`) were derived from the freudagent meta-framework schema (`~/workspace/freudagent/internal/20260312-meta_framework_schema.md`). If freudagent materializes as a standalone system, agent-state should be able to export or sync skill versions into the freudagent `skills` table. The column mapping is direct:

| agent-state | freudagent |
|-------------|------------|
| `skill_name` | `id` (or name lookup) |
| `domain` | `domain` |
| `task_type` | `task_type` |
| `status` | `status` |
| `version_hash` | (no equivalent -- freudagent uses integer version) |

## v_active_skills view

A convenience view filtering `dim_skill_version` to only `status = 'active'` rows, with latest-version-per-skill semantics. Would simplify common queries and could be used by the flywheel view to exclude deprecated skills.

## run-level domain tagging

Currently `domain` lives on `dim_skill_version`. Consider whether `fact_run` should also carry a `domain` column for runs that aren't tied to a specific skill but serve a particular domain. Would enable "show me all extraction runs" without joining through skill versions.
