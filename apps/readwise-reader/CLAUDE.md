# CLAUDE.md

last updated: 2026-02-06

Project-specific instructions for Claude instances working on this codebase.

## project overview

This is a Readwise Reader MCP server + Cowork plugin. It has three layers:

1. **MCP server** (`src/readwise_reader/server.py`): Composite Starlette app on `https://localhost:8787` (TLS via mkcert, configurable via env vars) serving MCP tools (via FastMCP), OAuth 2.1 endpoints, and a webhook receiver
2. **Storage layer** (`src/readwise_reader/storage/`): DuckDB star schema with batch sync engine and real-time webhook ingestion
3. **Cowork plugin** (`commands/`, `skills/`): Commands and skills that Claude uses to invoke MCP tools

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

- **ruff** >= 0.16 for linting (`line-length=100`, target `py313`, `extend-select = E,W,F,I,B,C4,UP`). `extend-select`, not `select`: `select` would replace ruff's 413 default rules with just these seven groups.
- **pytest** with `pytest-asyncio` (mode=auto), `respx` for HTTP mocking
- **Greenfield default for the local DB.** Prefer `CREATE OR REPLACE VIEW` plus re-init over migration bridges. This database is a local mirror of a remote SaaS, so it can be rebuilt; a migration bridge buys nothing and has to be maintained. Production-facing schemas are the exception, and this package has none — `marketplace.json` and published plugin contents are the repo-level cases. (Held as a root repo invariant until 2026-08-13, moved here because it only ever applied to this package.)
- DuckDB parameterized queries: `?` placeholders cannot mix with SQL functions like `CURRENT_TIMESTAMP` in the same VALUES clause. Pass timestamps as parameters instead.
- Use `EXCLUDED.column` in ON CONFLICT DO UPDATE to reference new values (DuckDB syntax)
- Tool registration follows `register_*_tools(mcp)` pattern in separate modules under `tools/`
- No emojis in code, docs, or output
- Changelog entries go in the **repo root** `CHANGELOG.md`, not here. This package deliberately has no changelog of its own: it was the only first-party unit with one, so nothing maintained it and it drifted five versions behind `pyproject.toml` before anyone noticed. Semver, no dates.
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

Cert lookup order: `certs/` (project root) then `<HOME>/.readwise-reader/certs/`. The server fails with a clear error if no certs are found.

### Claude Desktop setup (one-time)

Claude Desktop's Electron runtime doesn't trust mkcert's CA by default. Fix with `NODE_EXTRA_CA_CERTS`:

**macOS** (persists across reboots):
```bash
launchctl setenv NODE_EXTRA_CA_CERTS "$(mkcert -CAROOT)/rootCA.pem"
# Restart Claude Desktop after running this
```

**Linux** (add to <HOME>/.profile or equivalent):
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

- DuckDB database: `<HOME>/.readwise-reader/reader.duckdb`
- Encrypted token store: `<HOME>/.readwise-reader/tokens.enc`
- Encryption key: `<HOME>/.readwise-reader/.key` (mode 0600)
- TLS certs: `certs/` (gitignored) or `<HOME>/.readwise-reader/certs/`

## what's not yet implemented

- `enrichment/pipeline.py`: PyLate embeddings and structured extraction are stubs
- `spec.md` references PyLate with `lightonai/GTE-ModernColBERT-v1` model (downloaded to `models/`)
- The `models/` directory has a `.gitignore` (large model files excluded from git)
