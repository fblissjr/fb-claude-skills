"""OAuth 2.1 Authorization Server for Readwise Reader MCP.

Implements the MCP authorization spec: the server acts as both the
Authorization Server (issuing tokens) and the Resource Server (validating them).
The user's Readwise API token is collected once during authorization and stored
locally. MCP clients receive short-lived JWTs -- they never see the Readwise token.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import jwt
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from readwise_reader.auth.token_store import TokenStore

logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET_LENGTH = 64
ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 86400 * 30  # 30 days


class OAuthServer:
    """OAuth 2.1 Authorization Server for MCP.

    Handles the full OAuth flow:
    1. Client registers (or uses metadata document)
    2. Client starts authorization with PKCE
    3. User enters Readwise API token in a local HTML form
    4. Server issues authorization code
    5. Client exchanges code for access token
    6. Server validates access tokens on MCP requests
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8787",
        token_store: TokenStore | None = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.token_store = token_store or TokenStore()
        self._jwt_secret = secrets.token_hex(JWT_SECRET_LENGTH)
        # Pending authorization requests: code -> {code_challenge, redirect_uri, client_id, scopes}
        self._pending_auth: dict[str, dict[str, Any]] = {}
        # Issued refresh tokens: token_hash -> {client_id, scopes, readwise_token_ref}
        self._refresh_tokens: dict[str, dict[str, Any]] = {}
        # Registered clients: client_id -> {redirect_uris, ...}
        self._clients: dict[str, dict[str, Any]] = {}

    # -- Metadata endpoints --

    async def protected_resource_metadata(self, request: Request) -> Response:
        """RFC 9728: Protected Resource Metadata."""
        return JSONResponse({
            "resource": self.server_url,
            "authorization_servers": [self.server_url],
            "scopes_supported": ["readwise:read", "readwise:write"],
            "bearer_methods_supported": ["header"],
        })

    async def authorization_server_metadata(self, request: Request) -> Response:
        """RFC 8414: Authorization Server Metadata."""
        return JSONResponse({
            "issuer": self.server_url,
            "authorization_endpoint": f"{self.server_url}/oauth/authorize",
            "token_endpoint": f"{self.server_url}/oauth/token",
            "registration_endpoint": f"{self.server_url}/oauth/register",
            "scopes_supported": ["readwise:read", "readwise:write"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "service_documentation": f"{self.server_url}/docs",
        })

    # -- Dynamic Client Registration --

    async def register_client(self, request: Request) -> Response:
        """RFC 7591: Dynamic Client Registration."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid_request"}, status_code=400)

        client_id = secrets.token_urlsafe(32)
        redirect_uris = body.get("redirect_uris", [])
        client_name = body.get("client_name", "unknown")

        self._clients[client_id] = {
            "redirect_uris": redirect_uris,
            "client_name": client_name,
            "grant_types": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_method": "none",
        }

        return JSONResponse({
            "client_id": client_id,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_method": "none",
        }, status_code=201)

    # -- Authorization endpoint --

    async def authorize(self, request: Request) -> Response:
        """Handle authorization requests."""
        params = dict(request.query_params)
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        code_challenge = params.get("code_challenge", "")
        code_challenge_method = params.get("code_challenge_method", "")
        state = params.get("state", "")
        scope = params.get("scope", "readwise:read readwise:write")

        if code_challenge_method and code_challenge_method != "S256":
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Only S256 is supported"},
                status_code=400,
            )

        # If the user already has a stored Readwise token, skip the form
        if self.token_store.has_readwise_token():
            return self._issue_auth_code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_challenge=code_challenge,
                state=state,
                scope=scope,
            )

        # Show the token entry form
        return HTMLResponse(self._auth_form_html(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
            scope=scope,
        ))

    async def authorize_submit(self, request: Request) -> Response:
        """Handle the token submission form."""
        form = await request.form()
        readwise_token = str(form.get("readwise_token", "")).strip()
        client_id = str(form.get("client_id", ""))
        redirect_uri = str(form.get("redirect_uri", ""))
        code_challenge = str(form.get("code_challenge", ""))
        state = str(form.get("state", ""))
        scope = str(form.get("scope", "readwise:read readwise:write"))

        if not readwise_token:
            return HTMLResponse(
                self._auth_form_html(
                    client_id=client_id,
                    redirect_uri=redirect_uri,
                    code_challenge=code_challenge,
                    state=state,
                    scope=scope,
                    error="Please enter your Readwise API token.",
                ),
                status_code=400,
            )

        # Validate the token against Readwise API
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                "https://readwise.io/api/v2/auth/",
                headers={"Authorization": f"Token {readwise_token}"},
                timeout=10.0,
            )
            if resp.status_code != 204:
                return HTMLResponse(
                    self._auth_form_html(
                        client_id=client_id,
                        redirect_uri=redirect_uri,
                        code_challenge=code_challenge,
                        state=state,
                        scope=scope,
                        error="Invalid Readwise API token. Please check and try again.",
                    ),
                    status_code=400,
                )

        # Store the validated token
        self.token_store.set_readwise_token(readwise_token)

        return self._issue_auth_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
            scope=scope,
        )

    def _issue_auth_code(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        scope: str,
    ) -> Response:
        """Generate an authorization code and redirect."""
        code = secrets.token_urlsafe(48)
        self._pending_auth[code] = {
            "code_challenge": code_challenge,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "scopes": scope.split(),
            "created_at": time.time(),
        }

        params: dict[str, str] = {"code": code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(redirect_url, status_code=302)

    # -- Token endpoint --

    async def token(self, request: Request) -> Response:
        """Exchange authorization code or refresh token for access token."""
        try:
            body = await request.form()
        except Exception:
            body = {}

        grant_type = str(body.get("grant_type", ""))

        if grant_type == "authorization_code":
            return self._handle_auth_code_grant(dict(body))
        elif grant_type == "refresh_token":
            return self._handle_refresh_grant(dict(body))
        else:
            return JSONResponse(
                {"error": "unsupported_grant_type"},
                status_code=400,
            )

    def _handle_auth_code_grant(self, body: dict[str, Any]) -> Response:
        """Handle authorization_code grant."""
        code = str(body.get("code", ""))
        code_verifier = str(body.get("code_verifier", ""))
        redirect_uri = str(body.get("redirect_uri", ""))

        pending = self._pending_auth.pop(code, None)
        if not pending:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)

        # Check code expiry (10 minutes)
        if time.time() - pending["created_at"] > 600:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Code expired"},
                status_code=400,
            )

        # Verify PKCE
        if pending["code_challenge"]:
            expected = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()
            if expected != pending["code_challenge"]:
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                    status_code=400,
                )

        # Verify redirect_uri
        if redirect_uri and redirect_uri != pending["redirect_uri"]:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)

        return self._issue_tokens(pending["client_id"], pending["scopes"])

    def _handle_refresh_grant(self, body: dict[str, Any]) -> Response:
        """Handle refresh_token grant."""
        refresh_token = str(body.get("refresh_token", ""))
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored = self._refresh_tokens.pop(token_hash, None)

        if not stored:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)

        return self._issue_tokens(stored["client_id"], stored["scopes"])

    def _issue_tokens(self, client_id: str, scopes: list[str]) -> Response:
        """Issue access token and refresh token."""
        now = time.time()

        access_token = jwt.encode(
            {
                "sub": client_id,
                "iss": self.server_url,
                "aud": self.server_url,
                "scope": " ".join(scopes),
                "iat": int(now),
                "exp": int(now + ACCESS_TOKEN_TTL),
            },
            self._jwt_secret,
            algorithm="HS256",
        )

        refresh_token = secrets.token_urlsafe(48)
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        self._refresh_tokens[refresh_hash] = {
            "client_id": client_id,
            "scopes": scopes,
        }

        return JSONResponse({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL,
            "refresh_token": refresh_token,
            "scope": " ".join(scopes),
        })

    # -- Token validation (for MCP requests) --

    def validate_access_token(self, token: str) -> dict[str, Any] | None:
        """Validate a JWT access token. Returns claims or None."""
        try:
            claims = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
                audience=self.server_url,
            )
            return claims
        except jwt.ExpiredSignatureError:
            logger.debug("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug("Invalid access token: %s", e)
            return None

    # -- HTML form --

    def _auth_form_html(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        scope: str,
        error: str = "",
    ) -> str:
        """Generate the Readwise token entry HTML form."""
        error_html = f'<p style="color: #dc3545; margin-bottom: 16px;">{error}</p>' if error else ""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Readwise Reader - MCP Authorization</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            max-width: 480px;
            margin: 80px auto;
            padding: 0 20px;
            background: #f8f9fa;
            color: #212529;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 1.5rem;
            margin: 0 0 8px 0;
        }}
        .subtitle {{
            color: #6c757d;
            margin: 0 0 24px 0;
        }}
        label {{
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        input[type="text"] {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        input[type="text"]:focus {{
            outline: none;
            border-color: #0d6efd;
            box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.15);
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: #0d6efd;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 16px;
        }}
        button:hover {{
            background: #0b5ed7;
        }}
        .help {{
            font-size: 13px;
            color: #6c757d;
            margin-top: 8px;
        }}
        a {{ color: #0d6efd; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Readwise Reader</h1>
        <p class="subtitle">Connect your Readwise account to Claude</p>
        {error_html}
        <form method="POST" action="/oauth/authorize/submit">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="scope" value="{scope}">
            <label for="readwise_token">Readwise API Token</label>
            <input type="text" id="readwise_token" name="readwise_token"
                   placeholder="Enter your Readwise access token"
                   autocomplete="off" required>
            <p class="help">
                Get your token at <a href="https://readwise.io/access_token"
                target="_blank">readwise.io/access_token</a>
            </p>
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>"""

    # -- Starlette routes --

    def routes(self) -> list[Route]:
        """Return Starlette routes for the OAuth server."""
        return [
            Route("/.well-known/oauth-protected-resource", self.protected_resource_metadata),
            Route("/.well-known/oauth-authorization-server", self.authorization_server_metadata),
            Route("/oauth/register", self.register_client, methods=["POST"]),
            Route("/oauth/authorize", self.authorize),
            Route("/oauth/authorize/submit", self.authorize_submit, methods=["POST"]),
            Route("/oauth/token", self.token, methods=["POST"]),
        ]
