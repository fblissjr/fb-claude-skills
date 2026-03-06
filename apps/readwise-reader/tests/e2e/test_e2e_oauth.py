"""E2E tests: OAuth metadata, registration, PKCE flow, token rejection."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time

import httpx
import pytest
from starlette.applications import Starlette

from readwise_reader.auth.oauth_server import OAuthServer

TEST_SERVER_URL = "http://testserver"


@pytest.fixture
def e2e_http_client(e2e_app: Starlette) -> httpx.AsyncClient:
    """Unauthenticated async HTTP client against the ASGI app."""
    transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
    return httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL)


class TestOAuthMetadata:
    async def test_protected_resource_metadata(
        self, e2e_http_client: httpx.AsyncClient
    ) -> None:
        async with e2e_http_client as client:
            resp = await client.get("/.well-known/oauth-protected-resource")
            assert resp.status_code == 200
            data = resp.json()
            assert data["resource"] == TEST_SERVER_URL
            assert "readwise:read" in data["scopes_supported"]

    async def test_authorization_server_metadata(
        self, e2e_http_client: httpx.AsyncClient
    ) -> None:
        async with e2e_http_client as client:
            resp = await client.get("/.well-known/oauth-authorization-server")
            assert resp.status_code == 200
            data = resp.json()
            assert data["issuer"] == TEST_SERVER_URL
            assert "authorization_code" in data["grant_types_supported"]
            assert "S256" in data["code_challenge_methods_supported"]
            assert data["registration_endpoint"] == f"{TEST_SERVER_URL}/oauth/register"


class TestDynamicClientRegistration:
    async def test_register_client(
        self, e2e_http_client: httpx.AsyncClient
    ) -> None:
        async with e2e_http_client as client:
            resp = await client.post("/oauth/register", json={
                "redirect_uris": ["http://localhost:3000/callback"],
                "client_name": "e2e-test-client",
            })
            assert resp.status_code == 201
            data = resp.json()
            assert "client_id" in data
            assert data["client_name"] == "e2e-test-client"


class TestPKCEFlow:
    async def test_authorize_issues_code_when_token_stored(
        self, e2e_http_client: httpx.AsyncClient, e2e_oauth: OAuthServer
    ) -> None:
        """When a Readwise token is already stored, /oauth/authorize redirects with a code."""
        # Register a client first
        async with e2e_http_client as client:
            reg = await client.post("/oauth/register", json={
                "redirect_uris": ["http://localhost:3000/callback"],
                "client_name": "pkce-test",
            })
            client_id = reg.json()["client_id"]

            code_verifier = secrets.token_urlsafe(48)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()

            resp = await client.get(
                "/oauth/authorize",
                params={
                    "client_id": client_id,
                    "redirect_uri": "http://localhost:3000/callback",
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                    "state": "test-state",
                    "scope": "readwise:read readwise:write",
                },
                follow_redirects=False,
            )
            # Should redirect with code (token is pre-seeded in e2e_token_store)
            assert resp.status_code == 302
            location = resp.headers["location"]
            assert "code=" in location
            assert "state=test-state" in location

    async def test_full_pkce_token_exchange(
        self, e2e_http_client: httpx.AsyncClient, e2e_oauth: OAuthServer
    ) -> None:
        """Full PKCE flow: register -> authorize -> exchange code -> get access token."""
        async with e2e_http_client as client:
            # 1. Register
            reg = await client.post("/oauth/register", json={
                "redirect_uris": ["http://localhost:3000/callback"],
                "client_name": "pkce-exchange-test",
            })
            client_id = reg.json()["client_id"]

            # 2. PKCE challenge
            code_verifier = secrets.token_urlsafe(48)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()

            # 3. Authorize (gets redirect with code)
            auth_resp = await client.get(
                "/oauth/authorize",
                params={
                    "client_id": client_id,
                    "redirect_uri": "http://localhost:3000/callback",
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                    "scope": "readwise:read",
                },
                follow_redirects=False,
            )
            location = auth_resp.headers["location"]
            # Extract code from redirect URL
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(location)
            code = parse_qs(parsed.query)["code"][0]

            # 4. Exchange code for tokens
            token_resp = await client.post("/oauth/token", data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": "http://localhost:3000/callback",
            })
            assert token_resp.status_code == 200
            tokens = token_resp.json()
            assert "access_token" in tokens
            assert "refresh_token" in tokens
            assert tokens["token_type"] == "Bearer"

            # 5. Validate the issued token
            claims = e2e_oauth.validate_access_token(tokens["access_token"])
            assert claims is not None
            assert "readwise:read" in claims["scope"]


class TestAuthRejection:
    async def test_mcp_request_without_auth_rejected(
        self, e2e_app: Starlette
    ) -> None:
        """MCP endpoint rejects requests without Authorization header."""
        transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL) as client:
            resp = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401

    async def test_mcp_request_with_invalid_token_rejected(
        self, e2e_app: Starlette
    ) -> None:
        """MCP endpoint rejects requests with a garbage bearer token."""
        transport = httpx.ASGITransport(app=e2e_app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url=TEST_SERVER_URL) as client:
            resp = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer totally-bogus-token",
                },
            )
            assert resp.status_code == 401

    async def test_mcp_request_with_expired_token_rejected(
        self, e2e_app: Starlette, e2e_oauth: OAuthServer
    ) -> None:
        """MCP endpoint rejects requests with an expired JWT."""
        import jwt

        expired_token = jwt.encode(
            {
                "sub": "expired-client",
                "iss": TEST_SERVER_URL,
                "aud": TEST_SERVER_URL,
                "scope": "readwise:read",
                "iat": int(time.time() - 7200),
                "exp": int(time.time() - 3600),
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
                    "Authorization": f"Bearer {expired_token}",
                },
            )
            assert resp.status_code == 401
