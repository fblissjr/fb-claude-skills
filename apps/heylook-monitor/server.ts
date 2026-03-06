import {
  RESOURCE_MIME_TYPE,
  registerAppResource,
  registerAppTool,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type {
  CallToolResult,
  ReadResourceResult,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "node:fs/promises";
import path from "node:path";
import { z } from "zod";

// Works both from source (server.ts) and compiled (dist/server.js)
const DIST_DIR = import.meta.filename.endsWith(".ts")
  ? path.join(import.meta.dirname, "dist")
  : import.meta.dirname;

const BASE_URL = process.env.HEYLOOK_URL ?? "http://localhost:8080";

// =============================================================================
// Upstream API helpers
// =============================================================================

async function fetchApi<T>(endpoint: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// =============================================================================
// Types
// =============================================================================

interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}

interface ModelsResponse {
  data: Model[];
}

interface SystemMetrics {
  ram_total_gb: number;
  ram_used_gb: number;
  ram_available_gb: number;
  ram_percent: number;
  cpu_percent: number;
  models: Record<
    string,
    {
      memory_mb: number;
      context_window: number;
      context_used: number;
    }
  >;
}

interface PerformanceData {
  models: Record<
    string,
    {
      tokens_per_second: number;
      peak_tps: number;
      error_rate: number;
      time_to_first_token_ms: number;
      active_requests: number;
    }
  >;
}

interface Capabilities {
  backends: string[];
  features: string[];
  gpu: {
    name: string;
    memory_gb: number;
  } | null;
}

// =============================================================================
// Output schemas for structured content
// =============================================================================

const DashboardOutputSchema = z.object({
  connected: z.boolean(),
  models: z.array(
    z.object({
      id: z.string(),
      owned_by: z.string(),
    }),
  ),
  system: z
    .object({
      ram_total_gb: z.number(),
      ram_used_gb: z.number(),
      ram_percent: z.number(),
      cpu_percent: z.number(),
    })
    .nullable(),
  performance: z
    .record(
      z.string(),
      z.object({
        tokens_per_second: z.number(),
        peak_tps: z.number(),
        error_rate: z.number(),
        time_to_first_token_ms: z.number(),
        active_requests: z.number(),
      }),
    )
    .nullable(),
  capabilities: z
    .object({
      backends: z.array(z.string()),
      features: z.array(z.string()),
      gpu: z
        .object({
          name: z.string(),
          memory_gb: z.number(),
        })
        .nullable(),
    })
    .nullable(),
  timestamp: z.string(),
});

const PollOutputSchema = z.object({
  connected: z.boolean(),
  models: z
    .array(
      z.object({
        id: z.string(),
        owned_by: z.string(),
      }),
    )
    .nullable(),
  system: z
    .object({
      ram_total_gb: z.number(),
      ram_used_gb: z.number(),
      ram_percent: z.number(),
      cpu_percent: z.number(),
    })
    .nullable(),
  performance: z
    .record(
      z.string(),
      z.object({
        tokens_per_second: z.number(),
        peak_tps: z.number(),
        error_rate: z.number(),
        time_to_first_token_ms: z.number(),
        active_requests: z.number(),
      }),
    )
    .nullable(),
  model_metrics: z
    .record(
      z.string(),
      z.object({
        memory_mb: z.number(),
        context_window: z.number(),
        context_used: z.number(),
      }),
    )
    .nullable(),
  timestamp: z.string(),
});

const InferenceInputSchema = z.object({
  model: z.string(),
  prompt: z.string(),
  max_tokens: z.number().optional(),
});

const InferenceOutputSchema = z.object({
  model: z.string(),
  response: z.string(),
  tokens: z.number(),
  latency_ms: z.number(),
});

const ModelsOutputSchema = z.object({
  models: z.array(
    z.object({
      id: z.string(),
      owned_by: z.string(),
    }),
  ),
  count: z.number(),
});

// =============================================================================
// MCP Server
// =============================================================================

export function createServer(): McpServer {
  const server = new McpServer({
    name: "heylook-monitor",
    version: "1.0.0",
  });

  const resourceUri = "ui://heylook-monitor/mcp-app.html";

  // -------------------------------------------------------------------------
  // show_llm_dashboard: model + app visible, opens the dashboard
  // -------------------------------------------------------------------------
  registerAppTool(
    server,
    "show_llm_dashboard",
    {
      title: "Show LLM Dashboard",
      description:
        "Opens a live dashboard showing local LLM server status: loaded models, system metrics (RAM/CPU), per-model performance (TPS, latency), and server capabilities.",
      inputSchema: {},
      outputSchema: DashboardOutputSchema.shape,
      _meta: { ui: { resourceUri } },
    },
    async (): Promise<CallToolResult> => {
      const [modelsRes, metrics, perf, caps] = await Promise.allSettled([
        fetchApi<ModelsResponse>("/v1/models"),
        fetchApi<SystemMetrics>("/v1/system/metrics"),
        fetchApi<PerformanceData>("/v1/performance"),
        fetchApi<Capabilities>("/v1/capabilities"),
      ]);

      const models =
        modelsRes.status === "fulfilled" && modelsRes.value
          ? modelsRes.value.data
          : [];
      const systemMetrics =
        metrics.status === "fulfilled" ? metrics.value : null;
      const performance = perf.status === "fulfilled" ? perf.value : null;
      const capabilities = caps.status === "fulfilled" ? caps.value : null;
      const connected = models.length > 0 || systemMetrics !== null;

      const data = {
        connected,
        models: models.map((m) => ({ id: m.id, owned_by: m.owned_by })),
        system: systemMetrics
          ? {
              ram_total_gb: systemMetrics.ram_total_gb,
              ram_used_gb: systemMetrics.ram_used_gb,
              ram_percent: systemMetrics.ram_percent,
              cpu_percent: systemMetrics.cpu_percent,
            }
          : null,
        performance: performance?.models ?? null,
        capabilities,
        timestamp: new Date().toISOString(),
      };

      // Text summary for model context
      const lines: string[] = [];
      if (connected) {
        lines.push(`LLM server at ${BASE_URL} is online.`);
        lines.push(`Models loaded: ${models.map((m) => m.id).join(", ") || "none"}`);
        if (systemMetrics) {
          lines.push(
            `RAM: ${systemMetrics.ram_used_gb.toFixed(1)}/${systemMetrics.ram_total_gb.toFixed(1)} GB (${systemMetrics.ram_percent}%)`,
          );
          lines.push(`CPU: ${systemMetrics.cpu_percent}%`);
        }
        if (performance) {
          for (const [model, stats] of Object.entries(performance.models)) {
            lines.push(
              `${model}: ${stats.tokens_per_second.toFixed(1)} tok/s (peak ${stats.peak_tps.toFixed(1)})`,
            );
          }
        }
        if (capabilities?.gpu) {
          lines.push(
            `GPU: ${capabilities.gpu.name} (${capabilities.gpu.memory_gb} GB)`,
          );
        }
      } else {
        lines.push(`LLM server at ${BASE_URL} is not reachable.`);
      }

      return {
        content: [{ type: "text", text: lines.join("\n") }],
        structuredContent: data,
      };
    },
  );

  // -------------------------------------------------------------------------
  // poll_status: app-only, lightweight polling for real-time updates
  // -------------------------------------------------------------------------
  registerAppTool(
    server,
    "poll_status",
    {
      title: "Poll Status",
      description:
        "Lightweight polling endpoint for the dashboard UI. Returns models, system metrics, and performance data. App-only.",
      inputSchema: {},
      outputSchema: PollOutputSchema.shape,
      _meta: { ui: { visibility: ["app"] } },
    },
    async (): Promise<CallToolResult> => {
      const [modelsRes, metrics, perf] = await Promise.allSettled([
        fetchApi<ModelsResponse>("/v1/models"),
        fetchApi<SystemMetrics>("/v1/system/metrics"),
        fetchApi<PerformanceData>("/v1/performance"),
      ]);

      const models =
        modelsRes.status === "fulfilled" && modelsRes.value
          ? modelsRes.value.data
          : null;
      const systemMetrics =
        metrics.status === "fulfilled" ? metrics.value : null;
      const performance = perf.status === "fulfilled" ? perf.value : null;
      const connected = models !== null || systemMetrics !== null;

      const data = {
        connected,
        models: models
          ? models.map((m) => ({ id: m.id, owned_by: m.owned_by }))
          : null,
        system: systemMetrics
          ? {
              ram_total_gb: systemMetrics.ram_total_gb,
              ram_used_gb: systemMetrics.ram_used_gb,
              ram_percent: systemMetrics.ram_percent,
              cpu_percent: systemMetrics.cpu_percent,
            }
          : null,
        performance: performance?.models ?? null,
        model_metrics: systemMetrics?.models ?? null,
        timestamp: new Date().toISOString(),
      };

      return {
        content: [{ type: "text", text: JSON.stringify(data) }],
        structuredContent: data,
      };
    },
  );

  // -------------------------------------------------------------------------
  // quick_inference: model + app visible, test prompt against local model
  // -------------------------------------------------------------------------
  registerAppTool(
    server,
    "quick_inference",
    {
      title: "Quick Inference",
      description:
        "Send a test prompt to a locally loaded model via the OpenAI-compatible chat completions API. Returns the response text, token count, and latency.",
      inputSchema: InferenceInputSchema.shape,
      outputSchema: InferenceOutputSchema.shape,
      _meta: { ui: { resourceUri } },
    },
    async (_args: Record<string, unknown>): Promise<CallToolResult> => {
      const parsed = InferenceInputSchema.parse(_args);
      const start = Date.now();

      try {
        const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: parsed.model,
            messages: [{ role: "user", content: parsed.prompt }],
            max_tokens: parsed.max_tokens ?? 256,
            stream: false,
          }),
        });

        if (!res.ok) {
          const errText = await res.text();
          return {
            content: [
              {
                type: "text",
                text: `Inference failed (${res.status}): ${errText}`,
              },
            ],
            isError: true,
          };
        }

        const body = (await res.json()) as {
          choices: Array<{ message: { content: string } }>;
          usage?: { completion_tokens: number };
        };

        const latency = Date.now() - start;
        const responseText = body.choices?.[0]?.message?.content ?? "";
        const tokens = body.usage?.completion_tokens ?? 0;

        const data = {
          model: parsed.model,
          response: responseText,
          tokens,
          latency_ms: latency,
        };

        return {
          content: [
            {
              type: "text",
              text: `${parsed.model} responded (${tokens} tokens, ${latency}ms):\n${responseText}`,
            },
          ],
          structuredContent: data,
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text",
              text: `Inference error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    },
  );

  // -------------------------------------------------------------------------
  // list_local_models: model + app visible
  // -------------------------------------------------------------------------
  registerAppTool(
    server,
    "list_local_models",
    {
      title: "List Local Models",
      description:
        "List all models currently available on the local LLM server with their providers.",
      inputSchema: {},
      outputSchema: ModelsOutputSchema.shape,
      _meta: { ui: { resourceUri } },
    },
    async (): Promise<CallToolResult> => {
      const modelsRes = await fetchApi<ModelsResponse>("/v1/models");

      if (!modelsRes || !modelsRes.data) {
        return {
          content: [
            {
              type: "text",
              text: `Could not reach LLM server at ${BASE_URL}`,
            },
          ],
          isError: true,
        };
      }

      const models = modelsRes.data.map((m) => ({
        id: m.id,
        owned_by: m.owned_by,
      }));

      const data = { models, count: models.length };

      const lines = models.map((m) => `- ${m.id} (${m.owned_by})`);
      const text =
        models.length > 0
          ? `${models.length} model(s) available:\n${lines.join("\n")}`
          : "No models currently loaded.";

      return {
        content: [{ type: "text", text }],
        structuredContent: data,
      };
    },
  );

  // -------------------------------------------------------------------------
  // Resource: dashboard HTML
  // -------------------------------------------------------------------------
  registerAppResource(
    server,
    resourceUri,
    resourceUri,
    { mimeType: RESOURCE_MIME_TYPE, description: "heylook-monitor Dashboard" },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, "mcp-app.html"),
        "utf-8",
      );

      return {
        contents: [
          {
            uri: resourceUri,
            mimeType: RESOURCE_MIME_TYPE,
            text: html,
          },
        ],
      };
    },
  );

  return server;
}
