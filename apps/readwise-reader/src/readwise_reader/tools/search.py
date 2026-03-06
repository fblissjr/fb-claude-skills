"""MCP tools for search operations (DuckDB-backed)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from readwise_reader.storage.database import Database


def _get_db(ctx: Context) -> Database:  # type: ignore[type-arg]
    return ctx.request_context.lifespan_context.db


def register_search_tools(mcp: FastMCP) -> None:
    """Register search-related MCP tools."""

    @mcp.tool()
    async def search_library(
        ctx: Context[ServerSession, Any],
        query: str,
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search your Readwise Reader library using full-text search.

        Searches across document titles, summaries, notes, and content
        in the local DuckDB database.

        Args:
            query: Search terms.
            category: Filter by type: article, email, rss, pdf, epub, tweet, video, note.
            location: Filter by location: new (inbox), later, archive, feed.
            tag: Filter by tag name.
            limit: Max results (default 20).

        Returns:
            Matching documents ranked by recency.
        """
        db = _get_db(ctx)
        # If filters are provided, combine with search
        if category or location or tag:
            filtered = db.query_documents(
                category=category, location=location, tag=tag, limit=200
            )
            query_lower = query.lower()
            results = []
            for doc in filtered:
                searchable = " ".join(
                    str(v) for v in [doc.get("title"), doc.get("summary"), doc.get("notes")]
                    if v
                ).lower()
                if query_lower in searchable:
                    results.append(doc)
                    if len(results) >= limit:
                        break
            return results
        return db.search_documents(query, limit=limit)

    @mcp.tool()
    async def search_highlights(
        ctx: Context[ServerSession, Any],
        query: str,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search across your highlights and annotations.

        Args:
            query: Search terms to match against highlight text and notes.
            tag: Optional tag filter.
            limit: Max results (default 20).

        Returns:
            Matching highlights with their source document info.
        """
        db = _get_db(ctx)
        return db.search_highlights(query, tag=tag, limit=limit)
