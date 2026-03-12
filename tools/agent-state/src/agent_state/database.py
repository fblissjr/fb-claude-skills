"""DuckDB connection management and schema initialization."""

from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".claude" / "agent_state.duckdb"
SCHEMA_VERSION = 2


class AgentStateDB:
    """DuckDB database for agent run audit and state tracking.

    Manages connection lifecycle and provides query helpers.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_file = (
            importlib.resources.files("agent_state")
            / "schemas"
            / "agent_state.sql"
        )
        schema_sql = schema_file.read_text()
        self.conn.execute(schema_sql)
        logger.info("Database schema initialized at %s", self.db_path)

    def schema_version(self) -> int:
        """Return current schema version."""
        result = self.conn.execute(
            "SELECT MAX(version) FROM meta_schema_version"
        ).fetchone()
        return result[0] if result and result[0] else 0

    def execute(self, sql: str, params: list | None = None) -> duckdb.DuckDBPyConnection:
        """Execute SQL with optional parameters."""
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def fetchone(self, sql: str, params: list | None = None) -> tuple | None:
        """Execute and fetch one row."""
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: list | None = None) -> list[tuple]:
        """Execute and fetch all rows."""
        return self.execute(sql, params).fetchall()

    def fetchall_dicts(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute and fetch all rows as dicts."""
        result = self.execute(sql, params)
        if not result.description:
            return []
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> AgentStateDB:
        return self

    def __exit__(self, *args) -> None:
        self.close()
