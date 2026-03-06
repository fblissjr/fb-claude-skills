"""MCP tools for reading activity summaries and library stats."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.storage.database import Database
from readwise_reader.storage.sync import SyncEngine


def _get_deps(ctx: Context) -> tuple[ReadwiseClient, Database]:  # type: ignore[type-arg]
    app_ctx = ctx.request_context.lifespan_context
    return app_ctx.client, app_ctx.db


def register_digest_tools(mcp: FastMCP) -> None:
    """Register digest and stats MCP tools."""

    @mcp.tool()
    async def library_stats(
        ctx: Context[ServerSession, Any],
    ) -> dict[str, Any]:
        """Get library statistics.

        Returns counts by category and location, total documents/highlights/tags,
        inbox size, and last sync time.
        """
        _, db = _get_deps(ctx)
        return db.library_stats()

    @mcp.tool()
    async def reading_digest(
        ctx: Context[ServerSession, Any],
        since: str | None = None,
    ) -> dict[str, Any]:
        """Get a summary of recent reading activity.

        Args:
            since: ISO 8601 date. Defaults to last 7 days if not provided.

        Returns:
            Summary of documents saved, archived, and highlighted since the date.
        """
        _, db = _get_deps(ctx)
        from datetime import datetime, timedelta

        if not since:
            since = (datetime.now(UTC) - timedelta(days=7)).isoformat()

        recent_docs = db.query_documents(since=since, limit=200)

        # Break down by location
        by_location: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for doc in recent_docs:
            loc = doc.get("location", "unknown") or "unknown"
            by_location[loc] = by_location.get(loc, 0) + 1
            cat = doc.get("category", "unknown") or "unknown"
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "since": since,
            "total_documents": len(recent_docs),
            "by_location": by_location,
            "by_category": by_category,
            "recent_titles": [
                {
                    "title": d.get("title"),
                    "category": d.get("category"),
                    "location": d.get("location"),
                }
                for d in recent_docs[:10]
            ],
        }

    @mcp.tool()
    async def sync_library(
        ctx: Context[ServerSession, Any],
        full: bool = False,
    ) -> dict[str, Any]:
        """Sync your Readwise Reader library to local storage.

        Pulls documents, highlights, and tags from the Readwise API
        into the local DuckDB database for fast querying.

        Args:
            full: If True, re-sync everything. If False, only sync changes since last sync.

        Returns:
            Sync results with counts of created/updated items.
        """
        client, db = _get_deps(ctx)
        engine = SyncEngine(client, db)
        if full:
            return await engine.full_sync()
        doc_result = await engine.sync_documents()
        tag_result = await engine.sync_tags()
        return {"documents": doc_result, "tags": tag_result}

    @mcp.tool()
    async def get_highlights(
        ctx: Context[ServerSession, Any],
        doc_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get highlights, optionally filtered by document.

        Args:
            doc_id: Optional document ID to filter highlights.
            limit: Max results (default 50).

        Returns:
            Highlights with their source document info.
        """
        _, db = _get_deps(ctx)
        return db.get_highlights(doc_id=doc_id, limit=limit)
