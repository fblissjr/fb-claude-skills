"""Batch sync engine: Readwise Reader API -> DuckDB."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.storage.database import Database

logger = logging.getLogger(__name__)


class SyncEngine:
    """Syncs data from Readwise Reader API to local DuckDB."""

    def __init__(self, client: ReadwiseClient, db: Database) -> None:
        self.client = client
        self.db = db

    async def sync_documents(self, full: bool = False) -> dict[str, int]:
        """Sync documents from Readwise API to DuckDB.

        If full=False, uses incremental sync from last known timestamp.
        Returns counts of created/updated documents.
        """
        updated_after: str | None = None
        if not full:
            updated_after = self.db.get_sync_value("last_doc_sync")

        logger.info(
            "Starting %s document sync (updated_after=%s)",
            "full" if full else "incremental",
            updated_after,
        )

        docs = await self.client.list_all_documents(updated_after=updated_after)
        created = 0
        updated = 0

        for doc in docs:
            doc_dict = doc.model_dump()
            existing = self.db.get_document(doc_dict["id"])
            self.db.upsert_document(doc_dict)

            if existing:
                updated += 1
                self.db.log_change(doc_dict["id"], "update", "sync")
            else:
                created += 1
                self.db.log_change(doc_dict["id"], "create", "sync")

            # Sync tags from document
            if doc_dict.get("tags"):
                for tag_name in doc_dict["tags"]:
                    tag_key = tag_name.lower().replace(" ", "-")
                    self.db.upsert_tag(tag_key, tag_name)

        # Update sync timestamp and rebuild search indexes
        now = datetime.now(UTC).isoformat()
        self.db.set_sync_value("last_doc_sync", now)
        self.db.rebuild_fts_indexes()

        logger.info("Document sync complete: %d created, %d updated", created, updated)
        return {"created": created, "updated": updated}

    def _resolve_doc_id(self, v2_book_id: int, source_url: str | None) -> str:
        """Resolve a v2 book ID to a v3 document ID using three-tier lookup.

        1. Direct v2_book_id mapping on dim_documents
        2. URL match (source_url or url), then store the v2_book_id mapping
        3. Fallback: "v2:{id}" prefix (reconciled later in full_sync)
        """
        doc_id = self.db.get_doc_id_by_v2_book_id(v2_book_id)
        if doc_id:
            return doc_id

        if source_url:
            doc_id = self.db.get_doc_id_by_url(source_url)
            if doc_id:
                self.db.set_v2_book_id(doc_id, v2_book_id)
                return doc_id

        return f"v2:{v2_book_id}"

    async def sync_highlights(self, full: bool = False) -> dict[str, int]:
        """Sync highlights from Readwise API (v2 export) to DuckDB."""
        updated_after: str | None = None
        if not full:
            updated_after = self.db.get_sync_value("last_highlight_sync")

        logger.info(
            "Starting %s highlight sync (updated_after=%s)",
            "full" if full else "incremental",
            updated_after,
        )

        total_highlights = 0
        cursor: str | None = None

        while True:
            result = await self.client.export_highlights(
                updated_after=updated_after, page_cursor=cursor
            )
            for book in result.results:
                doc_id = self._resolve_doc_id(book.user_book_id, book.source_url)
                for highlight in book.highlights:
                    h_dict = highlight.model_dump()
                    self.db.upsert_highlight(h_dict, doc_id)
                    total_highlights += 1

            cursor = result.nextPageCursor
            if not cursor:
                break

        now = datetime.now(UTC).isoformat()
        self.db.set_sync_value("last_highlight_sync", now)

        logger.info("Highlight sync complete: %d highlights processed", total_highlights)
        return {"highlights_synced": total_highlights}

    async def sync_tags(self) -> dict[str, int]:
        """Sync all tags from Readwise API."""
        tags = await self.client.list_all_tags()
        for tag in tags:
            self.db.upsert_tag(tag["key"], tag["name"])
        self.db.refresh_tag_counts()
        logger.info("Tag sync complete: %d tags", len(tags))
        return {"tags_synced": len(tags)}

    async def full_sync(self) -> dict[str, dict[str, int]]:
        """Run a full sync of documents, highlights, and tags."""
        doc_result = await self.sync_documents(full=True)
        highlight_result = await self.sync_highlights(full=True)
        tag_result = await self.sync_tags()

        reconciled = self.db.reconcile_orphaned_highlights()
        if reconciled:
            logger.info("Reconciled %d orphaned highlights", reconciled)

        self.db.rebuild_fts_indexes()

        now = datetime.now(UTC).isoformat()
        self.db.set_sync_value("last_full_sync", now)

        return {
            "documents": doc_result,
            "highlights": highlight_result,
            "tags": tag_result,
            "highlights_reconciled": reconciled,
        }
