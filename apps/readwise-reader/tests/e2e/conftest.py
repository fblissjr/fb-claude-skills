"""E2E test fixtures: in-process ASGI app with MCP client session."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path

import httpx
import orjson
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route

from readwise_reader.api.client import ReadwiseClient
from readwise_reader.auth.metadata import ReadwiseTokenVerifier
from readwise_reader.auth.oauth_server import OAuthServer
from readwise_reader.auth.token_store import TokenStore
from readwise_reader.server import AppContext
from readwise_reader.storage.database import Database
from readwise_reader.tools.digest import register_digest_tools
from readwise_reader.tools.documents import register_document_tools
from readwise_reader.tools.search import register_search_tools
from readwise_reader.tools.tags import register_tag_tools
from readwise_reader.tools.triage import register_triage_tools

TEST_SERVER_URL = "http://testserver"


# -- Component fixtures --


@pytest.fixture
def e2e_token_store(tmp_path: Path) -> TokenStore:
    """TokenStore in a temp directory, pre-seeded with a fake Readwise token."""
    store = TokenStore(
        store_path=tmp_path / "tokens.enc",
        key_path=tmp_path / ".key",
    )
    store.set_readwise_token("test-readwise-token-e2e")
    return store


@pytest.fixture
def e2e_oauth(e2e_token_store: TokenStore) -> OAuthServer:
    return OAuthServer(server_url=TEST_SERVER_URL, token_store=e2e_token_store)


@pytest.fixture
def e2e_db(tmp_path: Path) -> Database:
    """Seeded DuckDB instance with sample documents, highlights, and tags."""
    db = Database(db_path=tmp_path / "e2e.duckdb")

    # 5 documents across categories and locations
    docs = [
        {
            "id": "doc-1", "title": "Introduction to Rust",
            "author": "Steve Klabnik", "category": "article", "location": "later",
            "summary": "A comprehensive guide to the Rust programming language",
            "url": "https://example.com/rust", "word_count": 5000,
            "tags": {"rust": {}, "programming": {}},
        },
        {
            "id": "doc-2", "title": "Python Best Practices",
            "author": "Guido van Rossum", "category": "article", "location": "archive",
            "summary": "Writing idiomatic Python code",
            "url": "https://example.com/python", "word_count": 3000,
            "tags": {"python": {}, "programming": {}},
        },
        {
            "id": "doc-3", "title": "Machine Learning Fundamentals",
            "author": "Andrew Ng", "category": "pdf", "location": "new",
            "summary": "Core concepts in machine learning",
            "url": "https://example.com/ml", "word_count": 12000,
            "tags": {"ml": {}},
        },
        {
            "id": "doc-4", "title": "Weekly Newsletter #42",
            "author": None, "category": "email", "location": "new",
            "summary": "This week in tech",
            "url": "https://example.com/newsletter",
        },
        {
            "id": "doc-5", "title": "System Design Interview",
            "author": "Alex Xu", "category": "article", "location": "later",
            "summary": "Distributed systems design patterns",
            "url": "https://example.com/system-design", "word_count": 8000,
            "tags": {"programming": {}, "interviews": {}},
        },
    ]
    for doc in docs:
        db.upsert_document(doc)

    # 2 highlights
    db.upsert_highlight(
        {"id": "hl-1", "text": "Ownership is Rust's most unique feature", "note": "Key concept"},
        doc_id="doc-1",
    )
    db.upsert_highlight(
        {"id": "hl-2", "text": "Explicit is better than implicit", "note": "Zen of Python"},
        doc_id="doc-2",
    )

    # 4 tags
    tag_pairs = [
        ("rust", "rust"), ("python", "python"), ("ml", "ml"), ("programming", "programming"),
    ]
    for key, name in tag_pairs:
        db.upsert_tag(key, name)
    db.refresh_tag_counts()

    db.rebuild_fts_indexes()
    return db


def _build_mcp_server_and_app(
    oauth: OAuthServer,
    db: Database,
    token_store: TokenStore,
) -> tuple[FastMCP, Starlette]:
    """Build the FastMCP server and Starlette app (shared by fixtures)."""
    token_verifier = ReadwiseTokenVerifier(oauth)

    @contextlib.asynccontextmanager
    async def test_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
        client = ReadwiseClient(token="test-readwise-token-e2e")
        try:
            yield AppContext(client=client, db=db, token_store=token_store)
        finally:
            await client.close()

    mcp_server = FastMCP(
        name="Readwise Reader",
        instructions="Test MCP server",
        lifespan=test_lifespan,
        token_verifier=token_verifier,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(TEST_SERVER_URL),
            required_scopes=["readwise:read"],
            resource_server_url=AnyHttpUrl(TEST_SERVER_URL),
        ),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
    )

    register_document_tools(mcp_server)
    register_search_tools(mcp_server)
    register_tag_tools(mcp_server)
    register_triage_tools(mcp_server)
    register_digest_tools(mcp_server)

    mcp_app = mcp_server.streamable_http_app()

    # No lifespan on the Starlette app -- session_manager.run() is managed
    # explicitly in the e2e_mcp_session fixture (httpx.ASGITransport doesn't
    # trigger ASGI lifespan events).
    routes = [
        *oauth.routes(),
        Route("/webhook", lambda r: None, methods=["POST"]),
        Mount("/", mcp_app),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
    return mcp_server, app


@pytest.fixture
def e2e_app(
    e2e_oauth: OAuthServer,
    e2e_db: Database,
    e2e_token_store: TokenStore,
) -> Starlette:
    """ASGI app for non-MCP tests (OAuth, raw HTTP auth checks)."""
    _, app = _build_mcp_server_and_app(e2e_oauth, e2e_db, e2e_token_store)
    return app


@pytest.fixture
def e2e_access_token(e2e_oauth: OAuthServer) -> str:
    """Valid JWT access token for test requests."""
    resp = e2e_oauth._issue_tokens("e2e-test-client", ["readwise:read", "readwise:write"])
    body = orjson.loads(resp.body)
    return body["access_token"]


@pytest.fixture
async def e2e_mcp_session(
    e2e_oauth: OAuthServer,
    e2e_db: Database,
    e2e_token_store: TokenStore,
    e2e_access_token: str,
) -> AsyncGenerator[ClientSession]:
    """Connected and initialized MCP ClientSession over in-process ASGI transport.

    Runs the full MCP client stack in a dedicated asyncio task so that all
    anyio cancel scopes are entered and exited within the same task.
    pytest-asyncio tears down async generator fixtures in a different task
    from setup, which causes anyio to raise 'Attempted to exit cancel scope
    in a different task' during teardown of nested context managers.
    """
    mcp_server, app = _build_mcp_server_and_app(e2e_oauth, e2e_db, e2e_token_store)

    ready: asyncio.Event = asyncio.Event()
    done: asyncio.Event = asyncio.Event()
    session_ref: dict[str, ClientSession] = {}

    async def _run() -> None:
        async with mcp_server.session_manager.run():
            transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
            async with httpx.AsyncClient(
                transport=transport,
                base_url=TEST_SERVER_URL,
                headers={"Authorization": f"Bearer {e2e_access_token}"},
            ) as http_client:
                async with streamable_http_client(
                    f"{TEST_SERVER_URL}/mcp",
                    http_client=http_client,
                ) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        session_ref["session"] = session
                        ready.set()
                        await done.wait()

    task = asyncio.create_task(_run())
    await ready.wait()

    yield session_ref["session"]

    done.set()
    try:
        await asyncio.wait_for(task, timeout=5.0)
    except (TimeoutError, RuntimeError, BaseExceptionGroup):
        pass
    if not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
