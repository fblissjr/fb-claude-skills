"""E2E tests: MCP connection handshake, capabilities, session lifecycle."""

from __future__ import annotations

from mcp.client.session import ClientSession


class TestMCPConnection:
    async def test_server_accepts_initialize(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        """Server responds to initialize with correct server info."""
        # initialize() already called in fixture; verify via list_tools round-trip
        result = await e2e_mcp_session.list_tools()
        assert result.tools is not None

    async def test_server_reports_tool_capabilities(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        """Server advertises tools via get_server_capabilities."""
        caps = e2e_mcp_session.get_server_capabilities()
        assert caps is not None
        assert caps.tools is not None

    async def test_ping(self, e2e_mcp_session: ClientSession) -> None:
        """Server responds to ping."""
        await e2e_mcp_session.send_ping()

    async def test_list_tools_returns_nonempty(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        """Server lists registered tools."""
        result = await e2e_mcp_session.list_tools()
        assert len(result.tools) > 0
        tool_names = {t.name for t in result.tools}
        assert "library_stats" in tool_names
        assert "search_library" in tool_names
