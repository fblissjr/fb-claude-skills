last updated: 2026-02-19

# MCP Protocol and Servers

Domain report on the Model Context Protocol (MCP): wire format, primitives, transports, authentication, SDK implementations, testing infrastructure, registry ecosystem, and security model.

---

## 1. Overview

The Model Context Protocol (MCP) is an open standard for connecting AI applications to external tools, data sources, and APIs. Created by David Soria Parra and Justin Spahr-Summers, it defines a bidirectional protocol between **clients** (Claude Code, Claude Desktop, custom agents) and **servers** (programs exposing capabilities).

MCP solves the N-by-M integration problem. Before MCP, every tool-client pair required bespoke code. MCP provides a single interface: one server works with any client, one client connects to any server. It separates **providing context** (data, tools, prompts) from **using context** (LLM interaction, reasoning).

The ecosystem includes reference servers (Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time), hundreds of third-party integrations, and SDKs for TypeScript, Python, C#, Go, Java, Kotlin, PHP, Ruby, Rust, and Swift.

---

## 2. Protocol Fundamentals

### JSON-RPC 2.0 Wire Format

MCP uses JSON-RPC 2.0 with three message types:

- **Requests** -- carry `id` and `method`, expect a response
- **Notifications** -- fire-and-forget, no `id`
- **Responses** -- carry matching `id`, contain `result` or `error`

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"calc","arguments":{"a":1}}}
{"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"t","progress":0.5}}
{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"result"}]}}
```

### Protocol Version

Current version: `2025-11-25` (defined as `LATEST_PROTOCOL_VERSION` in `schema/2025-11-25/schema.ts`). Versions use **date-based** format (YYYY-MM-DD), not semver. Previous: `2025-06-18`, `2025-03-26`, `2024-11-05`. A `draft/` directory holds in-progress work.

### Core Types and Error Codes

From the schema source of truth (`coderef/mcp/modelcontextprotocol/schema/2025-11-25/schema.ts`):

- `RequestId` (`string | number`), `ProgressToken` (`string | number`), `Cursor` (opaque string)
- `RequestParams` with optional `_meta.progressToken`
- `Result` with optional `_meta`, `Error` with `code`, `message`, `data?`

| Code | Constant | Meaning |
|------|----------|---------|
| -32700 | PARSE_ERROR | Invalid JSON |
| -32600 | INVALID_REQUEST | Invalid JSON-RPC structure |
| -32601 | METHOD_NOT_FOUND | Method does not exist |
| -32602 | INVALID_PARAMS | Invalid method parameters |
| -32603 | INTERNAL_ERROR | Internal server error |
| -32042 | URL_ELICITATION_REQUIRED | Server requires URL-based elicitation |

---

## 3. Three Primitives

MCP defines three capability categories, each with a different control model.

### Tools (Model-Controlled)

Tools let LLMs take actions (like POST endpoints). The model decides when to invoke them. Each has `name`, `title`, `description`, `inputSchema`, optional `outputSchema`, and `annotations` (read-only, destructive, idempotent). Protocol methods: `tools/list`, `tools/call`, `notifications/tools/list_changed`. Capability: `capabilities.tools`.

### Resources (User-Controlled)

Resources expose data (like GET endpoints). The user selects which to include in context. Each has `name`, `uri`, `description`, `mimeType`, `size`. Supports URI templates (RFC 6570), subscriptions, and pagination. Protocol methods: `resources/list`, `resources/read`, `resources/templates/list`, `resources/subscribe`, `resources/unsubscribe`, plus change notifications. Capability: `capabilities.resources`.

### Prompts (User-Invoked)

Prompts are reusable LLM interaction templates. Users trigger them via slash commands (e.g., `/mcp__server__prompt`). Each has `name`, `title`, `description`, `arguments`. Protocol methods: `prompts/list`, `prompts/get`, `notifications/prompts/list_changed`. Capability: `capabilities.prompts`.

| Primitive | Controller | Analogy | Side Effects |
|-----------|-----------|---------|--------------|
| Tools | Model | POST | Expected |
| Resources | User/App | GET | None |
| Prompts | User | Slash command | N/A |

---

## 4. Transport Mechanisms

### stdio (Local)

Runs server as local child process. Communication over stdin/stdout, newline-delimited JSON-RPC. Best for CLI tools, local development, direct system access.

```bash
claude mcp add --transport stdio my-server -- node build/index.js
```

Configuration in `.mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["build/index.js"],
      "env": { "API_KEY": "${API_KEY}" }
    }
  }
}
```

Important: on Windows (not WSL), stdio servers using `npx` require the `cmd /c` wrapper.

### Streamable HTTP (Remote -- Recommended)

HTTP-based transport with request/response over POST (typically `/mcp`), optional SSE streaming, JSON-only response mode (no SSE), session management via `Mcp-Session-Id` header, resumability with event stores, and stateful/stateless operation modes.

Stateless mode (no session tracking) suits horizontally scaled API-style servers. Stateful mode supports session persistence, resumability, and server-initiated requests (sampling, elicitation).

```bash
claude mcp add --transport http my-server https://example.com/mcp
```

Configuration in `.mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

### SSE (Legacy -- Deprecated)

Original HTTP transport using separate POST and SSE GET endpoints. Superseded by Streamable HTTP. Still supported for backward compatibility.

```bash
claude mcp add --transport sse my-server https://example.com/sse
```

| Feature | stdio | Streamable HTTP | SSE (legacy) |
|---------|-------|----------------|--------------|
| Location | Local | Remote | Remote |
| Sessions | Implicit | Optional | Yes |
| Scalability | Single process | Horizontal | Limited |
| Auth | N/A | OAuth 2.0 | Bearer tokens |
| Status | Active | Recommended | Deprecated |

---

## 5. Authentication

### OAuth 2.0 Flow

MCP follows a resource server pattern with separate Authorization Server (AS) and Resource Server (RS). The client discovers the AS via RFC 9728 (Protected Resource Metadata), obtains tokens, and presents them to the MCP server. Claude Code handles the full flow: add server, run `/mcp`, complete browser OAuth, tokens auto-refresh.

For servers without dynamic client registration:

```bash
claude mcp add --transport http --client-id ID --client-secret --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

Secrets are stored in the system keychain (macOS) or credentials file, never in config.

### Bearer Tokens and Variable Expansion

```bash
claude mcp add --transport http api https://api.example.com/mcp --header "Authorization: Bearer TOKEN"
```

`.mcp.json` supports `${VAR}` and `${VAR:-default}` expansion in `command`, `args`, `env`, `url`, and `headers`.

### Installation Scopes

MCP servers can be configured at three scope levels in Claude Code:

| Scope | Storage | Visibility | Use Case |
|-------|---------|-----------|----------|
| Local (default) | `~/.claude.json` under project path | You, this project | Personal dev servers, sensitive credentials |
| Project | `.mcp.json` in project root (version controlled) | All team members | Shared tools, team collaboration |
| User | `~/.claude.json` global | You, all projects | Cross-project utilities |

Precedence: local > project > user. Claude Code prompts for approval before using project-scoped servers.

---

## 6. Capability Negotiation

### Initialization Sequence

1. Client sends `initialize` with `protocolVersion`, `clientInfo`, `capabilities`
2. Server responds with its `protocolVersion`, `serverInfo`, `capabilities`, optional `instructions`
3. Client sends `notifications/initialized`
4. Normal exchange begins. If client cannot support server's version, it must disconnect.

### Client Capabilities

Declared in `ClientCapabilities` (from schema):

| Capability | Purpose |
|-----------|---------|
| `roots` | Client can expose filesystem roots to server |
| `roots.listChanged` | Client sends notifications when roots change |
| `sampling` | Client supports LLM sampling requests from server |
| `sampling.context` | Client supports context inclusion in sampling |
| `sampling.tools` | Client supports tool use in sampling |
| `elicitation.form` | Client supports form-mode elicitation |
| `elicitation.url` | Client supports URL-mode elicitation |
| `tasks` | Client supports task-augmented requests |
| `tasks.list` / `tasks.cancel` | Task listing and cancellation |
| `experimental` | Non-standard capabilities (open set) |

### Server Capabilities

Declared in `ServerCapabilities` (from schema):

| Capability | Purpose |
|-----------|---------|
| `tools` / `tools.listChanged` | Server offers tools, with change notifications |
| `resources` / `resources.subscribe` / `resources.listChanged` | Server offers resources with subscriptions |
| `prompts` / `prompts.listChanged` | Server offers prompts with change notifications |
| `logging` | Server can send log messages to client |
| `completions` | Server supports argument autocompletion |
| `tasks` / `tasks.list` / `tasks.cancel` | Task support with listing and cancellation |
| `experimental` | Non-standard capabilities (open set) |

### Enforcement

Both SDKs enforce capabilities at runtime. Before sending a request, the sender checks the receiver declared the relevant capability via `assertCapabilityForMethod()`. Before registering a handler, the SDK validates local capability declaration via `assertRequestHandlerCapability()`. Servers send `list_changed` notifications when capabilities change; Claude Code automatically refreshes on receipt.

---

## 7. Advanced Features

### Sampling

Servers request LLM completions from clients, creating a bidirectional flow. Requires client capability `sampling`. The server calls `ctx.session.create_message()` (Python) or `server.createMessage()` (TypeScript) with messages and `max_tokens`. Supports optional context inclusion and tool use parameters.

```python
@mcp.tool()
async def summarize(text: str, ctx: Context[ServerSession, None]) -> str:
    result = await ctx.session.create_message(
        messages=[SamplingMessage(role="user", content=TextContent(type="text", text=f"Summarize: {text}"))],
        max_tokens=200,
    )
    return result.content.text
```

### Elicitation

Servers request structured user input during tool execution. Two modes:

- **Form mode** -- collects non-sensitive structured data via Pydantic schema. The client renders a form from the schema.
- **URL mode** -- redirects users to external URLs for sensitive operations (OAuth, payments, credential collection). Uses `ctx.elicit_url()`.

Returns `ElicitationResult` with `action` ("accept", "decline", "cancel") and optional validated `data`. The `UrlElicitationRequiredError` pattern (error code -32042) signals that the server cannot proceed without URL elicitation.

### Tasks

Long-running operations with polling and resumption. When a request includes `task` metadata, the server returns a `CreateTaskResult` immediately. The actual result is retrieved later via `tasks/result`. Both sides must declare task-augmented request types in capabilities. Located in experimental namespaces in both SDKs (`packages/core/src/experimental/tasks/` in TypeScript).

### Roots, Logging, Completions, Progress, Pagination

- **Roots** -- Clients expose filesystem boundaries via `roots/list`. Servers discover workspace scope. Change notifications via `notifications/roots/list_changed`.
- **Logging** -- Structured log messages at debug/info/warning/error levels via `notifications/message`. Python SDK: `ctx.debug()`, `ctx.info()`, `ctx.warning()`, `ctx.error()`.
- **Completions** -- Autocompletion suggestions for prompt arguments and resource template parameters. Supports context-aware completions based on previously resolved values.
- **Progress** -- `notifications/progress` with `progressToken`, `progress`, `total`, `message`. The token is passed in the original request's `_meta.progressToken`.
- **Pagination** -- Cursor-based for all list operations via `cursor` request param and `nextCursor` response field.

---

## 8. Building Servers with TypeScript SDK

The TypeScript SDK (`coderef/mcp/typescript-sdk/`) publishes `@modelcontextprotocol/server` and `@modelcontextprotocol/client` with Zod v4 peer dependency. Optional middleware: `@modelcontextprotocol/node`, `@modelcontextprotocol/express`, `@modelcontextprotocol/hono`. Currently v2 pre-alpha; v1.x recommended for production.

Architecture: Types layer (Zod schemas) -> Protocol layer (abstract JSON-RPC routing) -> High-level APIs (`McpServer` for servers, `Client` for clients).

```typescript
const server = new McpServer({ name: 'my-server', version: '1.0.0' });

server.registerTool('calc', {
    title: 'Calculator', description: 'Add numbers',
    inputSchema: z.object({ a: z.number(), b: z.number() }),
    outputSchema: z.object({ sum: z.number() })
}, async ({ a, b }) => ({
    content: [{ type: 'text', text: String(a + b) }],
    structuredContent: { sum: a + b }
}));

// Streamable HTTP (stateful)
const transport = new NodeStreamableHTTPServerTransport({ sessionIdGenerator: () => randomUUID() });
// Stateless: sessionIdGenerator: undefined
// JSON-only: enableJsonResponse: true
await server.connect(transport);

// Or stdio
await server.connect(new StdioServerTransport());
```

### Handler Context

Request handlers receive a structured context with nested groups:

- `mcpReq.id` -- JSON-RPC message ID
- `mcpReq.method` -- request method string (e.g., `tools/call`)
- `mcpReq.signal` -- AbortSignal for cancellation
- `mcpReq.send(request, schema)` -- send related request (bidirectional flows)
- `mcpReq.notify(notification)` -- send notifications back
- `http?.authInfo` -- validated auth token info (HTTP transports only)
- `task?` -- task context with `id`, `store`, `requestedTtl`

Server context extends with `mcpReq.log()`, `mcpReq.elicitInput()`, `mcpReq.requestSampling()`.

### Middleware Packages

Thin framework adapters (no new MCP functionality):

- `@modelcontextprotocol/node` -- wraps `IncomingMessage`/`ServerResponse`
- `@modelcontextprotocol/express` -- Express defaults + Host header validation
- `@modelcontextprotocol/hono` -- Hono defaults + JSON body parsing + Host header validation

---

## 9. Building Servers with Python SDK

The Python SDK (`coderef/mcp/python-sdk/`) provides `FastMCP` (high-level, decorator-based) and a low-level server. Install: `uv add "mcp[cli]"`. v1.x stable; v2 in development.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo", json_response=True)

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    return f"Hello, {name}!"

@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review:\n\n{code}"

mcp.run(transport="streamable-http")  # or default stdio
```

Context via type annotation: `ctx: Context[ServerSession, None]` provides `request_id`, logging (`debug`/`info`/`warning`/`error`), `report_progress`, `read_resource`, `elicit`, `session` (for sampling). Structured output works with Pydantic models, TypedDicts, dataclasses, `dict[str, T]`, primitives.

### Authentication

The Python SDK implements OAuth 2.1 resource server functionality via `mcp.server.auth`. Servers provide a `TokenVerifier` implementation and `AuthSettings`:

```python
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

class MyVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        pass  # validate against your auth server

mcp = FastMCP("Protected", token_verifier=MyVerifier(),
    auth=AuthSettings(issuer_url="https://auth.example.com",
                      resource_server_url="http://localhost:3001",
                      required_scopes=["user"]))
```

### Lifespan and Mounting

Async lifespan context managers handle startup/shutdown. Resources are accessible in tools via `ctx.request_context.lifespan_context`. Servers mount in Starlette/ASGI via `mcp.streamable_http_app()` for multi-server deployments.

---

## 10. Testing with MCP Inspector

The Inspector (`coderef/mcp/inspector/`) has two components: MCPI (React web UI, port 6274) and MCPP (Node.js protocol bridge, port 6277). The proxy connects to your server as an MCP client while serving the UI.

```bash
npx @modelcontextprotocol/inspector node build/index.js           # UI mode
npx @modelcontextprotocol/inspector --cli node build/index.js     # CLI mode
npx @modelcontextprotocol/inspector --cli --method tools/list node build/index.js
npx @modelcontextprotocol/inspector --config mcp.json --server my-server
```

Supports all transports (stdio, SSE, Streamable HTTP). CLI mode enables CI/CD and scripting. UI mode provides form-based testing, request history, and JSON visualization. Exports configurations for Claude Code and Cursor.

Security: auth required by default (random session token), localhost-only binding, Origin header validation. `DANGEROUSLY_OMIT_AUTH` exists but is strongly discouraged (CVE-2025-49596).

---

## 11. Publishing to MCP Registry

The Registry (`coderef/mcp/registry/`) is a Go/PostgreSQL application providing server discovery. API freeze at v0.1; preview since September 2025.

Publishing authentication: GitHub OAuth, GitHub OIDC (from Actions), DNS verification, HTTP verification. Namespace ownership validated (e.g., `io.github.username/server` requires GitHub auth as that user).

```bash
make publisher && ./bin/mcp-publisher --help
```

Live API at `https://registry.modelcontextprotocol.io`. Local dev: `make dev-compose`.

### Architecture

The registry is a Go application with PostgreSQL:

```
cmd/publisher/     -- server publishing CLI
internal/api/      -- HTTP handlers and routing
internal/auth/     -- GitHub OAuth, JWT, namespace blocking
internal/database/ -- PostgreSQL persistence
internal/service/  -- business logic
internal/validators/ -- input validation
pkg/api/v0/        -- version 0 API types
pkg/model/         -- data models for server.json
```

---

## 12. Security Best Practices

**Input validation** -- Use Zod (TypeScript) or Pydantic (Python) for runtime schema validation. Never trust client data without validation.

**Rate limiting** -- Claude Code warns at 10K tokens output, defaults max at 25K (`MAX_MCP_OUTPUT_TOKENS`). Startup timeout via `MCP_TIMEOUT`.

**Permission boundaries** -- Resources read-only, tools declare nature via annotations, filesystem servers use configurable access controls, stdio servers inherit spawning process permissions.

**Transport security** -- HTTPS in production, localhost-only binding for Inspector, CORS must expose `Mcp-Session-Id`.

**Credentials** -- Never store secrets in committed `.mcp.json`. Use `${VAR}` expansion. Keychain for OAuth secrets. Claude Code prompts approval for project-scoped servers.

**Managed configuration** -- Two mechanisms for organizational control:

1. **Exclusive control** (`managed-mcp.json`): Deploy to system directories. Users cannot add other servers.
   - macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
   - Linux/WSL: `/etc/claude-code/managed-mcp.json`
   - Windows: `C:\Program Files\ClaudeCode\managed-mcp.json`

2. **Policy-based** (allowlists/denylists in managed settings): Restrict by server name (`serverName`), exact command (`serverCommand`), or URL pattern with wildcards (`serverUrl`). Denylist takes absolute precedence. Empty allowlist = complete lockdown. When command entries exist in allowlist, stdio servers must match one of those commands.

**Prompt injection** -- MCP servers fetching untrusted content expose injection risk. Third-party servers are not verified by Anthropic.

**Tool Search security** -- When MCP tool definitions exceed 10% of context window, Claude Code defers loading via Tool Search. Server instructions help Claude discover tools. Configurable via `ENABLE_TOOL_SEARCH` (auto/true/false).

---

## 13. Cross-References

### Related Documents

- `docs/analysis/mcp_apps_and_ui_development.md` -- MCP App patterns, React frontends
- `docs/analysis/plugin_system_architecture.md` -- plugin/MCP server bundling, plugin.json vs .mcp.json
- `docs/analysis/cross_surface_compatibility.md` -- transport compatibility across Claude surfaces

### .mcp.json Files in This Repository

- `mece-decomposer/.mcp.json` -- stdio transport for MECE MCP app (`node ${CLAUDE_PLUGIN_ROOT}/mcp-app/dist/index.cjs --stdio`)
- `coderef/mcp/inspector/.mcp.json` and `coderef/mcp/servers/.mcp.json` -- HTTP to `https://modelcontextprotocol.io/mcp`

### Source Repositories (`coderef/mcp/`)

| Directory | Purpose |
|-----------|---------|
| `modelcontextprotocol/` | Spec, schema, docs |
| `typescript-sdk/` | TS server/client SDK |
| `python-sdk/` | Python FastMCP SDK |
| `inspector/` | Testing/debugging tool |
| `registry/` | Server discovery catalog |
| `servers/` | Reference implementations |
| `access/` | Access control |

### Key File Paths

- Schema source: `coderef/mcp/modelcontextprotocol/schema/2025-11-25/schema.ts`
- TS server guide: `coderef/mcp/typescript-sdk/docs/server.md`
- Python SDK: `coderef/mcp/python-sdk/README.md` (v1), `README.v2.md` (v2 draft)
- Inspector: `coderef/mcp/inspector/README.md`
- Registry: `coderef/mcp/registry/README.md`
- Claude Code MCP docs: `docs/claude-docs/claude_docs_mcp.md`
