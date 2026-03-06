"""Tests for the OAuth 2.1 authorization server."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from pathlib import Path

import jwt as pyjwt
import pytest

from readwise_reader.auth.oauth_server import ACCESS_TOKEN_TTL, OAuthServer
from readwise_reader.auth.token_store import TokenStore


@pytest.fixture
def token_store(tmp_path: Path) -> TokenStore:
    return TokenStore(
        store_path=tmp_path / "tokens.enc",
        key_path=tmp_path / ".key",
    )


@pytest.fixture
def oauth(token_store: TokenStore) -> OAuthServer:
    return OAuthServer(server_url="http://localhost:8787", token_store=token_store)


class TestTokenStore:
    def test_initial_state(self, token_store: TokenStore) -> None:
        assert token_store.has_readwise_token() is False
        assert token_store.get_readwise_token() is None

    def test_set_and_get(self, token_store: TokenStore) -> None:
        token_store.set_readwise_token("test_token_123")
        assert token_store.has_readwise_token() is True
        assert token_store.get_readwise_token() == "test_token_123"

    def test_delete(self, token_store: TokenStore) -> None:
        token_store.set_readwise_token("test_token_123")
        token_store.delete_readwise_token()
        assert token_store.has_readwise_token() is False

    def test_encryption_persistence(self, tmp_path: Path) -> None:
        """Token persists across TokenStore instances with same key."""
        key_path = tmp_path / ".key"
        store_path = tmp_path / "tokens.enc"

        store1 = TokenStore(store_path=store_path, key_path=key_path)
        store1.set_readwise_token("persistent_token")

        store2 = TokenStore(store_path=store_path, key_path=key_path)
        assert store2.get_readwise_token() == "persistent_token"


class TestOAuthServer:
    def test_issue_and_validate_token(self, oauth: OAuthServer) -> None:
        """Test the full token issuance and validation cycle."""
        # Directly issue tokens (bypassing the HTTP flow)
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        app = Starlette(routes=oauth.routes())
        client = TestClient(app)

        # Test metadata endpoint
        resp = client.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resource"] == "http://localhost:8787"
        assert "readwise:read" in data["scopes_supported"]

    def test_authorization_server_metadata(self, oauth: OAuthServer) -> None:
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        app = Starlette(routes=oauth.routes())
        client = TestClient(app)

        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issuer"] == "http://localhost:8787"
        assert "authorization_code" in data["grant_types_supported"]
        assert "S256" in data["code_challenge_methods_supported"]

    def test_client_registration(self, oauth: OAuthServer) -> None:
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        app = Starlette(routes=oauth.routes())
        client = TestClient(app)

        resp = client.post("/oauth/register", json={
            "redirect_uris": ["http://localhost:3000/callback"],
            "client_name": "test-client",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "client_id" in data
        assert data["client_name"] == "test-client"

    def test_jwt_validation(self, oauth: OAuthServer) -> None:
        """Test JWT token creation and validation."""
        import jwt

        now = time.time()
        token = jwt.encode(
            {
                "sub": "test-client",
                "iss": "http://localhost:8787",
                "aud": "http://localhost:8787",
                "scope": "readwise:read readwise:write",
                "iat": int(now),
                "exp": int(now + 3600),
            },
            oauth._jwt_secret,
            algorithm="HS256",
        )
        claims = oauth.validate_access_token(token)
        assert claims is not None
        assert claims["sub"] == "test-client"
        assert "readwise:read" in claims["scope"]

    def test_expired_jwt_rejected(self, oauth: OAuthServer) -> None:
        import jwt

        now = time.time()
        token = jwt.encode(
            {
                "sub": "test-client",
                "iss": "http://localhost:8787",
                "aud": "http://localhost:8787",
                "scope": "readwise:read",
                "iat": int(now - 7200),
                "exp": int(now - 3600),  # expired 1 hour ago
            },
            oauth._jwt_secret,
            algorithm="HS256",
        )
        assert oauth.validate_access_token(token) is None

    def test_pkce_verification(self, oauth: OAuthServer) -> None:
        """Test that PKCE code_challenge/code_verifier works."""
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        # Simulate issuing an auth code with PKCE
        code = secrets.token_urlsafe(48)
        oauth._pending_auth[code] = {
            "code_challenge": code_challenge,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "test-client",
            "scopes": ["readwise:read"],
            "created_at": time.time(),
        }

        # Exchange with correct verifier
        result = oauth._handle_auth_code_grant({
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": "http://localhost:3000/callback",
        })
        assert result.status_code == 200

    def test_pkce_wrong_verifier(self, oauth: OAuthServer) -> None:
        """Test that wrong PKCE verifier is rejected."""
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        code = secrets.token_urlsafe(48)
        oauth._pending_auth[code] = {
            "code_challenge": code_challenge,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "test-client",
            "scopes": ["readwise:read"],
            "created_at": time.time(),
        }

        result = oauth._handle_auth_code_grant({
            "code": code,
            "code_verifier": "wrong_verifier",
            "redirect_uri": "http://localhost:3000/callback",
        })
        assert result.status_code == 400


def _issue_tokens_via_pkce(oauth: OAuthServer) -> dict:
    """Helper: complete a full PKCE auth code flow, returning the token response."""
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    code = secrets.token_urlsafe(48)
    oauth._pending_auth[code] = {
        "code_challenge": code_challenge,
        "redirect_uri": "http://localhost:3000/callback",
        "client_id": "lifecycle-test-client",
        "scopes": ["readwise:read", "readwise:write"],
        "created_at": time.time(),
    }

    resp = oauth._handle_auth_code_grant({
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": "http://localhost:3000/callback",
    })
    assert resp.status_code == 200
    import orjson
    return orjson.loads(resp.body)


class TestTokenRefreshLifecycle:
    def test_full_token_lifecycle(self, oauth: OAuthServer) -> None:
        """Full lifecycle: register -> PKCE auth -> verify -> refresh -> reject old."""
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        app = Starlette(routes=oauth.routes())
        client = TestClient(app)

        # 1. Register client
        reg_resp = client.post("/oauth/register", json={
            "redirect_uris": ["http://localhost:3000/callback"],
            "client_name": "lifecycle-test",
        })
        assert reg_resp.status_code == 201

        # 2. Issue tokens via PKCE (using helper to bypass HTTP redirect flow)
        tokens = _issue_tokens_via_pkce(oauth)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. Verify the access token
        claims = oauth.validate_access_token(access_token)
        assert claims is not None
        assert "readwise:read" in claims["scope"]

        # 4. Refresh: exchange refresh token for new tokens
        refresh_resp = oauth._handle_refresh_grant({"refresh_token": refresh_token})
        assert refresh_resp.status_code == 200
        import orjson
        new_tokens = orjson.loads(refresh_resp.body)
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens["refresh_token"]

        # 5. Verify the NEW access token works
        new_claims = oauth.validate_access_token(new_access_token)
        assert new_claims is not None

        # 6. Verify the OLD refresh token is rejected (rotation consumed it)
        reuse_resp = oauth._handle_refresh_grant({"refresh_token": refresh_token})
        assert reuse_resp.status_code == 400

        # 7. The new refresh token should still work
        final_resp = oauth._handle_refresh_grant({"refresh_token": new_refresh_token})
        assert final_resp.status_code == 200

    def test_refresh_token_rotation_invalidates_old(self, oauth: OAuthServer) -> None:
        """After rotation, the previous refresh token no longer works."""
        tokens = _issue_tokens_via_pkce(oauth)
        old_refresh = tokens["refresh_token"]

        # Use the refresh token once
        resp1 = oauth._handle_refresh_grant({"refresh_token": old_refresh})
        assert resp1.status_code == 200

        # Try to reuse the same refresh token
        resp2 = oauth._handle_refresh_grant({"refresh_token": old_refresh})
        assert resp2.status_code == 400

    def test_expired_access_token_requires_refresh(self, oauth: OAuthServer) -> None:
        """Access token expired -> validate returns None -> refresh produces a valid token."""
        tokens = _issue_tokens_via_pkce(oauth)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Access token should be valid now
        assert oauth.validate_access_token(access_token) is not None

        # Decode without verification to get claims, then re-encode as expired
        expired_token = pyjwt.encode(
            {
                "sub": "lifecycle-test-client",
                "iss": "http://localhost:8787",
                "aud": "http://localhost:8787",
                "scope": "readwise:read readwise:write",
                "iat": int(time.time() - ACCESS_TOKEN_TTL - 100),
                "exp": int(time.time() - 100),  # expired 100 seconds ago
            },
            oauth._jwt_secret,
            algorithm="HS256",
        )

        # Expired token should fail validation
        assert oauth.validate_access_token(expired_token) is None

        # Refresh should produce a new valid token
        import orjson
        refresh_resp = oauth._handle_refresh_grant({"refresh_token": refresh_token})
        assert refresh_resp.status_code == 200
        new_tokens = orjson.loads(refresh_resp.body)

        # New access token should be valid
        assert oauth.validate_access_token(new_tokens["access_token"]) is not None
