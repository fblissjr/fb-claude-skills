"""Enrichment pipeline interface (stub for future implementation).

Planned enrichments:
- PyLate multi-vector embeddings for semantic search across highlights
  The fact_highlights.embedding column is a FLOAT[] placeholder. PyLate produces
  variable-length multi-vector representations. When ready, consider a separate
  embeddings table or DuckDB array similarity functions.

- structure-it style structured extraction: Extract article content into
  Pydantic models (like WebArticle) and shred into atomic facts for
  granular retrieval. See ~/workspace/structure-it for patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class EnrichedDocument(BaseModel):
    """Result of enriching a document."""

    doc_id: str
    enrichment_type: str
    data: dict[str, Any]


class EnrichmentPipeline(ABC):
    """Base class for document enrichment pipelines."""

    @abstractmethod
    async def enrich(self, doc_id: str, content: str) -> EnrichedDocument:
        """Enrich a document with additional data.

        Args:
            doc_id: The document ID.
            content: The document content (HTML or text).

        Returns:
            EnrichedDocument with the enrichment results.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """The name of this enrichment pipeline."""
        ...


class EmbeddingPipeline(EnrichmentPipeline):
    """Stub: PyLate multi-vector embedding pipeline.

    When implemented, this will:
    1. Chunk document content into passages
    2. Generate multi-vector embeddings via PyLate
    3. Store embeddings in fact_highlights.embedding or a dedicated table
    4. Enable semantic similarity search across highlights
    """

    async def enrich(self, doc_id: str, content: str) -> EnrichedDocument:
        raise NotImplementedError("Embedding pipeline not yet implemented")

    def name(self) -> str:
        return "embeddings"


class StructuredExtractionPipeline(EnrichmentPipeline):
    """Stub: Structured extraction pipeline (structure-it pattern).

    When implemented, this will:
    1. Parse document HTML/content
    2. Extract structured data into Pydantic models
    3. Shred into atomic facts (fact_items pattern from structure-it)
    4. Store in DuckDB for granular querying
    """

    async def enrich(self, doc_id: str, content: str) -> EnrichedDocument:
        raise NotImplementedError("Structured extraction pipeline not yet implemented")

    def name(self) -> str:
        return "structured_extraction"
