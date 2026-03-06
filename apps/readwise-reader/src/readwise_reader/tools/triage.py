"""MCP tools for inbox triage operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.api.models import UpdateDocumentRequest
from readwise_reader.storage.database import Database


def _get_deps(ctx: Context) -> tuple[ReadwiseClient, Database]:  # type: ignore[type-arg]
    app_ctx = ctx.request_context.lifespan_context
    return app_ctx.client, app_ctx.db


def register_triage_tools(mcp: FastMCP) -> None:
    """Register inbox triage MCP tools."""

    @mcp.tool()
    async def get_inbox(
        ctx: Context[ServerSession, Any],
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get items in your Reader inbox (location='new') for triage.

        Args:
            category: Optional filter by type (article, email, rss, etc.).
            limit: Max results (default 20).

        Returns:
            Inbox items sorted by most recent first.
        """
        _, db = _get_deps(ctx)
        return db.query_documents(location="new", category=category, limit=limit)

    @mcp.tool()
    async def triage_document(
        ctx: Context[ServerSession, Any],
        doc_id: str,
        action: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Triage a document: move it to 'later', 'archive', or delete it.

        Args:
            doc_id: The document ID to triage.
            action: One of 'later' (keep for reading), 'archive' (done), 'delete' (remove).
            tags: Optional tags to apply during triage.

        Returns:
            Result of the triage action.
        """
        client, db = _get_deps(ctx)

        if action == "delete":
            success = await client.delete_document(doc_id)
            if success:
                db.delete_document(doc_id)
                db.log_change(doc_id, "delete", "triage")
                return {"triaged": True, "action": "delete", "doc_id": doc_id}
            return {"triaged": False, "error": f"Failed to delete {doc_id}"}

        if action not in ("later", "archive"):
            return {
                "triaged": False,
                "error": f"Invalid action: {action}. Use 'later', 'archive', or 'delete'.",
            }

        request = UpdateDocumentRequest(location=action, tags=tags)
        await client.update_document(doc_id, request)
        doc = await client.get_document(doc_id)
        if doc:
            db.upsert_document(doc.model_dump())
        db.log_change(doc_id, "update", f"triage:{action}")
        return {"triaged": True, "action": action, "doc_id": doc_id}

    @mcp.tool()
    async def batch_triage(
        ctx: Context[ServerSession, Any],
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Triage multiple documents at once.

        Args:
            actions: List of {"doc_id": "...", "action": "later|archive|delete", "tags": [...]}.

        Returns:
            List of results for each action.
        """
        results = []
        client, db = _get_deps(ctx)
        for item in actions:
            doc_id = item.get("doc_id", "")
            action = item.get("action", "")
            tags = item.get("tags")

            if action == "delete":
                success = await client.delete_document(doc_id)
                if success:
                    db.delete_document(doc_id)
                    db.log_change(doc_id, "delete", "batch_triage")
                results.append({"doc_id": doc_id, "action": action, "success": success})
            elif action in ("later", "archive"):
                try:
                    request = UpdateDocumentRequest(location=action, tags=tags)
                    await client.update_document(doc_id, request)
                    db.log_change(doc_id, "update", f"batch_triage:{action}")
                    results.append({"doc_id": doc_id, "action": action, "success": True})
                except Exception as e:
                    results.append({
                        "doc_id": doc_id, "action": action,
                        "success": False, "error": str(e),
                    })
            else:
                results.append({
                    "doc_id": doc_id, "action": action,
                    "success": False, "error": "invalid action",
                })

        return results
