last updated: 2026-02-19

# MCP Apps and UI Development

Building interactive user interfaces for MCP tools. This report covers the two primary
SDK paths -- the official MCP Apps specification (`@modelcontextprotocol/ext-apps`,
SEP-1865) and the MCP UI SDK (`@mcp-ui/*`) -- and how they converge on a single standard
for delivering rich UI from MCP servers into conversational hosts.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Official MCP Apps SDK (ext-apps)](#2-official-mcp-apps-sdk-ext-apps)
3. [Tool-UI Linkage](#3-tool-ui-linkage)
4. [View Communication](#4-view-communication)
5. [React Integration](#5-react-integration)
6. [Framework Templates](#6-framework-templates)
7. [MCP UI SDK](#7-mcp-ui-sdk)
8. [Platform Adapters](#8-platform-adapters)
9. [CSP and Security](#9-csp-and-security)
10. [Bundling](#10-bundling)
11. [Testing Patterns](#11-testing-patterns)
12. [Host Compatibility Matrix](#12-host-compatibility-matrix)
13. [Graceful Degradation](#13-graceful-degradation)
14. [Real Implementation Analysis](#14-real-implementation-analysis)
15. [Cross-References](#15-cross-references)

---

## 1. Overview

### The Problem

MCP tools return text and structured data. That covers a wide range of use cases but
breaks down when the result demands interactivity -- charts, forms, dashboards, video
players, 3D scenes, or real-time monitoring. Before standardization, each host that wanted
UI support implemented it differently, forcing server developers to maintain separate
adapters for each host.

### Two SDK Paths

Two independent efforts converged into a single specification (SEP-1865, stable since
2026-01-26):

**Official MCP Apps SDK** (`@modelcontextprotocol/ext-apps`)
- Published by the Model Context Protocol organization.
- Defines the specification, core classes (`App`, `AppBridge`), server helpers
  (`registerAppTool`, `registerAppResource`), React hooks, and reference implementations.
- Source: `coderef/ext-apps/` in this repository.
- npm: `@modelcontextprotocol/ext-apps`

**MCP UI SDK** (`@mcp-ui/*`)
- Pioneered by Ido Salomon and Liad Yosef. Directly influenced the MCP Apps specification.
- Provides `@mcp-ui/server` (TypeScript, Python, Ruby) and `@mcp-ui/client`.
- `@mcp-ui/client` is the recommended SDK for hosts implementing MCP Apps.
- Adds platform adapters (e.g., ChatGPT Apps SDK adapter), legacy `UIResourceRenderer`,
  and Web Component support.
- Source: `coderef/mcp-ui/` in this repository.
- npm: `@mcp-ui/server`, `@mcp-ui/client`

The two are complementary, not competing. The ext-apps SDK defines the specification and
the View/Host protocol. The mcp-ui SDK provides the `createUIResource` helper for servers
and the `AppRenderer`/`UIResourceRenderer` components for hosts. Both are fully compliant
with the MCP Apps specification.

### Architecture

Three entities cooperate:

```
Server                    Host                     View (iframe)
+----------------+       +----------------+       +----------------+
| MCP Server     |<----->| AppBridge      |<----->| App            |
| - Tools        | MCP   | - Proxies MCP  | post  | - PostMessage  |
| - UI Resources | proto | - Manages View | Msg   |   Transport    |
+----------------+       +----------------+       +----------------+
```

- **Server** -- a standard MCP server that declares tools and `ui://` resources.
- **Host** -- the chat client (Claude, VS Code, Goose, etc.) that connects to servers,
  embeds Views in sandboxed iframes, and proxies communication between View and Server.
- **View** -- the UI running inside a sandboxed iframe. Receives tool data from the Host
  and can call server tools or send messages back to the conversation.

---

## 2. Official MCP Apps SDK (ext-apps)

### Package Structure

| Package / Import Path | Purpose |
|---|---|
| `@modelcontextprotocol/ext-apps` | Core: `App` class, `PostMessageTransport`, type exports |
| `@modelcontextprotocol/ext-apps/react` | React hooks: `useApp`, `useHostStyles`, `useAutoResize`, `useDocumentTheme` |
| `@modelcontextprotocol/ext-apps/app-bridge` | Host-side: `AppBridge` class for embedding and communicating with Views |
| `@modelcontextprotocol/ext-apps/server` | Server-side: `registerAppTool`, `registerAppResource`, `getUiCapability` |

Source files in `coderef/ext-apps/src/`:

- `app.ts` -- `App` class (extends MCP `Protocol`)
- `app-bridge.ts` -- `AppBridge` class (extends MCP `Protocol`)
- `server/index.ts` -- server helper functions
- `message-transport.ts` -- `PostMessageTransport`
- `types.ts` -- protocol types, Zod schemas
- `styles.ts` -- `applyHostStyleVariables`, `applyHostFonts`, `applyDocumentTheme`
- `react/` -- React hooks

### The App Class

`App` extends the MCP SDK's `Protocol` class. It represents the View side of the protocol.

Key capabilities:

- **Lifecycle management** -- `connect()` performs the initialization handshake
  (`ui/initialize` request, `ui/notifications/initialized` notification).
- **Server tool calls** -- `callServerTool()` proxies tool calls through the Host to the
  originating MCP server.
- **Messages** -- `sendMessage()` adds messages to the conversation thread.
- **Model context** -- `updateModelContext()` provides context to the model for future
  turns without triggering an immediate response.
- **Links** -- `openLink()` requests the Host open an external URL.
- **Display modes** -- `requestDisplayMode()` requests inline, fullscreen, or
  picture-in-picture rendering.
- **Size reporting** -- `sendSizeChanged()` and `setupSizeChangedNotifications()`
  (auto-resize via `ResizeObserver`, enabled by default).
- **Logging** -- `sendLog()` sends debug/telemetry to the Host.

Convenience notification setters (register before calling `connect()`):

```typescript
app.ontoolinput = (params) => { /* complete tool arguments */ };
app.ontoolinputpartial = (params) => { /* streaming partial arguments */ };
app.ontoolresult = (params) => { /* tool execution result */ };
app.ontoolcancelled = (params) => { /* tool was cancelled */ };
app.onhostcontextchanged = (params) => { /* theme, locale, etc. changed */ };
app.onteardown = async () => { /* cleanup before unmount */ return {}; };
app.oncalltool = async (params) => { /* handle tool calls TO this app */ };
app.onlisttools = async () => { /* list tools this app provides */ };
```

Minimal usage:

```typescript
import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";

const app = new App({ name: "WeatherApp", version: "1.0.0" }, {});

app.ontoolinput = (params) => renderWeather(params.arguments);
app.ontoolresult = (params) => updateWithResult(params.content);

await app.connect(new PostMessageTransport(window.parent, window.parent));
```

### The AppBridge Class

`AppBridge` is the Host-side counterpart. It extends `Protocol` and acts as a proxy
between the Host application and a View running in an iframe.

Key capabilities:

- **Automatic MCP forwarding** -- when constructed with an MCP `Client`, it automatically
  sets up request/notification forwarding for tools, resources, and prompts based on
  server capabilities.
- **Manual handler registration** -- when constructed with `null` client, the host
  registers handlers manually via setters (`oncalltool`, `onlistresources`,
  `onreadresource`, etc.).
- **Data delivery** -- `sendToolInput()`, `sendToolInputPartial()`, `sendToolResult()`,
  `sendToolCancelled()`.
- **Context management** -- `setHostContext()` updates theme, locale, dimensions, and
  notifies the View of changes via diff detection.
- **Graceful shutdown** -- `teardownResource()` sends a teardown request before
  unmounting the iframe.
- **Sandbox support** -- `onsandboxready` / `sendSandboxResourceReady()` for the
  double-iframe sandbox architecture required by web-based hosts.

Lifecycle from the host perspective:

```typescript
const bridge = new AppBridge(mcpClient, hostInfo, capabilities);
const transport = new PostMessageTransport(iframe.contentWindow!, iframe.contentWindow!);

bridge.oninitialized = () => {
  bridge.sendToolInput({ arguments: toolArgs });
};
bridge.onsizechange = ({ width, height }) => {
  iframe.style.height = `${height}px`;
};

await bridge.connect(transport);
```

### Lifecycle Summary

1. **Create** -- Host instantiates `AppBridge`; View instantiates `App`.
2. **Connect** -- Both call `connect()` with `PostMessageTransport`.
3. **Initialize** -- View sends `ui/initialize`; Host responds with capabilities, context.
4. **Data delivery** -- Host sends `tool-input` (and optionally `tool-input-partial`
   before it, and `tool-result` after execution).
5. **Interactive phase** -- View calls server tools, sends messages, updates context.
6. **Teardown** -- Host sends `ui/resource-teardown`; View performs cleanup.

---

## 3. Tool-UI Linkage

### Registration

Server-side, tools are linked to UI resources through `_meta.ui.resourceUri`:

```typescript
import { registerAppTool, registerAppResource, RESOURCE_MIME_TYPE }
  from "@modelcontextprotocol/ext-apps/server";

// 1. Register the UI resource
registerAppResource(server, "Weather View", "ui://weather/view.html", {
  description: "Interactive weather display",
}, async () => ({
  contents: [{
    uri: "ui://weather/view.html",
    mimeType: RESOURCE_MIME_TYPE,  // "text/html;profile=mcp-app"
    text: await fs.readFile("dist/view.html", "utf-8"),
  }],
}));

// 2. Register the tool with UI metadata
registerAppTool(server, "get-weather", {
  description: "Get current weather for a location",
  inputSchema: { location: z.string() },
  _meta: { ui: { resourceUri: "ui://weather/view.html" } },
}, async (args) => {
  const weather = await fetchWeather(args.location);
  return { content: [{ type: "text", text: JSON.stringify(weather) }] };
});
```

### The _meta.ui Object

```typescript
interface McpUiToolMeta {
  resourceUri?: string;                    // UI resource URI (ui:// scheme)
  visibility?: Array<"model" | "app">;     // Who can see/call this tool
}
```

The `registerAppTool` helper normalizes metadata: if `_meta.ui.resourceUri` is set, it
also populates the deprecated flat key `_meta["ui/resourceUri"]` for backward
compatibility with older hosts.

### Tool Visibility

- **Default** (`["model", "app"]`): tool visible to both the LLM and the View.
- **Model-only** (`["model"]`): tool visible to LLM, not callable by the View.
- **App-only** (`["app"]`): tool hidden from LLM, only callable by the View. Ideal for
  refresh buttons, pagination, form submissions, and other UI-driven actions that should
  not clutter the agent's tool list.

```typescript
registerAppTool(server, "update-quantity", {
  description: "Update item quantity in cart",
  inputSchema: { itemId: z.string(), quantity: z.number() },
  _meta: {
    ui: {
      resourceUri: "ui://shop/cart.html",
      visibility: ["app"],  // Hidden from model
    },
  },
}, async ({ itemId, quantity }) => {
  return { content: [{ type: "text", text: JSON.stringify(await updateCart(itemId, quantity)) }] };
});
```

### Resource Discovery Flow

1. Host calls `tools/list` on the server at connection time.
2. Host inspects each tool's `_meta.ui.resourceUri` (using `getToolUiResourceUri()`).
3. If present and host supports MCP Apps, host may prefetch via `resources/read`.
4. When the LLM calls the tool, host renders the cached HTML in a sandboxed iframe and
   passes tool input/result to the View.

The `getToolUiResourceUri()` utility supports both the new nested format
(`_meta.ui.resourceUri`) and the deprecated flat format (`_meta["ui/resourceUri"]`):

```typescript
import { getToolUiResourceUri } from "@modelcontextprotocol/ext-apps/app-bridge";

const uri = getToolUiResourceUri(tool);
if (uri) {
  // This tool has an associated UI resource
}
```

---

## 4. View Communication

### Transport Layer

All View-Host communication uses JSON-RPC 2.0 over the browser `postMessage` API.
`PostMessageTransport` implements the MCP SDK's `Transport` interface:

```typescript
export class PostMessageTransport implements Transport {
  constructor(
    private eventTarget: Window = window.parent,
    private eventSource: MessageEventSource,
  ) { /* ... */ }

  async start() { window.addEventListener("message", this.messageListener); }
  async send(message: JSONRPCMessage) { this.eventTarget.postMessage(message, "*"); }
  async close() { window.removeEventListener("message", this.messageListener); }
}
```

Security: the transport validates `event.source` against the expected source window.
Non-JSON-RPC messages are silently ignored. Malformed JSON-RPC messages trigger the
`onerror` handler.

### Protocol Messages

**View to Host requests:**

| Method | Purpose |
|---|---|
| `ui/initialize` | Handshake: app info, capabilities, protocol version |
| `tools/call` | Call a server tool (proxied through host) |
| `ui/message` | Add a message to the conversation |
| `ui/update-model-context` | Update model context for future turns |
| `ui/open-link` | Request host to open an external URL |
| `ui/request-display-mode` | Request display mode change (inline/fullscreen/pip) |

**View to Host notifications:**

| Method | Purpose |
|---|---|
| `ui/notifications/initialized` | View ready after handshake |
| `ui/notifications/size-changed` | View content size changed |
| `notifications/message` | Logging/telemetry |

**Host to View notifications:**

| Method | Purpose |
|---|---|
| `ui/notifications/tool-input` | Complete tool arguments |
| `ui/notifications/tool-input-partial` | Streaming partial arguments |
| `ui/notifications/tool-result` | Tool execution result |
| `ui/notifications/tool-cancelled` | Tool was cancelled |
| `ui/notifications/host-context-changed` | Theme, locale, dimensions changed |

**Host to View requests:**

| Method | Purpose |
|---|---|
| `ui/resource-teardown` | Request graceful shutdown |
| `ping` | Connection health check |
| `tools/call` | Call a tool provided by the View |
| `tools/list` | List tools provided by the View |

### Tool Data Delivery

The tool result supports two content fields for separation of concerns:

- `content` -- standard MCP text content, included in the model's context.
- `structuredContent` -- arbitrary structured data optimized for UI rendering, not
  included in model context.

This separation lets servers provide rich data to the UI without bloating the model's
context window. The View receives both via `ontoolresult`.

### State Sync Pattern

The `updateModelContext()` method enables Views to push state to the model without
triggering an immediate response:

```typescript
await app.updateModelContext({
  content: [{ type: "text", text: `User selected items: ${JSON.stringify(selection)}` }],
});

// Later, trigger a model response by sending a message
await app.sendMessage({
  role: "user",
  content: [{ type: "text", text: "Summarize my selections" }],
});
```

The host defers context updates until the next user message, and only sends the last
update (each call overwrites the previous one).

---

## 5. React Integration

The React integration is optional. The core SDK is framework-agnostic. React hooks are
provided for convenience.

### useApp

Creates and connects an `App` instance on mount:

```tsx
import { useApp } from "@modelcontextprotocol/ext-apps/react";

function MyApp() {
  const { app, isConnected, error } = useApp({
    appInfo: { name: "MyApp", version: "1.0.0" },
    capabilities: {},
    onAppCreated: (app) => {
      app.ontoolinput = (input) => setData(input.arguments);
      app.ontoolresult = (result) => setResult(result);
      app.ontoolcancelled = (params) => setError(params.reason);
    },
  });

  if (error) return <div>Error: {error.message}</div>;
  if (!isConnected) return <div>Connecting...</div>;
  return <Dashboard data={data} result={result} />;
}
```

Design decisions:
- Options are only used during initial mount (no reconnection on option change).
- `App` is not closed on unmount (avoids React Strict Mode double-mount issues).
- Handlers must be registered in `onAppCreated` (before `connect()`) to avoid missing
  notifications.

### useHostStyles / useHostStyleVariables / useHostFonts

Applies host-provided CSS custom properties and fonts to match the host's visual style:

```tsx
function MyApp() {
  const { app } = useApp({ appInfo, capabilities: {} });
  useHostStyles(app, app?.getHostContext());

  return (
    <div style={{ background: "var(--color-background-primary)" }}>
      Content
    </div>
  );
}
```

`useHostStyles` is a convenience that combines `useHostStyleVariables` (CSS variables +
theme via `color-scheme`) and `useHostFonts` (font CSS via `@font-face` / `@import`).
Both listen for `onhostcontextchanged` notifications and apply updates dynamically.

### useAutoResize

Rarely needed since `useApp` enables auto-resize by default (`autoResize: true`). Provided
for cases where you create `App` manually with `autoResize: false`:

```tsx
function MyComponent() {
  const [app, setApp] = useState<App | null>(null);

  useEffect(() => {
    const myApp = new App(appInfo, {}, { autoResize: false });
    myApp.connect().then(() => setApp(myApp));
  }, []);

  useAutoResize(app);
  return <div>Content</div>;
}
```

Uses `ResizeObserver` on `document.body` and `document.documentElement`. Cleans up on
unmount.

### useDocumentTheme

Provides reactive theme detection via `MutationObserver` on `document.documentElement`:

```tsx
function MyApp() {
  const theme = useDocumentTheme();
  return <div className={theme === "dark" ? "dark-theme" : "light-theme"}>...</div>;
}
```

Returns `"light"` or `"dark"`. Watches for changes to `data-theme` attribute and `class`
on the document element.

---

## 6. Framework Templates

The ext-apps repository provides starter templates for six frameworks. Each demonstrates
the same app (a color picker) built with different technologies:

| Framework | Directory | Package |
|---|---|---|
| React | `examples/basic-server-react` | `@modelcontextprotocol/server-basic-react` |
| Vue | `examples/basic-server-vue` | `@modelcontextprotocol/server-basic-vue` |
| Svelte | `examples/basic-server-svelte` | `@modelcontextprotocol/server-basic-svelte` |
| Preact | `examples/basic-server-preact` | `@modelcontextprotocol/server-basic-preact` |
| Solid | `examples/basic-server-solid` | `@modelcontextprotocol/server-basic-solid` |
| Vanilla JS | `examples/basic-server-vanillajs` | `@modelcontextprotocol/server-basic-vanillajs` |

All templates share the same server-side pattern:
1. Create `McpServer` instance.
2. Use `registerAppResource` to register the HTML (built as a single-file bundle).
3. Use `registerAppTool` with `_meta.ui.resourceUri` pointing to the resource.
4. Tool handler returns text content (for model) and optionally structured content
   (for the View).

The View code differs per framework but follows the same lifecycle:
1. Import/create `App` instance (or use framework-specific wrapper like `useApp`).
2. Register notification handlers.
3. Call `connect()`.
4. Render UI based on tool input and result.

### Full Examples

Beyond starter templates, the repository includes production-quality examples:

| Example | Description |
|---|---|
| Map | Interactive 3D globe viewer (CesiumJS) |
| Three.js | 3D scene renderer |
| ShaderToy | Real-time GLSL shader renderer |
| Sheet Music | ABC notation to sheet music |
| Wiki Explorer | Wikipedia link graph visualization |
| Cohort Heatmap | Customer retention heatmap |
| Scenario Modeler | SaaS business projections |
| Budget Allocator | Interactive budget allocation |
| Customer Segmentation | Scatter chart with clustering |
| System Monitor | Real-time OS metrics (polling pattern) |
| Transcript | Live speech transcription (microphone permission) |
| Video Resource | Binary video via MCP resources |
| PDF Server | Interactive PDF viewer (chunked loading) |
| QR Code | QR code generator (Python server) |
| Say Demo | Text-to-speech |

---

## 7. MCP UI SDK

### Overview

The `@mcp-ui/*` packages implement the MCP Apps standard with additional features:

- **Server SDKs** in TypeScript, Python, and Ruby.
- **Client SDK** with `AppRenderer` (MCP Apps) and `UIResourceRenderer` (legacy).
- **Platform adapters** (ChatGPT Apps SDK, others planned).
- **Web Component** support (`<ui-resource-renderer>`).
- **Multiple content types** beyond `text/html;profile=mcp-app`.

### createUIResource

The server-side helper that produces properly formatted UI resources:

```typescript
import { createUIResource } from "@mcp-ui/server";

const widgetUI = createUIResource({
  uri: "ui://my-server/widget",
  content: { type: "rawHtml", htmlString: "<h1>Widget</h1>" },
  encoding: "text",
});
```

Content types:

| Type | Field | Description |
|---|---|---|
| `rawHtml` | `htmlString` | Inline HTML content |
| `externalUrl` | `iframeUrl` | External URL loaded in iframe |
| `remoteDom` | `script` + `framework` | Remote DOM script with component library |

### UIResource Wire Format

```typescript
interface UIResource {
  type: "resource";
  resource: {
    uri: string;       // e.g., "ui://component/id"
    mimeType: string;  // "text/html", "text/uri-list", "application/vnd.mcp-ui.remote-dom"
    text?: string;     // Inline content
    blob?: string;     // Base64-encoded content
  };
}
```

The `mimeType` determines rendering:

- `text/html;profile=mcp-app` -- MCP Apps standard. Rendered via `AppRenderer`.
- `text/html` -- Legacy MCP-UI. Rendered via `UIResourceRenderer` in sandboxed iframe.
- `text/uri-list` -- External URL. Rendered via iframe pointing to the URL.
- `application/vnd.mcp-ui.remote-dom` -- Remote DOM. Script runs in a controlled
  environment with host-provided component library.

### AppRenderer (Client)

The recommended renderer for MCP Apps hosts:

```tsx
import { AppRenderer } from "@mcp-ui/client";

function ToolUI({ client, toolName, toolInput, toolResult }) {
  return (
    <AppRenderer
      client={client}
      toolName={toolName}
      sandbox={{ url: sandboxUrl }}
      toolInput={toolInput}
      toolResult={toolResult}
      onOpenLink={async ({ url }) => window.open(url)}
      onMessage={async (params) => console.log("Message:", params)}
    />
  );
}
```

Key props:
- `client` -- MCP client for automatic resource fetching.
- `toolName` -- triggers resource lookup via `_meta.ui.resourceUri`.
- `sandbox` -- sandbox proxy URL configuration.
- `toolInput` / `toolResult` -- forwarded to the View.
- `onOpenLink` / `onMessage` -- handlers for View requests.

### UIResourceRenderer (Legacy)

For hosts that do not yet support MCP Apps:

```tsx
import { UIResourceRenderer } from "@mcp-ui/client";

<UIResourceRenderer
  resource={mcpResource.resource}
  onUIAction={(action) => handleAction(action)}
/>
```

Also available as a Web Component:

```html
<ui-resource-renderer
  resource='{ "mimeType": "text/html", "text": "<h2>Hello</h2>" }'
></ui-resource-renderer>
```

### Python SDK

```python
from mcp_ui_server import create_ui_resource

html_resource = create_ui_resource({
    "uri": "ui://greeting/1",
    "content": { "type": "rawHtml", "htmlString": "<p>Hello from Python</p>" },
    "encoding": "text",
})
```

### Ruby SDK

```ruby
require "mcp_ui_server"

html_resource = McpUiServer.create_ui_resource(
  uri: "ui://greeting/1",
  content: { type: :raw_html, htmlString: "<p>Hello from Ruby</p>" },
  encoding: :text
)
```

---

## 8. Platform Adapters

MCP-UI includes adapter support for host-specific implementations. Adapters translate
between the MCP-UI `postMessage` protocol and host-specific APIs.

### Apps SDK Adapter (ChatGPT)

For OpenAI Apps SDK environments (e.g., ChatGPT), the adapter translates MCP-UI protocol
to Apps SDK API calls (e.g., `window.openai`):

```typescript
const htmlResource = createUIResource({
  uri: "ui://greeting/1",
  content: { type: "rawHtml", htmlString: `<button onclick="...">Call Tool</button>` },
  encoding: "text",
  adapters: {
    appsSdk: {
      enabled: true,
      config: { intentHandling: "ignore" },
    },
  },
});
```

How it works:
- Intercepts MCP-UI `postMessage` calls from widgets.
- Translates to appropriate Apps SDK API calls.
- Handles bidirectional communication (tools, prompts, state management).
- Your existing MCP-UI code works without changes.

Supported actions via the adapter:
- Tool calls (`{ type: "tool", payload: { toolName, params } }`)
- Prompts (`{ type: "prompt", payload: { prompt } }`)
- Intents (`{ type: "intent", payload: { intent, params } }`)
- Notifications (`{ type: "notify", payload: { message } }`)
- Render data access (`toolInput`, `toolOutput`, `widgetState`, `theme`, `locale`)

### Manual Adapter Wrapping

```typescript
import { wrapHtmlWithAdapters, getAppsSdkAdapterScript } from "@mcp-ui/server";

const wrappedHtml = wrapHtmlWithAdapters(
  "<button>Click me</button>",
  { appsSdk: { enabled: true, config: { intentHandling: "ignore" } } }
);
```

### Future Adapters

The adapter architecture is extensible. As hosts become compliant with the MCP Apps
specification, adapters become unnecessary. Until then, they provide a bridge for
cross-platform compatibility.

---

## 9. CSP and Security

### Sandboxing Model

All Views run in sandboxed iframes with no access to the Host's DOM, cookies, or storage.
Communication happens only through `postMessage`, making it auditable.

The iframe sandbox attribute provides isolation:
- `allow-scripts` -- JavaScript execution permitted.
- `allow-same-origin` -- Required for the sandbox proxy architecture.
- No `allow-top-navigation`, `allow-popups` (without user activation), or
  `allow-forms` by default.

### Content Security Policy

Servers declare required network domains via the `_meta.ui.csp` object:

```typescript
interface McpUiResourceCsp {
  connectDomains?: string[];    // fetch/XHR/WebSocket (maps to connect-src)
  resourceDomains?: string[];   // scripts/styles/images/fonts (maps to script-src, etc.)
  frameDomains?: string[];      // nested iframes (maps to frame-src)
  baseUriDomains?: string[];    // base URI (maps to base-uri)
}
```

### Restrictive Default

If `ui.csp` is omitted, hosts enforce:

```
default-src 'none';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
media-src 'self' data:;
connect-src 'none';
```

This means no external network connections by default. Servers must explicitly declare
every external domain their UI needs.

### Host Behavior Rules

- Host MUST construct CSP headers based on declared domains.
- Host MUST NOT allow undeclared domains (may further restrict).
- Host SHOULD log CSP configurations for security review.
- Host SHOULD audit trail all `postMessage` communication.

### Sandbox Proxy (Web Hosts)

Web-based hosts must use a double-iframe architecture:

1. Outer iframe (sandbox proxy) -- same origin isolation from host.
2. Inner iframe (View) -- loads the actual HTML with CSP enforcement.

Protocol:
1. Sandbox proxy sends `ui/notifications/sandbox-proxy-ready` when ready.
2. Host sends `ui/notifications/sandbox-resource-ready` with HTML content and sandbox
   attributes.
3. Sandbox proxy loads the HTML into the inner iframe with CSP headers.

This prevents the View from accessing the Host's DOM, cookies, or origin, even if
`allow-same-origin` is set on the inner iframe.

### Permissions

Resources can request browser capabilities via `_meta.ui.permissions`:

```typescript
permissions: {
  camera: {},          // Permission Policy: camera
  microphone: {},      // Permission Policy: microphone
  geolocation: {},     // Permission Policy: geolocation
  clipboardWrite: {},  // Permission Policy: clipboard-write
}
```

The `buildAllowAttribute()` helper converts these to iframe `allow` attribute format:

```typescript
const allow = buildAllowAttribute({ microphone: {}, clipboardWrite: {} });
// Returns: "microphone; clipboard-write"
```

### Dedicated Domains

For OAuth callbacks, CORS policies, or API key allowlists, Views can request a stable
origin via `_meta.ui.domain`:

```typescript
_meta: {
  ui: {
    domain: "a904794854a047f6.claudemcpcontent.com",
    csp: {
      connectDomains: ["https://api.example.com"],
    },
  },
}
```

The format is host-specific. Claude uses hash-based subdomains of
`claudemcpcontent.com`. OpenAI uses URL-derived subdomains of `oaiusercontent.com`.

---

## 10. Bundling

### Vite Single-File Strategy

MCP Apps require the entire View to be served as a single HTML document (since it is
loaded via `resources/read`, not from a web server). The standard approach is Vite with
`vite-plugin-singlefile`:

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    sourcemap: process.env.NODE_ENV === "development" ? "inline" : undefined,
    cssMinify: process.env.NODE_ENV !== "development",
    minify: process.env.NODE_ENV !== "development",
    rollupOptions: {
      input: "mcp-app.html",
    },
    outDir: "dist",
    emptyOutDir: false,
  },
});
```

This produces a single `.html` file with all JavaScript, CSS, and assets inlined.

### Server Build

For the server (which registers tools and serves the bundled HTML), use esbuild to
produce a single CJS bundle:

```javascript
// build-server.mjs
import { build } from "esbuild";
import module from "node:module";

const builtins = module.builtinModules.flatMap((m) => [m, `node:${m}`]);

await build({
  entryPoints: ["main.ts"],
  outfile: "dist/index.cjs",
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node20",
  external: builtins,
  banner: { js: "#!/usr/bin/env node" },
  define: {
    "import.meta.dirname": "__dirname",
    "import.meta.filename": "__filename",
  },
});
```

### Build Pipeline

Typical build sequence (as seen in the mece-decomposer):

```json
{
  "scripts": {
    "build": "tsc --noEmit && cross-env INPUT=mcp-app.html vite build && tsc -p tsconfig.server.json && node build-server.mjs"
  }
}
```

Steps:
1. Type-check with `tsc --noEmit`.
2. Build the View HTML with Vite (single-file output).
3. Compile server TypeScript.
4. Bundle server with esbuild (all npm deps inlined, only Node.js builtins external).

The result is a single `dist/index.cjs` that can be run with `node dist/index.cjs --stdio`
-- no `node_modules` needed at runtime.

---

## 11. Testing Patterns

### Local Development with basic-host

The ext-apps repository includes a reference host implementation (`examples/basic-host`)
for local testing:

```bash
git clone https://github.com/modelcontextprotocol/ext-apps.git
cd ext-apps && npm install
SERVERS='["http://localhost:3001/mcp"]' npm start
```

Open http://localhost:8080. Select your server, select a tool, enter JSON input, and click
"Call Tool" to see the View render. Debugging panels show tool input, tool result,
messages, and model context.

### Testing with MCP Clients

Configure your MCP server in Claude Desktop, VS Code, or other MCP Apps hosts. For stdio
transport:

```json
{
  "mcpServers": {
    "my-app": {
      "command": "node",
      "args": ["dist/index.cjs", "--stdio"]
    }
  }
}
```

### Exposing Local Servers

For remote hosts (e.g., claude.ai), use `cloudflared` to tunnel:

```bash
npx cloudflared tunnel --url http://localhost:3001
```

### E2E Testing

The ext-apps repository uses Playwright for end-to-end tests (`npm run test:e2e`).
These start the examples server automatically and test View rendering, initialization
handshake, tool data flow, and communication protocol.

### Development Watch Mode

For iterative development, use concurrent watch processes:

```json
{
  "scripts": {
    "watch": "cross-env INPUT=mcp-app.html vite build --watch",
    "serve": "tsx --watch main.ts",
    "dev": "concurrently \"npm run watch\" \"npm run serve\""
  }
}
```

### MCP Inspector

The MCP UI project provides `ui-inspector` -- a local tool for inspecting MCP-UI-enabled
servers without a full host implementation.

---

## 12. Host Compatibility Matrix

### MCP Apps Hosts

These hosts implement the MCP Apps specification and support `_meta.ui.resourceUri`:

| Host | Status |
|---|---|
| Claude (claude.ai) | Supported |
| VS Code (Insiders) | Supported |
| Postman | Supported |
| Goose | Supported |
| MCPJam | Supported |
| LibreChat | Supported |
| mcp-use | Supported |
| Smithery | Supported |

### Legacy MCP-UI Hosts

These hosts expect UI resources embedded directly in tool responses (pre-specification
pattern):

| Host | Rendering | UI Actions |
|---|---|---|
| Nanobot | Full | Full |
| MCPJam | Full | Full |
| Postman | Full | Partial |
| Goose | Full | Partial |
| LibreChat | Full | Partial |
| Smithery | Full | None |
| fast-agent | Full | None |

### Hosts Requiring Adapters

| Host | Protocol | Notes |
|---|---|---|
| ChatGPT | Apps SDK | Requires `appsSdk` adapter from `@mcp-ui/server` |

### Feature Support

Not all features are available in all hosts. Key differences:

- **Display modes** -- fullscreen/pip may not be available in all hosts.
- **Streaming partial input** -- depends on host streaming capability.
- **Server tool calls** -- requires host to proxy; some hosts may restrict.
- **Message sending** -- requires host conversation integration.
- **Model context updates** -- requires host context management.
- **Permissions** (camera, microphone, etc.) -- host-dependent.
- **CSP enforcement** -- varies by host implementation.
- **Dedicated domains** -- format is host-specific.

---

## 13. Graceful Degradation

### Design Principle

MCP Apps is designed as a progressive enhancement. UI is optional; tools must work without
it. This is the fundamental contract: your server works everywhere, and hosts that support
UI get a richer experience.

### Capability Negotiation

Servers check host capabilities before registering UI-enhanced tools:

```typescript
import { getUiCapability, RESOURCE_MIME_TYPE }
  from "@modelcontextprotocol/ext-apps/server";

server.server.oninitialized = () => {
  const clientCapabilities = server.server.getClientCapabilities();
  const uiCap = getUiCapability(clientCapabilities);

  if (uiCap?.mimeTypes?.includes(RESOURCE_MIME_TYPE)) {
    // Register UI-enhanced tool
    registerAppTool(server, "weather", {
      description: "Interactive weather dashboard",
      _meta: { ui: { resourceUri: "ui://weather/dashboard" } },
    }, weatherHandler);
  } else {
    // Register text-only fallback
    server.registerTool("weather", {
      description: "Get weather information",
    }, textWeatherHandler);
  }
};
```

The extension identifier for capability negotiation is `io.modelcontextprotocol/ui`.

### Text Fallback

Even without capability negotiation, tools with `_meta.ui.resourceUri` still work in
non-UI hosts. The `_meta` field is ignored by hosts that do not understand it, and the
tool's text `content` is displayed as-is. The structured `structuredContent` field is
simply not rendered.

This means a single tool registration can serve both UI and text-only hosts:

```typescript
registerAppTool(server, "get-weather", {
  description: "Get weather",
  _meta: { ui: { resourceUri: "ui://weather/view.html" } },
}, async (args) => {
  const weather = await fetchWeather(args.location);
  return {
    // Text content -- always available, used by model and non-UI hosts
    content: [{ type: "text", text: formatWeatherText(weather) }],
    // Structured content -- used by UI View, ignored by non-UI hosts
    structuredContent: { type: "weather", data: weather },
  };
});
```

---

## 14. Real Implementation Analysis

### mece-decomposer MCP App

The mece-decomposer plugin in this repository provides a real-world case study of an MCP
App implementation.

**Location:** `mece-decomposer/mcp-app/`

**Architecture:**

- **Server** (`server.ts`): Creates `McpServer`, registers three tools (`mece-decompose`,
  `mece-validate`, `mece-refine-node`) and one UI resource (`ui://mece/mcp-app.html`).
- **View** (`src/`): React application using `@modelcontextprotocol/ext-apps` hooks.
- **Entry point** (`main.ts`): Supports both stdio and HTTP (StreamableHTTP) transports.
- **Bundle** (`build-server.mjs`): esbuild bundles everything into `dist/index.cjs`.

**Tool Registration Pattern:**

```typescript
const resourceUri = "ui://mece/mcp-app.html";

// Tool 1: Model + App visible
registerAppTool(server, "mece-decompose", {
  title: "MECE Decompose",
  description: "Accept a MECE decomposition JSON and render it as an interactive tree",
  inputSchema: { decomposition: z.string() },
  _meta: { ui: { resourceUri } },
}, async (params) => {
  const parsed = JSON.parse(params.decomposition);
  return {
    structuredContent: { type: "decomposition", decomposition: parsed },
    content: [{ type: "text", text: `Decomposition loaded: "${parsed.metadata.scope}"` }],
  };
});

// Tool 3: App-only (hidden from model)
registerAppTool(server, "mece-refine-node", {
  inputSchema: { nodeId: z.string(), instruction: z.string() },
  _meta: { ui: { resourceUri, visibility: ["app"] } },
}, async (params) => { /* ... */ });
```

**Deployment via .mcp.json:**

```json
{
  "mcpServers": {
    "mece-decomposer": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-app/dist/index.cjs", "--stdio"]
    }
  }
}
```

This is the auto-configuration pattern for Claude Code plugins. When installed, the plugin
starts the MCP server automatically.

**Build Configuration:**

The Vite config uses `vite-plugin-singlefile` with the `INPUT` environment variable
pointing to the HTML entry point. The server build uses esbuild to produce a fully
self-contained CJS bundle.

**Key Patterns Used:**

1. **structuredContent separation** -- decomposition data goes to the View;
   summary text goes to the model.
2. **App-only tools** -- `mece-refine-node` is callable only by the View for interactive
   node editing.
3. **Graceful degradation** -- the validate tool falls back to basic JSON parsing if `uv`
   is unavailable.
4. **Dual transport** -- supports stdio (for Claude Code plugins) and HTTP (for remote
   hosts and local development).

---

## 15. Cross-References

### Related Documents in This Repository

- `docs/claude-docs/claude_docs_mcp.md` -- Claude Code's MCP integration documentation.
  Covers server installation (stdio, HTTP, SSE), configuration, and management commands.

- `mcp-apps/references/specification.mdx` -- the full MCP Apps specification
  (SEP-1865, stable 2026-01-26). Defines UI resource format, tool-UI linkage, communication
  protocol, security model, host context, theming, and display modes.

- `mcp-apps/references/overview.md` -- high-level overview of MCP Apps architecture,
  lifecycle, and concepts.

- `mcp-apps/references/patterns.md` -- common patterns: app-only tools, polling for live
  data, progressive rendering with partial tool input.

- `mcp-apps/references/testing.md` -- testing approaches: basic-host, MCP clients,
  cloudflared tunnels.

- `mcp-apps/references/migrate_from_openai_apps.md` -- migration guide from OpenAI Apps
  SDK to MCP Apps SDK.

### External References

- [MCP Apps Specification (SEP-1865)](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [MCP Apps SDK Repository](https://github.com/modelcontextprotocol/ext-apps)
- [MCP Apps API Documentation](https://modelcontextprotocol.github.io/ext-apps/api/)
- [MCP-UI Repository](https://github.com/idosal/mcp-ui)
- [MCP-UI Documentation](https://mcpui.dev/)
- [SEP-1865 Discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1865)
- [Agent Skills Specification](https://agentskills.io/)

### Source Code References (Local)

- `coderef/ext-apps/` -- MCP Apps SDK source (symlink to local clone)
- `coderef/mcp-ui/` -- MCP UI SDK source (symlink to local clone)
- `mcp-apps/` -- MCP Apps plugin (skills, references)
- `mece-decomposer/mcp-app/` -- Real MCP App implementation

---

## Appendix A: Quick Reference -- Server-Side Registration

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import {
  registerAppTool,
  registerAppResource,
  RESOURCE_MIME_TYPE,
  getUiCapability,
} from "@modelcontextprotocol/ext-apps/server";
import { createUIResource } from "@mcp-ui/server";
import { z } from "zod";
import fs from "node:fs/promises";

const server = new McpServer({ name: "my-server", version: "1.0.0" });

// Option A: Read pre-built HTML from dist/
registerAppResource(server, "My View", "ui://my-server/view.html", {
  description: "Interactive view",
}, async () => ({
  contents: [{
    uri: "ui://my-server/view.html",
    mimeType: RESOURCE_MIME_TYPE,
    text: await fs.readFile("dist/view.html", "utf-8"),
  }],
}));

// Option B: Use createUIResource from @mcp-ui/server
const viewUI = createUIResource({
  uri: "ui://my-server/view",
  content: { type: "rawHtml", htmlString: "<h1>Hello</h1>" },
  encoding: "text",
});

registerAppResource(server, "My View", viewUI.resource.uri, {},
  async () => ({ contents: [viewUI.resource] }));

// Register tool
registerAppTool(server, "show-view", {
  description: "Show interactive view",
  inputSchema: { query: z.string() },
  _meta: { ui: { resourceUri: "ui://my-server/view.html" } },
}, async ({ query }) => ({
  content: [{ type: "text", text: `Query: ${query}` }],
  structuredContent: { type: "result", query },
}));
```

## Appendix B: Quick Reference -- View-Side (React)

```tsx
import { useApp, useHostStyles } from "@modelcontextprotocol/ext-apps/react";
import { useState } from "react";

function MyView() {
  const [data, setData] = useState(null);
  const [result, setResult] = useState(null);

  const { app, isConnected, error } = useApp({
    appInfo: { name: "MyView", version: "1.0.0" },
    capabilities: {},
    onAppCreated: (app) => {
      app.ontoolinput = (params) => setData(params.arguments);
      app.ontoolresult = (params) => setResult(params);
      app.ontoolcancelled = (params) => console.log("Cancelled:", params.reason);
    },
  });

  useHostStyles(app, app?.getHostContext());

  if (error) return <div>Error: {error.message}</div>;
  if (!isConnected) return <div>Connecting...</div>;

  return (
    <div style={{ background: "var(--color-background-primary)" }}>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
      {result && <p>Result received</p>}
      <button onClick={() => app?.callServerTool({
        name: "refresh",
        arguments: {},
      })}>
        Refresh
      </button>
    </div>
  );
}
```

## Appendix C: Quick Reference -- View-Side (Vanilla JS)

```html
<!DOCTYPE html>
<html>
<head>
  <script type="module">
    import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";

    const app = new App({ name: "MyView", version: "1.0.0" }, {});

    app.ontoolinput = (params) => {
      document.getElementById("output").textContent =
        JSON.stringify(params.arguments, null, 2);
    };

    app.ontoolresult = (params) => {
      document.getElementById("result").textContent =
        JSON.stringify(params.content, null, 2);
    };

    app.onhostcontextchanged = (ctx) => {
      if (ctx.theme === "dark") {
        document.body.classList.add("dark");
      } else {
        document.body.classList.remove("dark");
      }
    };

    await app.connect(new PostMessageTransport(window.parent, window.parent));
  </script>
</head>
<body>
  <pre id="output">Waiting for tool input...</pre>
  <pre id="result"></pre>
</body>
</html>
```
