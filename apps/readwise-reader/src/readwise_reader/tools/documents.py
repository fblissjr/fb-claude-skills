"""MCP tools for document operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.api.models import SaveDocumentRequest, UpdateDocumentRequest
from readwise_reader.storage.database import Database


def _get_deps(ctx: Context) -> tuple[ReadwiseClient, Database]:  # type: ignore[type-arg]
    """Extract client and database from lifespan context."""
    app_ctx = ctx.request_context.lifespan_context
    return app_ctx.client, app_ctx.db


def register_document_tools(mcp: FastMCP) -> None:
    """Register document-related MCP tools."""

    @mcp.tool()
    async def save_document(
        ctx: Context[ServerSession, Any],
        url: str,
        title: str | None = None,
        tags: list[str] | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Save a URL to Readwise Reader.

        Args:
            url: The URL to save.
            title: Optional custom title.
            tags: Optional list of tags to apply.
            location: Where to save: 'new' (inbox), 'later', 'archive', 'feed'.
            notes: Optional note to attach.

        Returns:
            The saved document's ID and URL.
        """
        client, db = _get_deps(ctx)
        request = SaveDocumentRequest(
            url=url,
            title=title,
            tags=tags,
            location=location,
            notes=notes,
            saved_using="readwise-reader-mcp",
        )
        result = await client.save_document(request)
        # Sync the newly saved document to local DB
        doc = await client.get_document(result.id)
        if doc:
            db.upsert_document(doc.model_dump())
        return {"id": result.id, "url": result.url}

    @mcp.tool()
    async def list_documents(
        ctx: Context[ServerSession, Any],
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
        since: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List documents from your Readwise Reader library.

        Queries the local DuckDB cache for fast results. Run sync_library first
        if you need the latest data.

        Args:
            category: Filter by type: article, email, rss, pdf, epub, tweet, video, note.
            location: Filter by location: new (inbox), later, archive, feed.
            tag: Filter by tag name.
            since: ISO 8601 date to filter documents updated after.
            limit: Max results (default 20).

        Returns:
            List of document summaries.
        """
        _, db = _get_deps(ctx)
        return db.query_documents(
            category=category,
            location=location,
            tag=tag,
            since=since,
            limit=limit,
        )

    @mcp.tool()
    async def get_document(
        ctx: Context[ServerSession, Any],
        doc_id: str,
        include_content: bool = False,
    ) -> dict[str, Any]:
        """Get a single document by ID.

        Args:
            doc_id: The Readwise document ID.
            include_content: Whether to fetch full HTML content from the API.

        Returns:
            Document details including metadata and optionally content.
        """
        client, db = _get_deps(ctx)
        if include_content:
            doc = await client.get_document(doc_id, include_content=True)
            if doc:
                db.upsert_document(doc.model_dump())
                return doc.model_dump()
            return {"error": f"Document {doc_id} not found"}
        local = db.get_document(doc_id)
        if local:
            return local
        doc = await client.get_document(doc_id)
        if doc:
            db.upsert_document(doc.model_dump())
            return doc.model_dump()
        return {"error": f"Document {doc_id} not found"}

    @mcp.tool()
    async def update_document(
        ctx: Context[ServerSession, Any],
        doc_id: str,
        location: str | None = None,
        tags: list[str] | None = None,
        title: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update a document in Readwise Reader.

        Args:
            doc_id: The Readwise document ID to update.
            location: Move to: 'new', 'later', 'archive', 'feed'.
            tags: Replace all tags with this list.
            title: New title.
            notes: New note.

        Returns:
            Update confirmation.
        """
        client, db = _get_deps(ctx)
        request = UpdateDocumentRequest(
            location=location,
            tags=tags,
            title=title,
            notes=notes,
        )
        result = await client.update_document(doc_id, request)
        # Re-sync the updated document
        doc = await client.get_document(doc_id)
        if doc:
            db.upsert_document(doc.model_dump())
        return result

    @mcp.tool()
    async def delete_document(
        ctx: Context[ServerSession, Any],
        doc_id: str,
    ) -> dict[str, Any]:
        """Delete a document from Readwise Reader.

        Args:
            doc_id: The Readwise document ID to delete.

        Returns:
            Deletion confirmation.
        """
        client, db = _get_deps(ctx)
        success = await client.delete_document(doc_id)
        if success:
            db.delete_document(doc_id)
            db.log_change(doc_id, "delete", "user_request")
            return {"deleted": True, "doc_id": doc_id}
        return {"deleted": False, "error": f"Failed to delete {doc_id}"}
