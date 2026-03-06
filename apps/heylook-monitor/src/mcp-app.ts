/**
 * @file heylook-monitor -- live dashboard for heylookitsanllm
 */
import { App, type McpUiHostContext } from "@modelcontextprotocol/ext-apps";
import "./global.css";
import "./mcp-app.css";

// =============================================================================
// Types (mirrors server.ts structured content)
// =============================================================================

interface DashboardData {
  connected: boolean;
  models: Array<{ id: string; owned_by: string }>;
  system: {
    ram_total_gb: number;
    ram_used_gb: number;
    ram_percent: number;
    cpu_percent: number;
  } | null;
  performance: Record<
    string,
    {
      tokens_per_second: number;
      peak_tps: number;
      error_rate: number;
      time_to_first_token_ms: number;
      active_requests: number;
    }
  > | null;
  capabilities: {
    backends: string[];
    features: string[];
    gpu: { name: string; memory_gb: number } | null;
  } | null;
  timestamp: string;
}

interface PollData {
  connected: boolean;
  models: Array<{ id: string; owned_by: string }> | null;
  system: {
    ram_total_gb: number;
    ram_used_gb: number;
    ram_percent: number;
    cpu_percent: number;
  } | null;
  performance: Record<
    string,
    {
      tokens_per_second: number;
      peak_tps: number;
      error_rate: number;
      time_to_first_token_ms: number;
      active_requests: number;
    }
  > | null;
  model_metrics: Record<
    string,
    {
      memory_mb: number;
      context_window: number;
      context_used: number;
    }
  > | null;
  timestamp: string;
}

interface InferenceResult {
  model: string;
  response: string;
  tokens: number;
  latency_ms: number;
}

interface AppState {
  connected: boolean;
  models: Array<{ id: string; owned_by: string }>;
  capabilities: DashboardData["capabilities"];
  intervalId: number | null;
}

// =============================================================================
// DOM References
// =============================================================================

const mainEl = document.querySelector(".main") as HTMLElement;
const statusIndicator = document.getElementById("status-indicator")!;
const statusText = document.getElementById("status-text")!;
const ramBarFill = document.getElementById("ram-bar-fill")!;
const ramPercent = document.getElementById("ram-percent")!;
const ramDetail = document.getElementById("ram-detail")!;
const cpuBarFill = document.getElementById("cpu-bar-fill")!;
const cpuPercent = document.getElementById("cpu-percent")!;
const gpuInfo = document.getElementById("gpu-info")!;
const modelCardsEl = document.getElementById("model-cards")!;
const noModelsEl = document.getElementById("no-models")!;
const inferenceModel = document.getElementById(
  "inference-model",
) as HTMLSelectElement;
const inferencePrompt = document.getElementById(
  "inference-prompt",
) as HTMLTextAreaElement;
const inferenceRun = document.getElementById(
  "inference-run",
) as HTMLButtonElement;
const inferenceStatusEl = document.getElementById("inference-status")!;
const inferenceResultEl = document.getElementById("inference-result")!;
const inferenceResponseEl = document.getElementById("inference-response")!;
const inferenceMetaEl = document.getElementById("inference-meta")!;

// =============================================================================
// Constants & State
// =============================================================================

const POLL_INTERVAL = 5000;

const state: AppState = {
  connected: false,
  models: [],
  capabilities: null,
  intervalId: null,
};

// =============================================================================
// Formatting
// =============================================================================

function formatGb(gb: number): string {
  return `${gb.toFixed(1)} GB`;
}

// =============================================================================
// Safe DOM helpers
// =============================================================================

function el(
  tag: string,
  attrs?: Record<string, string>,
  ...children: (Node | string)[]
): HTMLElement {
  const e = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      e.setAttribute(k, v);
    }
  }
  for (const child of children) {
    if (typeof child === "string") {
      e.appendChild(document.createTextNode(child));
    } else {
      e.appendChild(child);
    }
  }
  return e;
}

// =============================================================================
// UI Updates
// =============================================================================

function updateConnectionStatus(connected: boolean): void {
  state.connected = connected;
  statusIndicator.classList.remove("connected", "disconnected");
  if (connected) {
    statusIndicator.classList.add("connected");
    statusText.textContent = new Date().toLocaleTimeString("en-US", {
      hour12: false,
    });
  } else {
    statusIndicator.classList.add("disconnected");
    statusText.textContent = "Offline";
  }
}

function updateSystemMetrics(system: DashboardData["system"]): void {
  if (!system) return;

  // RAM bar
  ramBarFill.style.width = `${system.ram_percent}%`;
  ramBarFill.classList.remove("warning", "danger");
  if (system.ram_percent >= 80) {
    ramBarFill.classList.add("danger");
  } else if (system.ram_percent >= 60) {
    ramBarFill.classList.add("warning");
  }
  ramPercent.textContent = `${system.ram_percent}%`;
  ramDetail.textContent = `${formatGb(system.ram_used_gb)} / ${formatGb(system.ram_total_gb)}`;

  // CPU bar
  cpuBarFill.style.width = `${system.cpu_percent}%`;
  cpuBarFill.classList.remove("warning", "danger");
  if (system.cpu_percent >= 80) {
    cpuBarFill.classList.add("danger");
  } else if (system.cpu_percent >= 60) {
    cpuBarFill.classList.add("warning");
  }
  cpuPercent.textContent = `${system.cpu_percent}%`;
}

function updateGpuInfo(capabilities: DashboardData["capabilities"]): void {
  if (capabilities?.gpu) {
    gpuInfo.textContent = `GPU: ${capabilities.gpu.name} (${capabilities.gpu.memory_gb} GB)`;
  } else {
    gpuInfo.textContent = "";
  }
}

function buildModelCard(
  model: { id: string; owned_by: string },
  performance: DashboardData["performance"],
  modelMetrics: PollData["model_metrics"],
): HTMLElement {
  const perf = performance?.[model.id];
  const metrics = modelMetrics?.[model.id];

  const header = el(
    "div",
    { class: "model-card-header" },
    el("span", { class: "model-id", title: model.id }, model.id),
    el("span", { class: "model-badge" }, model.owned_by),
  );

  const statsContainer = el("div", { class: "model-stats" });

  function addStat(label: string, value: string, cls?: string): void {
    const valEl = el("span", { class: `model-stat-value${cls ? ` ${cls}` : ""}` }, value);
    statsContainer.appendChild(
      el(
        "div",
        { class: "model-stat" },
        el("span", { class: "model-stat-label" }, label),
        valEl,
      ),
    );
  }

  if (perf) {
    addStat("TPS", perf.tokens_per_second.toFixed(1));
    addStat("Peak TPS", perf.peak_tps.toFixed(1));
    addStat("TTFT", `${perf.time_to_first_token_ms.toFixed(0)} ms`);
    addStat("Active", String(perf.active_requests));
    if (perf.error_rate > 0) {
      addStat("Errors", `${(perf.error_rate * 100).toFixed(1)}%`, "error");
    }
  }

  if (metrics) {
    addStat("Memory", `${metrics.memory_mb.toFixed(0)} MB`);
  }

  const card = el("div", { class: "model-card" }, header, statsContainer);

  if (metrics && metrics.context_window > 0) {
    const pct = Math.round(
      (metrics.context_used / metrics.context_window) * 100,
    );
    const contextBarFill = el("div", { class: "context-bar-fill" });
    contextBarFill.style.width = `${pct}%`;

    card.appendChild(
      el(
        "div",
        { class: "model-context-bar" },
        el(
          "div",
          { class: "context-label" },
          `Context: ${metrics.context_used.toLocaleString()} / ${metrics.context_window.toLocaleString()} (${pct}%)`,
        ),
        el("div", { class: "context-bar" }, contextBarFill),
      ),
    );
  }

  return card;
}

function renderModelCards(
  models: Array<{ id: string; owned_by: string }>,
  performance: DashboardData["performance"],
  modelMetrics: PollData["model_metrics"],
): void {
  // Clear existing cards safely
  while (modelCardsEl.firstChild) {
    modelCardsEl.removeChild(modelCardsEl.firstChild);
  }

  if (models.length === 0) {
    noModelsEl.hidden = false;
    return;
  }
  noModelsEl.hidden = true;

  for (const model of models) {
    modelCardsEl.appendChild(buildModelCard(model, performance, modelMetrics));
  }
}

function updateModelSelector(
  models: Array<{ id: string; owned_by: string }>,
): void {
  const currentValue = inferenceModel.value;

  // Clear and rebuild options safely
  while (inferenceModel.firstChild) {
    inferenceModel.removeChild(inferenceModel.firstChild);
  }

  const defaultOpt = document.createElement("option");
  defaultOpt.value = "";
  defaultOpt.textContent = "Select model...";
  inferenceModel.appendChild(defaultOpt);

  for (const m of models) {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = m.id;
    inferenceModel.appendChild(opt);
  }

  // Restore selection if still valid
  if (currentValue && models.some((m) => m.id === currentValue)) {
    inferenceModel.value = currentValue;
  }

  updateInferenceButtonState();
}

function updateInferenceButtonState(): void {
  inferenceRun.disabled =
    !inferenceModel.value || !inferencePrompt.value.trim();
}

// =============================================================================
// MCP App
// =============================================================================

const app = new App({ name: "heylook-monitor", version: "1.0.0" });

async function pollStatus(): Promise<void> {
  try {
    const result = await app.callServerTool({
      name: "poll_status",
      arguments: {},
    });

    const data = result.structuredContent as unknown as PollData;

    updateConnectionStatus(data.connected);

    if (data.connected) {
      updateSystemMetrics(data.system);

      if (data.models) {
        state.models = data.models;
        renderModelCards(data.models, data.performance, data.model_metrics);
        updateModelSelector(data.models);
      }
    } else {
      renderModelCards([], null, null);
      updateModelSelector([]);
    }
  } catch (error) {
    console.error("Poll failed:", error);
    updateConnectionStatus(false);
  }
}

function startPolling(): void {
  if (state.intervalId) return;
  pollStatus();
  state.intervalId = window.setInterval(pollStatus, POLL_INTERVAL);
}

function stopPolling(): void {
  if (state.intervalId) {
    clearInterval(state.intervalId);
    state.intervalId = null;
  }
}

// =============================================================================
// Inference
// =============================================================================

async function runInference(): Promise<void> {
  const model = inferenceModel.value;
  const prompt = inferencePrompt.value.trim();
  if (!model || !prompt) return;

  inferenceRun.disabled = true;
  inferenceStatusEl.textContent = "Running...";
  inferenceResultEl.hidden = true;

  try {
    const result = await app.callServerTool({
      name: "quick_inference",
      arguments: { model, prompt, max_tokens: 256 },
    });

    if (result.isError) {
      inferenceStatusEl.textContent = "Error";
      inferenceResponseEl.textContent =
        result.content?.[0]?.type === "text"
          ? (result.content[0] as { text: string }).text
          : "Unknown error";
      inferenceResultEl.hidden = false;
      inferenceMetaEl.textContent = "";
    } else {
      const data = result.structuredContent as unknown as InferenceResult;
      inferenceResponseEl.textContent = data.response;
      inferenceMetaEl.textContent = `${data.tokens} tokens | ${data.latency_ms} ms`;
      inferenceResultEl.hidden = false;
      inferenceStatusEl.textContent = "";
    }
  } catch (error) {
    console.error("Inference failed:", error);
    inferenceStatusEl.textContent = "Failed";
  } finally {
    updateInferenceButtonState();
  }
}

// =============================================================================
// Event Handlers
// =============================================================================

inferenceModel.addEventListener("change", updateInferenceButtonState);
inferencePrompt.addEventListener("input", updateInferenceButtonState);
inferenceRun.addEventListener("click", runInference);

// =============================================================================
// Initialization
// =============================================================================

app.onerror = console.error;

// Receive initial dashboard data from show_llm_dashboard
app.ontoolresult = (result) => {
  const data = result.structuredContent as unknown as DashboardData;
  if (!data) return;

  updateConnectionStatus(data.connected);
  state.capabilities = data.capabilities;

  if (data.connected) {
    updateSystemMetrics(data.system);
    updateGpuInfo(data.capabilities);

    if (data.models) {
      state.models = data.models;
      renderModelCards(data.models, data.performance, null);
      updateModelSelector(data.models);
    }
  }

  // Start polling after initial data
  startPolling();
};

app.onteardown = () => {
  stopPolling();
  return {};
};

function handleHostContextChanged(ctx: McpUiHostContext) {
  if (ctx.safeAreaInsets) {
    mainEl.style.paddingTop = `${ctx.safeAreaInsets.top}px`;
    mainEl.style.paddingRight = `${ctx.safeAreaInsets.right}px`;
    mainEl.style.paddingBottom = `${ctx.safeAreaInsets.bottom}px`;
    mainEl.style.paddingLeft = `${ctx.safeAreaInsets.left}px`;
  }
}

app.onhostcontextchanged = handleHostContextChanged;

app.connect().then(() => {
  const ctx = app.getHostContext();
  if (ctx) {
    handleHostContextChanged(ctx);
  }
});
