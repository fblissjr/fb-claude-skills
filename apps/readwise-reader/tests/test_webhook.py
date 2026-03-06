"""Integration tests for the webhook handler."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from readwise_reader.storage.database import Database
from readwise_reader.storage.webhook_handler import WebhookHandler


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.duckdb")


@pytest.fixture
def handler_with_secret(db: Database) -> WebhookHandler:
    return WebhookHandler(db=db, webhook_secret="test-secret-123")


@pytest.fixture
def handler_no_secret(db: Database) -> WebhookHandler:
    return WebhookHandler(db=db)


@pytest.fixture
def client_with_secret(handler_with_secret: WebhookHandler) -> TestClient:
    app = Starlette(routes=[
        Route("/webhook", handler_with_secret.handle_webhook, methods=["POST"]),
    ])
    return TestClient(app)


@pytest.fixture
def client_no_secret(handler_no_secret: WebhookHandler) -> TestClient:
    app = Starlette(routes=[
        Route("/webhook", handler_no_secret.handle_webhook, methods=["POST"]),
    ])
    return TestClient(app)


class TestWebhookAuth:
    def test_rejects_missing_secret(self, client_with_secret: TestClient) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "reader.any_document.created",
            "id": "doc-1",
        })
        assert resp.status_code == 401
        assert resp.json()["error"] == "unauthorized"

    def test_rejects_wrong_secret(self, client_with_secret: TestClient) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "reader.any_document.created",
            "id": "doc-1",
            "secret": "wrong-secret",
        })
        assert resp.status_code == 401

    def test_accepts_correct_secret(self, client_with_secret: TestClient) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "reader.any_document.created",
            "id": "doc-1",
            "title": "Test Article",
            "secret": "test-secret-123",
        })
        assert resp.status_code == 200

    def test_no_secret_configured_accepts_all(self, client_no_secret: TestClient) -> None:
        resp = client_no_secret.post("/webhook", json={
            "event_type": "reader.any_document.created",
            "id": "doc-1",
        })
        assert resp.status_code == 200


class TestWebhookDocumentEvents:
    def test_document_created(
        self, client_with_secret: TestClient, handler_with_secret: WebhookHandler
    ) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "reader.any_document.created",
            "id": "doc-abc",
            "title": "New Article from Webhook",
            "url": "https://example.com/new-article",
            "category": "article",
            "location": "new",
            "secret": "test-secret-123",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        doc = handler_with_secret.db.get_document("doc-abc")
        assert doc is not None
        assert doc["title"] == "New Article from Webhook"
        assert doc["category"] == "article"

    def test_document_updated(
        self, client_with_secret: TestClient, handler_with_secret: WebhookHandler
    ) -> None:
        # First create
        handler_with_secret.db.upsert_document({
            "id": "doc-abc",
            "title": "Original Title",
            "location": "new",
        })

        # Then update via webhook
        resp = client_with_secret.post("/webhook", json={
            "event_type": "reader.any_document.updated",
            "id": "doc-abc",
            "title": "Updated Title",
            "location": "later",
            "secret": "test-secret-123",
        })
        assert resp.status_code == 200

        doc = handler_with_secret.db.get_document("doc-abc")
        assert doc["title"] == "Updated Title"
        assert doc["location"] == "later"


class TestWebhookHighlightEvents:
    def test_highlight_created(
        self, client_with_secret: TestClient, handler_with_secret: WebhookHandler
    ) -> None:
        # Pre-create a document with a known v2_book_id
        handler_with_secret.db.upsert_document({
            "id": "doc-real",
            "title": "Test Doc",
            "v2_book_id": 42,
        })

        resp = client_with_secret.post("/webhook", json={
            "event_type": "readwise.highlight.created",
            "id": 12345,
            "text": "This is a highlighted passage",
            "note": "Great insight",
            "book_id": 42,
            "secret": "test-secret-123",
        })
        assert resp.status_code == 200

        # Highlight should be linked to the real document via v2_book_id reconciliation
        highlights = handler_with_secret.db.get_highlights(doc_id="doc-real")
        assert len(highlights) == 1
        assert highlights[0]["content_text"] == "This is a highlighted passage"

    def test_highlight_with_unknown_book(
        self, client_with_secret: TestClient, handler_with_secret: WebhookHandler
    ) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "readwise.highlight.created",
            "id": 99999,
            "text": "Orphaned highlight text",
            "book_id": 777,
            "secret": "test-secret-123",
        })
        assert resp.status_code == 200

        # Should be in staging_highlights with v2: prefix since no matching document exists
        result = handler_with_secret.db.conn.execute(
            "SELECT doc_id FROM staging_highlights WHERE highlight_id = '99999'"
        ).fetchone()
        assert result is not None
        assert result[0] == "v2:777"

        # Should NOT be in fact_highlights (FK would reject it)
        fact_result = handler_with_secret.db.conn.execute(
            "SELECT COUNT(*) FROM fact_highlights WHERE highlight_id = '99999'"
        ).fetchone()
        assert fact_result[0] == 0


class TestWebhookErrorHandling:
    def test_unknown_event_type(self, client_with_secret: TestClient) -> None:
        resp = client_with_secret.post("/webhook", json={
            "event_type": "some.unknown.event",
            "id": "whatever",
            "secret": "test-secret-123",
        })
        # Should return 200 (graceful handling, no crash)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_malformed_json(self, client_with_secret: TestClient) -> None:
        resp = client_with_secret.post(
            "/webhook",
            content=b"this is not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400
        assert "invalid" in resp.json()["error"]
