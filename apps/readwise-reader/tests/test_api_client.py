"""Tests for the Readwise API client."""

from __future__ import annotations

import httpx
import pytest
import respx

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.api.models import ListDocumentsParams, SaveDocumentRequest


@pytest.fixture
def client() -> ReadwiseClient:
    return ReadwiseClient(token="test_token", base_url="https://readwise.io")


@respx.mock
@pytest.mark.asyncio
async def test_validate_token_valid(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v2/auth/").mock(
        return_value=httpx.Response(204)
    )
    assert await client.validate_token() is True


@respx.mock
@pytest.mark.asyncio
async def test_validate_token_invalid(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v2/auth/").mock(
        return_value=httpx.Response(401)
    )
    assert await client.validate_token() is False


@respx.mock
@pytest.mark.asyncio
async def test_save_document(client: ReadwiseClient) -> None:
    respx.post("https://readwise.io/api/v3/save/").mock(
        return_value=httpx.Response(201, json={"id": "doc123", "url": "https://example.com"})
    )
    request = SaveDocumentRequest(url="https://example.com", title="Test")
    result = await client.save_document(request)
    assert result.id == "doc123"
    assert result.url == "https://example.com"


@respx.mock
@pytest.mark.asyncio
async def test_list_documents(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v3/list/").mock(
        return_value=httpx.Response(200, json={
            "count": 2,
            "nextPageCursor": None,
            "results": [
                {"id": "d1", "title": "Article 1", "category": "article"},
                {"id": "d2", "title": "Article 2", "category": "pdf"},
            ],
        })
    )
    result = await client.list_documents()
    assert result.count == 2
    assert len(result.results) == 2
    assert result.results[0].id == "d1"


@respx.mock
@pytest.mark.asyncio
async def test_list_documents_with_filters(client: ReadwiseClient) -> None:
    route = respx.get("https://readwise.io/api/v3/list/").mock(
        return_value=httpx.Response(200, json={
            "count": 1,
            "nextPageCursor": None,
            "results": [{"id": "d1", "title": "Article 1", "category": "article"}],
        })
    )
    params = ListDocumentsParams(category="article", location="new", limit=10)
    result = await client.list_documents(params)
    assert result.count == 1
    # Verify the query params were sent
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_get_document(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v3/list/").mock(
        return_value=httpx.Response(200, json={
            "count": 1,
            "nextPageCursor": None,
            "results": [{"id": "doc123", "title": "Test Article"}],
        })
    )
    doc = await client.get_document("doc123")
    assert doc is not None
    assert doc.id == "doc123"


@respx.mock
@pytest.mark.asyncio
async def test_get_document_not_found(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v3/list/").mock(
        return_value=httpx.Response(200, json={
            "count": 0,
            "nextPageCursor": None,
            "results": [],
        })
    )
    doc = await client.get_document("nonexistent")
    assert doc is None


@respx.mock
@pytest.mark.asyncio
async def test_delete_document(client: ReadwiseClient) -> None:
    respx.delete("https://readwise.io/api/v3/delete/doc123/").mock(
        return_value=httpx.Response(204)
    )
    assert await client.delete_document("doc123") is True


@respx.mock
@pytest.mark.asyncio
async def test_list_tags(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v3/tags/").mock(
        return_value=httpx.Response(200, json={
            "count": 2,
            "nextPageCursor": None,
            "results": [
                {"key": "python", "name": "Python"},
                {"key": "ml", "name": "Machine Learning"},
            ],
        })
    )
    result = await client.list_tags()
    assert result.count == 2
    assert result.results[0].name == "Python"


@respx.mock
@pytest.mark.asyncio
async def test_export_highlights(client: ReadwiseClient) -> None:
    respx.get("https://readwise.io/api/v2/export/").mock(
        return_value=httpx.Response(200, json={
            "count": 1,
            "nextPageCursor": None,
            "results": [{
                "user_book_id": 1,
                "title": "Test Book",
                "highlights": [
                    {"id": 101, "text": "Highlighted text", "note": "My note"},
                ],
            }],
        })
    )
    result = await client.export_highlights()
    assert result.count == 1
    assert len(result.results[0].highlights) == 1
    assert result.results[0].highlights[0].text == "Highlighted text"
