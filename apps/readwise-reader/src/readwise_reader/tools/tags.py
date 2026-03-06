"""MCP tools for tag operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from readwise_reader.storage.database import Database


def _get_db(ctx: Context) -> Database:  # type: ignore[type-arg]
    return ctx.request_context.lifespan_context.db


def register_tag_tools(mcp: FastMCP) -> None:
    """Register tag-related MCP tools."""

    @mcp.tool()
    async def list_tags(
        ctx: Context[ServerSession, Any],
    ) -> list[dict[str, Any]]:
        """List all tags with usage counts.

        Returns:
            Tags sorted by document count, each with key, name, doc_count, highlight_count.
        """
        db = _get_db(ctx)
        return db.get_all_tags()

    @mcp.tool()
    async def get_documents_by_tag(
        ctx: Context[ServerSession, Any],
        tag: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get all documents with a specific tag.

        Args:
            tag: The tag name to filter by.
            limit: Max results (default 50).

        Returns:
            Documents matching the tag.
        """
        db = _get_db(ctx)
        return db.query_documents(tag=tag, limit=limit)
