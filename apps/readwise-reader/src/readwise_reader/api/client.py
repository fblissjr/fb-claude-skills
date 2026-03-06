"""Async Readwise Reader API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from readwise_reader.api.models import (
    Document,
    DocumentListResponse,
    HighlightExportResponse,
    ListDocumentsParams,
    SaveDocumentRequest,
    SaveDocumentResponse,
    TagListResponse,
    UpdateDocumentRequest,
)
from readwise_reader.api.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

READER_BASE_URL = "https://readwise.io"


class ReadwiseClient:
    """Async client for the Readwise Reader API.

    Wraps Reader API v3 (documents, tags) and Core API v2 (highlights, auth).
    Enforces rate limits: 20 req/min for reads, 50 req/min for writes.
    """

    def __init__(self, token: str, base_url: str = READER_BASE_URL) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Token {self.token}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        # Reader v3 rate limits
        self._read_limiter = TokenBucketRateLimiter(rate=20, period=60.0)
        self._write_limiter = TokenBucketRateLimiter(rate=50, period=60.0)

    async def close(self) -> None:
        await self._http.aclose()

    # -- Auth --

    async def validate_token(self) -> bool:
        """Validate the API token. Returns True if valid (HTTP 204)."""
        await self._read_limiter.acquire()
        resp = await self._http.get("/api/v2/auth/")
        return resp.status_code == 204

    # -- Documents (v3) --

    async def save_document(self, request: SaveDocumentRequest) -> SaveDocumentResponse:
        """Save a document to Reader."""
        await self._write_limiter.acquire()
        resp = await self._http.post(
            "/api/v3/save/",
            json=request.model_dump(exclude_none=True),
        )
        resp.raise_for_status()
        return SaveDocumentResponse.model_validate(resp.json())

    async def list_documents(
        self, params: ListDocumentsParams | None = None
    ) -> DocumentListResponse:
        """List/filter documents from Reader."""
        await self._read_limiter.acquire()
        query_params: dict[str, Any] = {}
        if params:
            for key, value in params.model_dump(exclude_none=True).items():
                if isinstance(value, bool):
                    query_params[key] = str(value).lower()
                else:
                    query_params[key] = value
        resp = await self._http.get("/api/v3/list/", params=query_params)
        resp.raise_for_status()
        return DocumentListResponse.model_validate(resp.json())

    async def get_document(
        self, doc_id: str, include_content: bool = False
    ) -> Document | None:
        """Get a single document by ID."""
        params = ListDocumentsParams(id=doc_id)
        if include_content:
            params.withHtmlContent = True
        result = await self.list_documents(params)
        if result.results:
            return result.results[0]
        return None

    async def update_document(
        self, doc_id: str, request: UpdateDocumentRequest
    ) -> dict[str, Any]:
        """Update a document in Reader."""
        await self._write_limiter.acquire()
        resp = await self._http.patch(
            f"/api/v3/update/{doc_id}/",
            json=request.model_dump(exclude_none=True),
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from Reader. Returns True on success."""
        await self._write_limiter.acquire()
        resp = await self._http.delete(f"/api/v3/delete/{doc_id}/")
        return resp.status_code == 204

    # -- Tags (v3) --

    async def list_tags(self, page_cursor: str | None = None) -> TagListResponse:
        """List all tags."""
        await self._read_limiter.acquire()
        params: dict[str, str] = {}
        if page_cursor:
            params["pageCursor"] = page_cursor
        resp = await self._http.get("/api/v3/tags/", params=params)
        resp.raise_for_status()
        return TagListResponse.model_validate(resp.json())

    async def list_all_tags(self) -> list[dict[str, Any]]:
        """List all tags, handling pagination."""
        all_tags: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            result = await self.list_tags(page_cursor=cursor)
            all_tags.extend([t.model_dump() for t in result.results])
            cursor = result.nextPageCursor
            if not cursor:
                break
        return all_tags

    # -- Highlights (v2) --

    async def export_highlights(
        self,
        updated_after: str | None = None,
        page_cursor: str | None = None,
    ) -> HighlightExportResponse:
        """Export highlights (v2 API)."""
        await self._read_limiter.acquire()
        params: dict[str, str] = {}
        if updated_after:
            params["updatedAfter"] = updated_after
        if page_cursor:
            params["pageCursor"] = page_cursor
        resp = await self._http.get("/api/v2/export/", params=params)
        resp.raise_for_status()
        return HighlightExportResponse.model_validate(resp.json())

    # -- Pagination helpers --

    async def list_all_documents(
        self,
        updated_after: str | None = None,
        location: str | None = None,
        category: str | None = None,
    ) -> list[Document]:
        """Fetch all documents, auto-paginating."""
        all_docs: list[Document] = []
        cursor: str | None = None
        while True:
            params = ListDocumentsParams(
                updatedAfter=updated_after,
                location=location,
                category=category,
                pageCursor=cursor,
            )
            result = await self.list_documents(params)
            all_docs.extend(result.results)
            cursor = result.nextPageCursor
            if not cursor:
                break
            logger.debug("Fetched %d documents, continuing with cursor...", len(all_docs))
        return all_docs
