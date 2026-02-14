last updated: 2026-02-14

# mcp-apps

Skills for building and migrating MCP Apps -- interactive UIs that run inside MCP-enabled hosts like Claude Desktop, VS Code, and Goose.

MCP Apps (SEP-1865, stable 2026-01-26) is an extension to the Model Context Protocol that enables MCP servers to deliver interactive user interfaces (data visualizations, forms, dashboards) to conversational hosts.

## installation

```bash
# add the marketplace (one time)
/plugin marketplace add fblissjr/fb-claude-skills

# install this plugin
/plugin install mcp-apps@fb-claude-skills
```

For development/testing without installing:

```bash
claude --plugin-dir /path/to/fb-claude-skills/mcp-apps
```

## skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `create-mcp-app` | "create an MCP App", "add a UI to an MCP tool" | Guides building a new MCP App from scratch: framework selection, tool+resource registration, theming, testing |
| `migrate-oai-app` | "migrate from OpenAI Apps SDK", "convert from window.openai" | Step-by-step migration from OpenAI Apps SDK to MCP Apps SDK with API mapping tables and CSP checklist |

## invocation

```
/create-mcp-app
/migrate-oai-app
```

Or describe what you want naturally -- the skills trigger on relevant keywords.

## references

Local copies of upstream documentation for offline use:

| File | Content |
|------|---------|
| `references/overview.md` | Architecture, lifecycle, security model |
| `references/patterns.md` | 13 production patterns (polling, chunked data, CSP, theming, etc.) |
| `references/testing.md` | Testing with basic-host, cloudflared, debugging |
| `references/specification.mdx` | Stable MCP Apps spec (SEP-1865, authoritative reference) |
| `references/migrate_from_openai_apps.md` | Detailed before/after mapping tables for migration |

## upstream

- SDK: https://github.com/modelcontextprotocol/ext-apps
- npm: `@modelcontextprotocol/ext-apps`
- Specification: SEP-1865 (stable 2026-01-26)
