"""Readwise Reader MCP Server -- Streamable HTTP entry point."""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.auth.metadata import ReadwiseTokenVerifier
from readwise_reader.auth.oauth_server import OAuthServer
from readwise_reader.auth.token_store import TokenStore
from readwise_reader.storage.database import Database
from readwise_reader.storage.webhook_handler import WebhookHandler
from readwise_reader.tools.digest import register_digest_tools
from readwise_reader.tools.documents import register_document_tools
from readwise_reader.tools.search import register_search_tools
from readwise_reader.tools.tags import register_tag_tools
from readwise_reader.tools.triage import register_triage_tools

logger = logging.getLogger(__name__)

HOST = os.environ.get("READWISE_HOST", "127.0.0.1")
PORT = int(os.environ.get("READWISE_PORT", "8787"))
USE_TLS = os.environ.get("READWISE_NO_TLS", "").lower() not in ("1", "true", "yes")
PROTOCOL = "https" if USE_TLS else "http"
SERVER_URL = f"{PROTOCOL}://{HOST}:{PORT}"

# TLS cert paths (mkcert): check project certs/ first, then ~/.readwise-reader/certs/
_PROJECT_CERTS = Path(__file__).resolve().parent.parent.parent / "certs"
_HOME_CERTS = Path.home() / ".readwise-reader" / "certs"


def _find_certs() -> tuple[Path, Path]:
    """Locate TLS cert and key files. Raises FileNotFoundError if missing."""
    for certs_dir in (_PROJECT_CERTS, _HOME_CERTS):
        cert = next(certs_dir.glob("*+*.pem"), None) if certs_dir.exists() else None
        key = next(certs_dir.glob("*+*-key.pem"), None) if certs_dir.exists() else None
        if cert and key:
            return cert, key
    msg = (
        f"TLS certs not found. Generate them with:\n"
        f"  mkdir -p certs && cd certs && mkcert localhost 127.0.0.1 ::1\n"
        f"Searched: {_PROJECT_CERTS}, {_HOME_CERTS}"
    )
    raise FileNotFoundError(msg)


@dataclass
class AppContext:
    """Shared application context available to all MCP tools."""

    client: ReadwiseClient
    db: Database
    token_store: TokenStore


# -- OAuth setup --

token_store = TokenStore()
oauth = OAuthServer(server_url=SERVER_URL, token_store=token_store)
token_verifier = ReadwiseTokenVerifier(oauth)


# -- Lifespan --

@contextlib.asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize shared resources for the MCP server."""
    db = Database()
    readwise_token = os.environ.get("READWISE_API_TOKEN") or token_store.get_readwise_token()

    if readwise_token:
        client = ReadwiseClient(token=readwise_token)
        logger.info("Readwise client initialized with stored token")
    else:
        # Create a placeholder client -- will fail until OAuth completes
        client = ReadwiseClient(token="NOT_CONFIGURED")
        logger.warning("No Readwise token stored. Complete OAuth to configure.")

    try:
        yield AppContext(client=client, db=db, token_store=token_store)
    finally:
        await client.close()
        db.close()
        logger.info("Server shutdown: resources cleaned up")


# -- MCP Server --

mcp = FastMCP(
    name="Readwise Reader",
    instructions=(
        "Readwise Reader MCP server. Search, save, and manage your reading library. "
        "Use sync_library to pull latest data, then search_library or list_documents "
        "to query your library. Use save_document to add URLs."
    ),
    host=HOST,
    port=PORT,
    lifespan=app_lifespan,
    token_verifier=token_verifier,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(SERVER_URL),
        required_scopes=["readwise:read"],
        resource_server_url=AnyHttpUrl(SERVER_URL),
    ),
)

# Register all tools
register_document_tools(mcp)
register_search_tools(mcp)
register_tag_tools(mcp)
register_triage_tools(mcp)
register_digest_tools(mcp)


# -- Composite ASGI App (MCP + OAuth + Webhooks) --

webhook_handler: WebhookHandler | None = None


def create_app() -> Starlette:
    """Create the full ASGI application with MCP, OAuth, and webhook routes."""
    global webhook_handler

    # The MCP app handles /mcp
    mcp_app = mcp.streamable_http_app()

    # Webhook handler (initialized lazily when DB is available)
    async def webhook_route(request):  # type: ignore[no-untyped-def]
        global webhook_handler
        if webhook_handler is None:
            # Initialize with a fresh DB connection for webhooks
            db = Database()
            webhook_handler = WebhookHandler(db=db)
        return await webhook_handler.handle_webhook(request)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):  # type: ignore[no-untyped-def]
        async with mcp.session_manager.run():
            yield

    routes = [
        # OAuth routes
        *oauth.routes(),
        # Webhook endpoint
        Route("/webhook", webhook_route, methods=["POST"]),
        # MCP endpoint (mounted as sub-application)
        Mount("/", mcp_app),
    ]

    app = Starlette(routes=routes, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )

    return app


def main() -> None:
    """Entry point: start the Readwise Reader MCP server."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    uvicorn_kwargs: dict[str, object] = {"host": HOST, "port": PORT, "log_level": "info"}
    if USE_TLS:
        cert_file, key_file = _find_certs()
        uvicorn_kwargs["ssl_certfile"] = str(cert_file)
        uvicorn_kwargs["ssl_keyfile"] = str(key_file)
        logger.info("TLS certs: %s, %s", cert_file, key_file)

    logger.info("Starting Readwise Reader MCP server on %s", SERVER_URL)

    app = create_app()
    uvicorn.run(app, **uvicorn_kwargs)


if __name__ == "__main__":
    main()
