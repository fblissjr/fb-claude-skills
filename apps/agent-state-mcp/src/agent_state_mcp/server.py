"""agent-state MCP server.

Wraps the ``agent-state`` Python package as a FastMCP stdio server so Claude
Code can query run history, watermarks, skill versions, and flywheel metrics
via ergonomic MCP tools instead of shelling out to the ``agent-state`` CLI.

Tools are intentionally named around questions ("list_recent_runs",
"get_watermark_status") rather than raw tables (``SELECT ... FROM fact_run``).
All tools are read-only: writes happen via the existing ``agent-state`` CLI or
``RunContext`` in the host pipeline.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from agent_state_mcp import tools as T

logger = logging.getLogger(__name__)


SERVER_INSTRUCTIONS = """\
agent-state MCP server -- read-only access to ~/.claude/agent_state.duckdb.

Use these tools instead of `agent-state <subcommand>` via Bash. They are
structured, faster, and permission-managed. The CLI is for interactive
debugging only.

Common questions -> tool names:
- "what ran recently?"          -> list_recent_runs
- "show me the run tree"        -> get_run_tree
- "what's in run X?"            -> get_run (summary) / get_run_messages (logs)
- "current watermarks?"         -> get_watermark_status
- "what failed recently?"       -> find_failed_runs
- "database health / totals?"   -> get_database_status
- "skills in domain X?"         -> list_skills_by_domain
- "producer -> consumer chain?" -> get_flywheel_metrics

Every response includes a `_meta` envelope (row_count, duration_ms,
schema_version, optional hint). Rows are stable dicts safe to pipe into
further reasoning.
"""


def _env_db_path() -> Path | None:
    """Allow override via env var (matches the agent-state CLI's --db)."""
    raw = os.environ.get("AGENT_STATE_DB")
    return Path(raw).expanduser() if raw else None


def build_server() -> FastMCP:
    """Construct and return the FastMCP server with all tools registered."""
    mcp = FastMCP(name="agent-state", instructions=SERVER_INSTRUCTIONS)
    _register_tools(mcp)
    return mcp


def _register_tools(mcp: FastMCP) -> None:  # noqa: C901 - tool descriptions, not logic
    """Register every read-only tool.

    Docstrings on each tool are what the MCP client (Claude Code) sees as
    the tool description. They intentionally repeat trigger phrases and
    include WHEN+WHAT so Claude picks the right tool quickly.
    """

    db_path = _env_db_path()

    @mcp.tool()
    def list_recent_runs(
        limit: int = 20,
        run_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List the most recent runs from fact_run, newest first.

        USE WHEN: the user says "show me recent runs", "what ran recently",
        "latest pipeline runs", "agent history", or you would otherwise run
        `agent-state runs` via Bash.

        Args:
            limit: max rows to return (1-500, default 20).
            run_type: filter by run_type ('pipeline', 'agent_sdk', 'claude_code').
            status: filter by status ('running', 'success', 'failure', 'partial').

        Returns:
            `{rows: [...], _meta: {row_count, duration_ms, schema_version}}`.
            Each row has run_id, run_type, run_name, status, started_at,
            ended_at, duration_ms, and count columns.
        """
        return T.list_recent_runs(
            limit=limit, run_type=run_type, status=status, db_path=db_path
        )

    @mcp.tool()
    def get_run(run_id: str) -> dict[str, Any]:
        """Return the full fact_run row for a single run_id.

        USE WHEN: you already have a run_id (from list_recent_runs or the
        tree) and want full detail including CDC watermarks, token counts,
        and metadata. Preferred over shelling out to query DuckDB directly.

        Returns:
            `{data: <row dict>, _meta: {...}}`. `data` is null if no match.
        """
        return T.get_run(run_id=run_id, db_path=db_path)

    @mcp.tool()
    def get_run_tree(run_id: str | None = None) -> dict[str, Any]:
        """Hierarchical run tree (recursive CTE over parent_run_id).

        USE WHEN: the user says "show the run tree", "how are these runs
        related", "what spawned what", or you would run `agent-state tree`.
        Pass run_id to show a subtree; omit it for the full forest.

        Returns:
            `{rows: [...]}` ordered by started_at with a `depth` column for
            indentation.
        """
        return T.get_run_tree_tool(run_id=run_id, db_path=db_path)

    @mcp.tool()
    def get_run_messages(
        run_id: str,
        level: str | None = None,
    ) -> dict[str, Any]:
        """Structured log messages for a run (fact_run_message).

        USE WHEN: debugging a run, the user says "show me the logs for X",
        "what did run X say", or you want to inspect step-level events.

        Args:
            run_id: target run.
            level: optional filter ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        """
        return T.get_run_messages_tool(
            run_id=run_id, level=level, db_path=db_path
        )

    @mcp.tool()
    def find_failed_runs(
        since_days: int = 7,
        skill_name: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Find failed or partial runs within a recent window.

        USE WHEN: the user says "what broke recently", "show failures",
        "what's failing", "errors in the last week", or is triaging a
        regression. Narrower than find_restartable_failures.

        Args:
            since_days: window in days (1-3650, default 7).
            skill_name: optional -- matches either run_name or skills this
                run consumed/produced (joins through dim_skill_version).
            limit: max rows (default 50).
        """
        return T.find_failed_runs(
            since_days=since_days,
            skill_name=skill_name,
            limit=limit,
            db_path=db_path,
        )

    @mcp.tool()
    def find_restartable_failures() -> dict[str, Any]:
        """Failed runs flagged as restartable (v_restartable_failures view).

        USE WHEN: planning a retry sweep, the user says "what can I retry",
        "show restartable failures", or you want a curated list filtered
        to runs with is_restartable=TRUE.
        """
        return T.list_restartable_failures(db_path=db_path)

    @mcp.tool()
    def get_database_status() -> dict[str, Any]:
        """Summary stats for the whole database -- the 'dashboard view'.

        USE WHEN: the user says "is agent-state healthy", "how many runs",
        "database status", "agent-state summary", or you would run
        `agent-state status`. Cheap; safe to call often.

        Returns:
            `{data: {total_runs, by_status, by_type, active_watermarks,
              tracked_skills, total_messages, database_path}, _meta: {...}}`.
        """
        return T.get_database_status(db_path=db_path)

    @mcp.tool()
    def get_watermark_status(source_key: str | None = None) -> dict[str, Any]:
        """Current watermark values (v_latest_watermark), newest check first.

        USE WHEN: the user says "show watermarks", "where did we leave off",
        "what's the last sync cursor", "current watermarks", or you would
        run `agent-state watermarks`.

        Args:
            source_key: optional -- scope to a single source (e.g.
                'readwise.book_id'). Omit for all tracked sources.
        """
        return T.get_watermark_status(source_key=source_key, db_path=db_path)

    @mcp.tool()
    def get_watermark_history(
        source_key: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Historical watermark values for one source, newest first.

        USE WHEN: you need to see when a watermark last changed, diagnose
        stuck cursors, or confirm monotonic progression.
        """
        return T.get_watermark_history_tool(
            source_key=source_key, limit=limit, db_path=db_path
        )

    @mcp.tool()
    def get_run_watermark_changes(run_id: str) -> dict[str, Any]:
        """Watermarks that changed during one specific run.

        USE WHEN: you want to know what state a run advanced -- e.g.
        "did last night's ingest actually move the cursor?".
        """
        return T.get_run_watermark_changes(run_id=run_id, db_path=db_path)

    @mcp.tool()
    def list_skills_by_domain(
        domain: str,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        """Active skill versions in a routing domain (dim_skill_version).

        USE WHEN: the user says "what extraction skills do we have",
        "skills for validation", "skills in the X domain", or you want
        the routing view of registered skills. Only returns status='active'.

        Args:
            domain: e.g. 'extraction', 'validation', 'summarization'.
            task_type: optional finer filter (e.g.
                'structured_data_from_document').
        """
        return T.list_skills_by_domain(
            domain=domain, task_type=task_type, db_path=db_path
        )

    @mcp.tool()
    def list_skill_versions(
        skill_name: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Version history (content hashes) for a specific skill, newest first.

        USE WHEN: you want to see how a skill has evolved, or tie a run's
        consumes_skill_version_id back to a content hash.
        """
        return T.list_skill_versions(
            skill_name=skill_name, limit=limit, db_path=db_path
        )

    @mcp.tool()
    def get_active_skill_version(skill_name: str) -> dict[str, Any]:
        """Return the latest ACTIVE version row for a named skill, or null.

        USE WHEN: you need the current canonical version_hash / path /
        metadata for a skill by name.
        """
        return T.get_active_skill_version(skill_name=skill_name, db_path=db_path)

    @mcp.tool()
    def resolve_skill_version_by_hash(version_hash: str) -> dict[str, Any]:
        """Look up a dim_skill_version row by its SHA-256 content hash.

        USE WHEN: you have a version_hash (from a run record or SKILL.md
        digest) and need the skill_name, path, status, or routing metadata
        attached to it.
        """
        return T.resolve_skill_version_by_hash(
            version_hash=version_hash, db_path=db_path
        )

    @mcp.tool()
    def list_tracked_domains() -> dict[str, Any]:
        """Distinct routing domains with active skill counts.

        USE WHEN: exploring the routing space, the user says "what domains
        are tracked", or you want a cheap overview before drilling into
        list_skills_by_domain.
        """
        return T.list_tracked_domains(db_path=db_path)

    @mcp.tool()
    def get_flywheel_metrics(skill_name: str | None = None) -> dict[str, Any]:
        """Flywheel view: producer run -> skill version -> consumer run.

        USE WHEN: the user says "show the flywheel", "what produced X",
        "what consumed Y", "show the skill lineage chain", or you would
        run `agent-state flywheel`.

        Args:
            skill_name: optional -- scope to one skill's chain.
        """
        return T.get_flywheel_metrics(skill_name=skill_name, db_path=db_path)

    @mcp.tool()
    def list_run_sources() -> dict[str, Any]:
        """dim_run_source rows with run counts -- where runs originate.

        USE WHEN: auditing provenance, or the user asks "where are runs
        coming from" / "which pipelines are active".
        """
        return T.list_run_sources(db_path=db_path)

    @mcp.tool()
    def list_watermark_sources() -> dict[str, Any]:
        """dim_watermark_source rows -- everything we track a cursor for.

        USE WHEN: the user asks "what are we tracking watermarks on",
        "list watermark sources", or before calling get_watermark_history.
        """
        return T.list_watermark_sources(db_path=db_path)


# --- entry point -------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent-state-mcp",
        description=(
            "MCP server (stdio transport) over ~/.claude/agent_state.duckdb. "
            "Intended to be launched by Claude Code via .mcp.json."
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=(
            "Override the agent_state DuckDB path. Also respects the "
            "AGENT_STATE_DB env var."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging to stderr.",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List registered tools and exit (no server).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Start the stdio MCP server (or list tools with --list-tools)."""
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    if args.db:
        os.environ["AGENT_STATE_DB"] = str(args.db)

    mcp = build_server()

    if args.list_tools:
        # Surface the registered tool names for smoke-testing.
        import asyncio

        async def _dump() -> list[str]:
            tools = await mcp.list_tools()
            return sorted(t.name for t in tools)

        names = asyncio.run(_dump())
        print("agent-state MCP tools:")
        for name in names:
            print(f"  - {name}")
        return 0

    # FastMCP.run() drives stdio by default.
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
