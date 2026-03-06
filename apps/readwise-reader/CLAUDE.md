# CLAUDE.md

last updated: 2026-02-06

Project-specific instructions for Claude instances working on this codebase.

## project overview

This is a Readwise Reader MCP server + Cowork plugin. It has three layers:

1. **MCP server** (`src/readwise_reader/server.py`): Composite Starlette app on `https://localhost:8787` (TLS via mkcert, configurable via env vars) serving MCP tools (via FastMCP), OAuth 2.1 endpoints, and a webhook receiver
2. **Storage layer** (`src/readwise_reader/storage/`): DuckDB star schema with batch sync engine and real-time webhook ingestion
3. **Cowork plugin** (`commands/`, `skills/`): Commands and skills that Claude uses to invoke MCP tools

## directory layout

```
src/readwise_reader/
  api/
    client.py          -- Async httpx client (Reader v3 + Core v2 APIs)
    models.py          -- Pydantic models for all API request/response shapes
    rate_limiter.py    -- Token bucket rate limiter (20 read/min, 50 write/min)
  auth/
    oauth_server.py    -- OAuth 2.1 server (PKCE, JWT, refresh tokens)
    token_store.py     -- Fernet-encrypted local storage for Readwise API token
    metadata.py        -- MCP TokenVerifier bridge
  storage/
    database.py        -- DuckDB connection, schema init, all CRUD methods
    schemas/reader.sql -- DDL for all tables (dim_documents, fact_highlights, staging_highlights, etc.)
    sync.py            -- Batch sync engine (API -> DuckDB), three-tier doc ID resolution
    webhook_handler.py -- Real-time Starlette webhook receiver
  tools/
    documents.py       -- save, list, get, update, delete document tools
    search.py          -- BM25 full-text search tools (documents + highlights)
    tags.py            -- tag listing and tag-based document queries
    triage.py          -- inbox triage tools (single + batch)
    digest.py          -- library stats, reading digest, sync_library, get_highlights
  enrichment/
    pipeline.py        -- STUBS: PyLate embeddings + structured extraction (not yet implemented)
  server.py            -- Entry point, lifespan, composite ASGI app assembly

.claude-plugin/plugin.json  -- Plugin manifest
.mcp.json                   -- MCP server connection config (localhost:8787/mcp)
commands/                   -- 5 commands (digest, reference, save, search, triage)
skills/                     -- 3 skills (library-search, content-triage, knowledge-retrieval)
CONNECTORS.md               -- Single connector docs

tests/
  test_storage.py    -- DuckDB CRUD, FTS, reconciliation, audit
  test_webhook.py    -- Starlette TestClient integration tests
  test_api_client.py -- httpx/respx mocked API client tests
  test_auth.py       -- OAuth server, PKCE, JWT, token refresh lifecycle
  test_tools.py      -- MCP tool integration tests
  e2e/
    conftest.py            -- Fixtures: test ASGI app, MCP client session, seeded DB
    test_e2e_connection.py -- MCP handshake, capabilities, session lifecycle
    test_e2e_oauth.py      -- OAuth metadata, registration, PKCE flow, token rejection
    test_e2e_tools.py      -- Tool listing + invocation for all 5 tool modules
    test_e2e_errors.py     -- Auth failures, invalid tools, malformed requests

internal/log/        -- Daily development logs (log_YYYY-MM-DD.md)
```

## key patterns to understand

### two-API problem

Readwise has two APIs with different ID systems:
- **Reader v3**: Documents have UUID-style string IDs (`doc_id`), cursor-based pagination, 20 req/min reads
- **Core v2**: Highlights reference integer `book_id`, cursor-based pagination via export endpoint

When highlights arrive from v2, their `book_id` may not match any known document yet. Resolution uses a three-tier strategy (in `sync.py:_resolve_doc_id` and `webhook_handler.py:_resolve_doc_id`):
1. Look up `v2_book_id` in `dim_documents`
2. Match by `source_url` or `url`, then backfill the `v2_book_id` mapping
3. Fall back to `v2:{book_id}` prefix (routed to `staging_highlights`)

### staging table pattern

`fact_highlights` has a real FK to `dim_documents`. Unresolved highlights (with `v2:*` doc_ids) go to `staging_highlights` (same schema, no FK). `reconcile_orphaned_highlights()` moves them to `fact_highlights` once the parent document syncs. This routing is transparent -- `upsert_highlight()` checks the doc_id prefix internally.

### FTS search

DuckDB FTS extension provides BM25-scored full-text search. Indexes are static snapshots rebuilt after sync operations (`rebuild_fts_indexes()`). All search methods have an ILIKE fallback if FTS fails.

### OAuth flow

The OAuth server bridges Readwise's API-key auth to MCP's token-based auth:
1. MCP client registers via dynamic client registration
2. Authorization redirects to a local HTML form where the user enters their Readwise API token
3. Token is validated against `readwise.io/api/v2/auth/` and stored encrypted locally
4. Server issues short-lived JWTs to MCP clients (1hr access, 30-day refresh)
5. MCP clients never see the Readwise API token

### lifespan context

Shared resources (`ReadwiseClient`, `Database`, `TokenStore`) are initialized in `app_lifespan()` and accessed by tools via `ctx.request_context.lifespan_context`. This is the standard FastMCP pattern.

## conventions

- **Python 3.13**, managed with `uv` (never pip/python directly)
- **orjson** for all JSON serialization
- **ruff** for linting (`line-length=100`, target `py313`, select `E,W,F,I,B,C4,UP`)
- **pytest** with `pytest-asyncio` (mode=auto), `respx` for HTTP mocking
- DuckDB parameterized queries: `?` placeholders cannot mix with SQL functions like `CURRENT_TIMESTAMP` in the same VALUES clause. Pass timestamps as parameters instead.
- Use `EXCLUDED.column` in ON CONFLICT DO UPDATE to reference new values (DuckDB syntax)
- Tool registration follows `register_*_tools(mcp)` pattern in separate modules under `tools/`
- No emojis in code, docs, or output
- Never commit or stage files automatically
- Keep `CHANGELOG.md` updated (semver, no dates)
- Maintain daily logs in `internal/log/log_YYYY-MM-DD.md`

## running

```bash
uv sync                        # install deps
uv run readwise-reader         # start server on https://localhost:8787 (default, TLS)
uv run pytest tests/ -v        # run all tests (unit + e2e)
uv run pytest tests/e2e/ -v   # run e2e tests only
uv run ruff check src/ tests/  # lint
```

### environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `READWISE_HOST` | `127.0.0.1` | Bind address |
| `READWISE_PORT` | `8787` | Bind port |
| `READWISE_NO_TLS` | (unset) | Set to `1`/`true`/`yes` to disable TLS (for dev/testing) |
| `READWISE_API_TOKEN` | (unset) | Readwise API token (bypasses OAuth, used in stdio mode) |

### TLS setup (required for HTTPS mode)

The server defaults to HTTPS. Use mkcert for locally-trusted certs:
```bash
brew install mkcert && mkcert -install   # one-time
mkdir -p certs && cd certs && mkcert localhost 127.0.0.1 ::1 && cd ..
```

Cert lookup order: `certs/` (project root) then `~/.readwise-reader/certs/`. The server fails with a clear error if no certs are found.

### Claude Desktop setup (one-time)

Claude Desktop's Electron runtime doesn't trust mkcert's CA by default. Fix with `NODE_EXTRA_CA_CERTS`:

**macOS** (persists across reboots):
```bash
launchctl setenv NODE_EXTRA_CA_CERTS "$(mkcert -CAROOT)/rootCA.pem"
# Restart Claude Desktop after running this
```

**Linux** (add to ~/.profile or equivalent):
```bash
export NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem"
```

**Windows** (PowerShell, then restart Claude Desktop):
```powershell
[System.Environment]::SetEnvironmentVariable("NODE_EXTRA_CA_CERTS", "$(mkcert -CAROOT)\rootCA.pem", "User")
```

### running modes

- **HTTPS (default)**: `uv run readwise-reader` -- for Claude Desktop Cowork connector
- **HTTP (dev)**: `READWISE_NO_TLS=1 uv run readwise-reader` -- for MCP Inspector, local testing
- **stdio**: `READWISE_API_TOKEN=<token> uv run mcp dev src/readwise_reader/server.py:mcp` -- for Claude Desktop native MCP

## data locations

- DuckDB database: `~/.readwise-reader/reader.duckdb`
- Encrypted token store: `~/.readwise-reader/tokens.enc`
- Encryption key: `~/.readwise-reader/.key` (mode 0600)
- TLS certs: `certs/` (gitignored) or `~/.readwise-reader/certs/`

## what's not yet implemented

- `enrichment/pipeline.py`: PyLate embeddings and structured extraction are stubs
- `spec.md` references PyLate with `lightonai/GTE-ModernColBERT-v1` model (downloaded to `models/`)
- The `models/` directory has a `.gitignore` (large model files excluded from git)
