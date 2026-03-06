"""E2E tests: MCP tool listing and invocation through the full protocol stack."""

from __future__ import annotations

import orjson
from mcp.client.session import ClientSession
from mcp.types import CallToolResult

# Expected tools across all 5 modules
EXPECTED_TOOLS = {
    # documents.py
    "save_document", "list_documents", "get_document", "update_document", "delete_document",
    # search.py
    "search_library", "search_highlights",
    # tags.py
    "list_tags", "get_documents_by_tag",
    # triage.py
    "get_inbox", "triage_document", "batch_triage",
    # digest.py
    "library_stats", "reading_digest", "sync_library", "get_highlights",
}


def _parse_single(result: CallToolResult) -> dict:
    """Parse a tool result that returns a single dict."""
    return orjson.loads(result.content[0].text)


def _parse_list(result: CallToolResult) -> list[dict]:
    """Parse a tool result that returns a list (one TextContent block per element)."""
    return [orjson.loads(c.text) for c in result.content]


class TestToolListing:
    async def test_lists_all_expected_tools(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        result = await e2e_mcp_session.list_tools()
        tool_names = {t.name for t in result.tools}
        missing = EXPECTED_TOOLS - tool_names
        assert not missing, f"Missing tools: {missing}"

    async def test_tools_have_descriptions(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        result = await e2e_mcp_session.list_tools()
        for tool in result.tools:
            if tool.name in EXPECTED_TOOLS:
                assert tool.description, f"Tool {tool.name} has no description"


class TestReadOnlyTools:
    """Test tools that only query the seeded DB (no external API calls)."""

    async def test_library_stats(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("library_stats", {})
        stats = _parse_single(result)
        assert stats["total_documents"] == 5
        assert stats["total_highlights"] == 2
        assert stats["total_tags"] == 4
        assert stats["inbox_size"] == 2  # doc-3 and doc-4

    async def test_list_documents(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("list_documents", {"limit": 10})
        docs = _parse_list(result)
        assert len(docs) == 5

    async def test_list_documents_with_category_filter(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        result = await e2e_mcp_session.call_tool(
            "list_documents", {"category": "article", "limit": 10}
        )
        docs = _parse_list(result)
        assert len(docs) == 3  # doc-1, doc-2, doc-5

    async def test_list_documents_with_location_filter(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        result = await e2e_mcp_session.call_tool(
            "list_documents", {"location": "new", "limit": 10}
        )
        docs = _parse_list(result)
        assert len(docs) == 2  # doc-3, doc-4

    async def test_get_document(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("get_document", {"doc_id": "doc-1"})
        doc = _parse_single(result)
        assert doc["doc_id"] == "doc-1"
        assert doc["title"] == "Introduction to Rust"

    async def test_search_library(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("search_library", {"query": "rust"})
        docs = _parse_list(result)
        assert len(docs) >= 1
        assert any(d["doc_id"] == "doc-1" for d in docs)

    async def test_search_highlights(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool(
            "search_highlights", {"query": "ownership"}
        )
        highlights = _parse_list(result)
        assert len(highlights) >= 1
        assert any(h["highlight_id"] == "hl-1" for h in highlights)

    async def test_list_tags(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("list_tags", {})
        tags = _parse_list(result)
        tag_names = {t["tag_name"] for t in tags}
        assert "rust" in tag_names
        assert "python" in tag_names
        assert "programming" in tag_names

    async def test_get_documents_by_tag(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool(
            "get_documents_by_tag", {"tag": "programming"}
        )
        docs = _parse_list(result)
        # doc-1 (rust, programming), doc-2 (python, programming), doc-5 (programming, interviews)
        assert len(docs) == 3

    async def test_get_inbox(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("get_inbox", {})
        docs = _parse_list(result)
        assert len(docs) == 2
        assert all(d["location"] == "new" for d in docs)

    async def test_get_highlights(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("get_highlights", {})
        highlights = _parse_list(result)
        assert len(highlights) == 2

    async def test_get_highlights_by_doc(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool(
            "get_highlights", {"doc_id": "doc-1"}
        )
        highlights = _parse_list(result)
        assert len(highlights) == 1
        assert highlights[0]["highlight_id"] == "hl-1"

    async def test_reading_digest(self, e2e_mcp_session: ClientSession) -> None:
        result = await e2e_mcp_session.call_tool("reading_digest", {})
        digest = _parse_single(result)
        assert "total_documents" in digest
        assert "by_location" in digest
        assert "by_category" in digest
