"""MCP Authorization integration -- TokenVerifier for FastMCP."""

from __future__ import annotations

import logging

from mcp.server.auth.provider import AccessToken, TokenVerifier

from readwise_reader.auth.oauth_server import OAuthServer

logger = logging.getLogger(__name__)


class ReadwiseTokenVerifier(TokenVerifier):
    """Validates JWT access tokens issued by our OAuth server.

    Plugs into FastMCP's auth system so that every MCP request
    is authenticated before tools are invoked.
    """

    def __init__(self, oauth: OAuthServer) -> None:
        self.oauth = oauth

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token from an MCP request."""
        claims = self.oauth.validate_access_token(token)
        if not claims:
            return None

        return AccessToken(
            token=token,
            client_id=claims.get("sub", "unknown"),
            scopes=claims.get("scope", "").split(),
            expires_at=claims.get("exp"),
        )
