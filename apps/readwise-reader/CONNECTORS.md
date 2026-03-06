# Connectors

## How tool references work

This plugin connects to a local Readwise Reader MCP server. Unlike multi-tool plugins, this one has a single connector -- your Readwise Reader account.

The MCP server runs locally and proxies requests to the Readwise Reader API, with a local DuckDB database for fast search and enrichment.

## Connectors for this plugin

| Category | Server | Notes |
|----------|--------|-------|
| Reading library | readwise-reader (local) | Requires Readwise API token, configured on first use via OAuth flow |

## Setup

1. Start the MCP server: `uv run readwise-reader` (serves HTTPS on localhost:8787)
2. The first MCP connection triggers an OAuth flow that asks for your Readwise API token
3. Get your token at [readwise.io/access_token](https://readwise.io/access_token)
4. After token entry, run `/readwise-reader:search sync` to pull your library
