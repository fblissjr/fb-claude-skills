"""MCP server for the agent-state DuckDB.

Exposes ~/.claude/agent_state.duckdb as structured MCP tools so Claude Code
can query run history, watermarks, skill versions, and flywheel metrics
without shelling out to the ``agent-state`` CLI.
"""

from __future__ import annotations

__version__ = "0.1.0"
