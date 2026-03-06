# Changelog

## 0.3.0

- Env-driven server config: `READWISE_HOST`, `READWISE_PORT`, `READWISE_NO_TLS`, `READWISE_API_TOKEN`
- Optional TLS: HTTPS by default, disable with `READWISE_NO_TLS=1` for dev/testing
- CORS middleware with `mcp-session-id` header exposed (required for Electron/browser MCP clients)
- Env var token fallback (`READWISE_API_TOKEN`) for stdio mode via `mcp dev`/`mcp install`
- E2E test suite: in-process ASGI MCP client tests covering connection, OAuth, all tools, and error handling
- Documented `NODE_EXTRA_CA_CERTS` setup for Claude Desktop TLS trust

## 0.2.0

- Full-text search with BM25 scoring via DuckDB FTS extension (replaces ILIKE)
- Highlight-to-document ID reconciliation bridging Readwise Core v2 and Reader v3 APIs
- Three-tier doc ID resolution: v2_book_id lookup, URL match, prefixed fallback with deferred reconciliation
- Staging table (`staging_highlights`) for unresolved v2 highlights; restored FK on `fact_highlights.doc_id`
- Reconciliation moves staging highlights to fact_highlights once parent document is synced
- FTS indexes auto-rebuild after sync operations
- Webhook handler integration tests (auth, document events, highlight events, error handling)
- Token refresh lifecycle tests (full OAuth flow, rotation invalidation, expired token handling)
- HTTPS via mkcert locally-trusted TLS certs; marketplace.json for Cowork plugin installation

## 0.1.0

- Initial project scaffold
- Readwise Reader API client with async httpx
- DuckDB storage layer (star schema)
- Batch sync engine (API -> DuckDB)
- MCP tools: documents, highlights, tags, search, library stats
- OAuth 2.1 authorization server with PKCE
- Streamable HTTP MCP server
- Cowork plugin: 5 commands, 3 skills
- Enrichment pipeline stubs
