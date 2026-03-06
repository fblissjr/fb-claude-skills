"""Pydantic models for Readwise Reader API data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# -- Request models --


class SaveDocumentRequest(BaseModel):
    """Request body for POST /api/v3/save/."""

    url: str
    html: str | None = None
    should_clean_html: bool | None = None
    title: str | None = None
    author: str | None = None
    summary: str | None = None
    published_date: str | None = None
    image_url: str | None = None
    location: str | None = None  # new, later, archive, feed
    category: str | None = None  # article, email, rss, highlight, note, pdf, epub, tweet, video
    saved_using: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class UpdateDocumentRequest(BaseModel):
    """Request body for PATCH /api/v3/update/<id>/."""

    title: str | None = None
    author: str | None = None
    summary: str | None = None
    published_date: str | None = None
    image_url: str | None = None
    seen: bool | None = None
    location: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ListDocumentsParams(BaseModel):
    """Query parameters for GET /api/v3/list/."""

    id: str | None = None
    updatedAfter: str | None = None
    location: str | None = None
    category: str | None = None
    tag: str | None = None
    limit: int | None = None  # 1-100, default 100
    pageCursor: str | None = None
    withHtmlContent: bool | None = None
    withRawSourceUrl: bool | None = None


# -- Response models --


class Document(BaseModel):
    """A Readwise Reader document."""

    id: str
    url: str | None = None
    title: str | None = None
    author: str | None = None
    category: str | None = None
    location: str | None = None
    summary: str | None = None
    word_count: int | None = None
    reading_progress: float | None = None
    image_url: str | None = None
    published_date: datetime | None = None
    site_name: str | None = None
    source_url: str | None = None
    notes: str | None = None
    tags: dict[str, Any] | None = None  # {"tag_name": {...}}
    html_content: str | None = None  # only with withHtmlContent=true
    created_at: datetime | None = None
    updated_at: datetime | None = None
    first_opened_at: datetime | None = None
    last_opened_at: datetime | None = None
    saved_at: datetime | None = None
    last_moved_at: datetime | None = None
    parent_id: str | None = None

    model_config = {"extra": "allow"}


class DocumentListResponse(BaseModel):
    """Response from GET /api/v3/list/."""

    count: int
    nextPageCursor: str | None = None
    results: list[Document]


class SaveDocumentResponse(BaseModel):
    """Response from POST /api/v3/save/."""

    id: str
    url: str

    model_config = {"extra": "allow"}


class Tag(BaseModel):
    """A Readwise Reader tag."""

    key: str = Field(alias="key")
    name: str = Field(alias="name")

    model_config = {"populate_by_name": True, "extra": "allow"}


class TagListResponse(BaseModel):
    """Response from GET /api/v3/tags/."""

    count: int
    nextPageCursor: str | None = None
    results: list[Tag]


# -- Highlight models (v2 API) --


class Highlight(BaseModel):
    """A Readwise highlight."""

    id: int
    text: str
    note: str | None = None
    location: int | None = None
    location_type: str | None = None
    highlighted_at: datetime | None = None
    url: str | None = None
    color: str | None = None
    updated: datetime | None = None
    book_id: int | None = None
    tags: list[dict[str, Any]] | None = None
    is_favorite: bool | None = None
    is_discard: bool | None = None
    external_id: str | None = None

    model_config = {"extra": "allow"}


class BookWithHighlights(BaseModel):
    """A book/source with its highlights from the export endpoint."""

    user_book_id: int
    title: str | None = None
    author: str | None = None
    readable_title: str | None = None
    source: str | None = None
    cover_image_url: str | None = None
    unique_url: str | None = None
    category: str | None = None
    document_note: str | None = None
    readwise_url: str | None = None
    source_url: str | None = None
    asin: str | None = None
    tags: list[dict[str, Any]] | None = None
    num_highlights: int | None = None
    highlights: list[Highlight] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class HighlightExportResponse(BaseModel):
    """Response from GET /api/v2/export/."""

    count: int
    nextPageCursor: str | None = None
    results: list[BookWithHighlights]


# -- Webhook models --


class WebhookDocumentPayload(BaseModel):
    """Payload from a Readwise Reader document webhook event."""

    id: str
    url: str | None = None
    title: str | None = None
    author: str | None = None
    category: str | None = None
    location: str | None = None
    tags: dict[str, Any] | None = None
    site_name: str | None = None
    word_count: int | None = None
    reading_time: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    published_date: str | None = None
    summary: str | None = None
    content: str | None = None
    source_url: str | None = None
    notes: str | None = None
    reading_progress: float | None = None
    first_opened_at: str | None = None
    last_opened_at: str | None = None
    saved_at: str | None = None
    last_moved_at: str | None = None
    event_type: str | None = None
    secret: str | None = None

    model_config = {"extra": "allow"}


class WebhookHighlightPayload(BaseModel):
    """Payload from a Readwise highlight webhook event."""

    id: int
    text: str | None = None
    note: str | None = None
    location: int | None = None
    location_type: str | None = None
    highlighted_at: str | None = None
    url: str | None = None
    color: str | None = None
    updated: str | None = None
    book_id: int | None = None
    tags: list[dict[str, Any]] | None = None
    event_type: str | None = None
    secret: str | None = None

    model_config = {"extra": "allow"}
