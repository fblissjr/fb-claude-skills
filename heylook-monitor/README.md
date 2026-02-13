last updated: 2026-02-13

# heylook-monitor

MCP App dashboard for [heylookitsanllm](https://github.com/fblissjr/heylookitsanllm) -- a local LLM server

Renders a live monitoring dashboard inside Claude Desktop (or any MCP-capable host) showing loaded models, system metrics, per-model performance, and a quick inference panel.

## architecture

```
                  heylookitsanllm
                  (localhost:8080)
                       ^
                       | fetch (server-side)
                       |
  MCP Server (server.ts) ---- tools/call ----> Host (Claude Desktop)
       |                                            |
       | registerAppResource                        | iframe
       |                                            v
       +--- ui://heylook-monitor/dashboard --> Dashboard UI
                                               (mcp-app.html)
```

The MCP server proxies all API calls to heylookitsanllm. The UI never hits localhost directly (avoids CSP issues in the sandboxed iframe).

## tools

| Tool | Visibility | Description |
|------|-----------|-------------|
| `show_llm_dashboard` | model + app | Opens dashboard. Fetches models, metrics, performance, capabilities in parallel. |
| `poll_status` | app only | Lightweight polling (5s interval). Returns models, metrics, performance. |
| `quick_inference` | model + app | Send a test prompt to a local model. Returns response, token count, latency. |
| `list_local_models` | model + app | List available models with providers. |

## setup

### prerequisites

- [heylookitsanllm](https://github.com/fblissjr/heylookitsanllm) running (default: `http://localhost:8080`)
- Node.js 18+

### build

```bash
cd heylook-monitor
npm install
npm run build
```

### run (HTTP transport)

```bash
npm run serve
# MCP server listening on http://localhost:3001/mcp
```

### run (stdio transport for Claude Desktop)

Add to Claude Desktop settings (`~/.claude/settings.json` or via UI):

```json
{
  "mcpServers": {
    "heylook-monitor": {
      "command": "npx",
      "args": ["tsx", "/path/to/heylook-monitor/main.ts", "--stdio"],
      "env": {
        "HEYLOOK_URL": "http://localhost:8080"
      }
    }
  }
}
```

Then ask Claude: "show me the LLM server dashboard"

### test with basic-host

```bash
cd coderef/ext-apps/examples/basic-host
SERVERS='["http://localhost:3001/mcp"]' npm start
```

Open http://localhost:8080, select heylook-monitor, call `show_llm_dashboard`.

## configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `HEYLOOK_URL` | `http://localhost:8080` | heylookitsanllm server URL |
| `PORT` | `3001` | HTTP transport listening port |

## development

```bash
npm run dev    # concurrent vite watch + HTTP server
npm run watch  # vite watch only
```

## dashboard features

- **System metrics** -- RAM/CPU usage bars with percentage and detail
- **Model cards** -- per-model TPS, peak TPS, TTFT, active requests, memory, context window usage
- **Quick inference** -- model selector, prompt input, response display with token count and latency
- **Auto-polling** -- 5-second refresh with connection status indicator
- **Graceful degradation** -- shows disconnected state when server is unreachable, resumes on reconnect
- **Light/dark theme** -- follows system preference via CSS custom properties
