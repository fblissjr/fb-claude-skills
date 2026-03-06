"""Webhook receiver for real-time sync from Readwise."""

from __future__ import annotations

import hmac
import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from readwise_reader.api.models import WebhookDocumentPayload, WebhookHighlightPayload
from readwise_reader.storage.database import Database

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles incoming Readwise webhooks and syncs to DuckDB."""

    def __init__(self, db: Database, webhook_secret: str | None = None) -> None:
        self.db = db
        self.webhook_secret = webhook_secret

    def verify_secret(self, payload_secret: str | None) -> bool:
        """Verify the webhook secret from the payload."""
        if not self.webhook_secret:
            return True  # No secret configured, accept all
        if not payload_secret:
            return False
        return hmac.compare_digest(self.webhook_secret, payload_secret)

    async def handle_webhook(self, request: Request) -> Response:
        """Process an incoming webhook request."""
        try:
            body: dict[str, Any] = await request.json()
        except Exception:
            logger.warning("Invalid webhook payload")
            return JSONResponse({"error": "invalid payload"}, status_code=400)

        # Verify secret
        if not self.verify_secret(body.get("secret")):
            logger.warning("Webhook secret verification failed")
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        event_type = body.get("event_type", "")
        logger.info("Received webhook event: %s", event_type)

        if event_type.startswith("reader.") or event_type.startswith("reader.any_document"):
            self._handle_document_event(body)
        elif event_type.startswith("readwise.highlight"):
            self._handle_highlight_event(body)
        else:
            logger.warning("Unknown webhook event type: %s", event_type)

        return JSONResponse({"status": "ok"})

    def _handle_document_event(self, payload: dict[str, Any]) -> None:
        """Process a document webhook event."""
        doc = WebhookDocumentPayload.model_validate(payload)
        doc_dict = doc.model_dump(exclude={"secret", "event_type"})
        self.db.upsert_document(doc_dict)
        self.db.log_change(doc.id, "update", f"webhook:{doc.event_type}")

        if doc.tags:
            for tag_name in doc.tags:
                tag_key = tag_name.lower().replace(" ", "-")
                self.db.upsert_tag(tag_key, tag_name)

        logger.info("Webhook: upserted document %s (%s)", doc.id, doc.event_type)

    def _resolve_doc_id(self, book_id: int | None, source_url: str | None) -> str:
        """Resolve a v2 book ID to a v3 document ID (three-tier lookup)."""
        if not book_id:
            return "unknown"

        doc_id = self.db.get_doc_id_by_v2_book_id(book_id)
        if doc_id:
            return doc_id

        if source_url:
            doc_id = self.db.get_doc_id_by_url(source_url)
            if doc_id:
                self.db.set_v2_book_id(doc_id, book_id)
                return doc_id

        return f"v2:{book_id}"

    def _handle_highlight_event(self, payload: dict[str, Any]) -> None:
        """Process a highlight webhook event."""
        highlight = WebhookHighlightPayload.model_validate(payload)
        h_dict = highlight.model_dump(exclude={"secret", "event_type"})
        doc_id = self._resolve_doc_id(highlight.book_id, highlight.url)
        self.db.upsert_highlight(h_dict, doc_id)
        logger.info("Webhook: upserted highlight %s", highlight.id)
