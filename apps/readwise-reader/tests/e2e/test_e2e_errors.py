"""E2E tests: auth failures, invalid tools, malformed requests."""

from __future__ import annotations

import time

import httpx
from mcp.client.session import ClientSession
from mcp.shared.exceptions import McpError
from starlette.applications import Starlette

from readwise_reader.auth.oauth_server import OAuthServer

TEST_SERVER_URL = "http://testserver"


class TestAuthErrors:
    async def test_no_auth_header(self, e2e_app: Starlette) -> None:
        transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL) as client:
            resp = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401

    async def test_invalid_bearer_token(self, e2e_app: Starlette) -> None:
        transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL) as client:
            resp = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer not-a-valid-jwt",
                },
            )
            assert resp.status_code == 401

    async def test_expired_jwt(
        self, e2e_app: Starlette, e2e_oauth: OAuthServer
    ) -> None:
        import jwt

        expired = jwt.encode(
            {
                "sub": "test", "iss": TEST_SERVER_URL, "aud": TEST_SERVER_URL,
                "scope": "readwise:read",
                "iat": int(time.time() - 7200), "exp": int(time.time() - 3600),
            },
            e2e_oauth._jwt_secret,
            algorithm="HS256",
        )
        transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL) as client:
            resp = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {expired}",
                },
            )
            assert resp.status_code == 401


class TestMCPErrors:
    async def test_call_nonexistent_tool(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        """Calling a nonexistent tool raises McpError or returns isError."""
        try:
            result = await e2e_mcp_session.call_tool("this_tool_does_not_exist", {})
            # If it returns instead of raising, check isError flag
            assert result.isError, "Expected error for nonexistent tool"
        except McpError:
            pass  # Also acceptable

    async def test_missing_required_argument(
        self, e2e_mcp_session: ClientSession
    ) -> None:
        """search_library requires 'query' -- calling without it should error."""
        try:
            result = await e2e_mcp_session.call_tool("search_library", {})
            assert result.isError, "Expected error for missing required argument"
        except McpError:
            pass  # Also acceptable
