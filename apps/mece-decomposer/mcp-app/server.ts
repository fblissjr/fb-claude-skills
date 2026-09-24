import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type {
  CallToolResult,
  ReadResourceResult,
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { z } from "zod";
import type { Decomposition, Node } from "./src/types.js";
import { generateSdkCode } from "./sdk-codegen.js";

const execFileAsync = promisify(execFile);

// Detect source vs compiled context
const IS_SOURCE = import.meta.filename.endsWith(".ts");

// Works both from source (server.ts in mcp-app/) and compiled (dist/index.cjs)
const DIST_DIR = IS_SOURCE
  ? path.join(import.meta.dirname, "dist")
  : import.meta.dirname;

// Plugin root: mece-decomposer/
// From source: mcp-app/ -> ../ -> mece-decomposer/
// From dist:   mcp-app/dist/ -> ../../ -> mece-decomposer/
const PLUGIN_ROOT = IS_SOURCE
  ? path.resolve(import.meta.dirname, "..")
  : path.resolve(import.meta.dirname, "..", "..");

// Path to the validate_mece.py script
export const VALIDATE_SCRIPT = path.join(
  PLUGIN_ROOT,
  "skills",
  "mece-decomposer",
  "scripts",
  "validate_mece.py",
);

/**
 * The command that validates one decomposition file. `uv run --script` reads the
 * script's inline dependency block, so it runs in any working directory;
 * `uv run python <script>` ignores that block and needs orjson in the project.
 */
export function validatorCommand(inputPath: string): [string, string[]] {
  return ["uv", ["run", "--script", VALIDATE_SCRIPT, inputPath]];
}

/**
 * Run the validator on one decomposition file and return its JSON report.
 * The script exits 1 for an invalid tree; that is a report, not a failure, so
 * only a run with no parseable report on stdout rejects.
 */
export async function runValidator(inputPath: string): Promise<any> {
  try {
    const { stdout } = await execFileAsync(...validatorCommand(inputPath));
    return JSON.parse(stdout);
  } catch (e) {
    const stdout = (e as { stdout?: string }).stdout;
    if (stdout) {
      try {
        return JSON.parse(stdout);
      } catch {
        // Not a report: fall through to the original error.
      }
    }
    throw e;
  }
}

/**
 * Creates a new MCP server instance with all MECE tools and resources.
 */
export function createServer(): McpServer {
  const server = new McpServer({
    name: "MECE Decomposer",
    version: "0.1.0",
  });

  const resourceUri = "ui://mece/mcp-app.html";

  // =========================================================================
  // Tool 1: mece-decompose (model + app)
  // =========================================================================
  registerAppTool(
    server,
    "mece-decompose",
    {
      title: "MECE Decompose",
      description:
        "Accept a MECE decomposition JSON and render it as an interactive tree visualization. Pass the full decomposition JSON as a string.",
      inputSchema: {
        decomposition: z.string().describe(
          "The full MECE decomposition JSON string conforming to output_schema.md",
        ),
      },
      _meta: { ui: { resourceUri } },
    },
    async (params: { decomposition: string }): Promise<CallToolResult> => {
      try {
        const parsed: Decomposition = JSON.parse(params.decomposition);
        const nodeCount = countNodes(parsed.tree);
        return {
          structuredContent: {
            type: "decomposition",
            decomposition: parsed,
          },
          content: [
            {
              type: "text",
              text: `Decomposition loaded: "${parsed.metadata.scope}" -- ${nodeCount} nodes, ${parsed.metadata.decomposition_dimension} dimension, overall score ${parsed.validation_summary.overall_score}`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text", text: `Error parsing decomposition: ${msg}` }],
          isError: true,
        };
      }
    },
  );

  // =========================================================================
  // Tool 2: mece-validate (model + app)
  // =========================================================================
  registerAppTool(
    server,
    "mece-validate",
    {
      title: "MECE Validate",
      description:
        "Validate a MECE decomposition JSON for schema compliance, structural integrity, and scoring. Returns a detailed validation report.",
      inputSchema: {
        decomposition: z.string().describe(
          "The full MECE decomposition JSON string to validate",
        ),
      },
      _meta: { ui: { resourceUri } },
    },
    async (params: { decomposition: string }): Promise<CallToolResult> => {
      try {
        // Write to temp file for the validator
        const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "mece-"));
        const tmpFile = path.join(tmpDir, "input.json");
        await fs.writeFile(tmpFile, params.decomposition, "utf-8");

        try {
          const report = await runValidator(tmpFile);
          const status = report.valid ? "PASS" : "FAIL";

          return {
            structuredContent: {
              type: "validation",
              report,
            },
            content: [
              {
                type: "text",
                text: `Validation ${status}: ${report.summary.errors} errors, ${report.summary.warnings} warnings, ${report.summary.info} info`,
              },
            ],
          };
        } finally {
          // Clean up temp files
          await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        // Graceful degradation if uv not available -- do basic JSON parse check
        try {
          const parsed: Decomposition = JSON.parse(params.decomposition);
          const summary = parsed.validation_summary;
          return {
            structuredContent: {
              type: "validation",
              report: {
                valid: summary.overall_score >= 0.7,
                summary: {
                  errors: summary.issues.filter((i) => i.severity === "error")
                    .length,
                  warnings: summary.issues.filter(
                    (i) => i.severity === "warning",
                  ).length,
                  info: summary.issues.filter((i) => i.severity === "info")
                    .length,
                  total_nodes: summary.total_nodes,
                  total_atoms: summary.total_atoms,
                  total_branches: summary.total_branches,
                  max_depth: summary.max_depth,
                  max_fan_out: summary.max_fan_out,
                },
                issues: summary.issues,
              },
            },
            content: [
              {
                type: "text",
                text: `Validation (fallback, validator could not run: ${msg}): using embedded validation_summary. Score: ${summary.overall_score}`,
              },
            ],
          };
        } catch {
          return {
            content: [
              { type: "text", text: `Validation failed: ${msg}` },
            ],
            isError: true,
          };
        }
      }
    },
  );

  // =========================================================================
  // Tool 3: mece-refine-node (app-only -- hidden from model)
  // =========================================================================
  registerAppTool(
    server,
    "mece-refine-node",
    {
      title: "MECE Refine Node",
      description:
        "Interactively edit a node in the decomposition tree. App-only tool for UI-driven refinement.",
      inputSchema: {
        nodeId: z.string().describe("The ID of the node to update"),
        updates: z.record(z.string(), z.unknown()).describe(
          "Partial node fields to update (label, description, orchestration, etc.)",
        ),
        fullTree: z.string().describe(
          "The full decomposition JSON with the update applied",
        ),
      },
      _meta: { ui: { resourceUri, visibility: ["app"] } },
    },
    async (params: {
      nodeId: string;
      updates: Record<string, unknown>;
      fullTree: string;
    }): Promise<CallToolResult> => {
      try {
        const parsed: Decomposition = JSON.parse(params.fullTree);
        const node = findNode(parsed.tree, params.nodeId);
        if (!node) {
          return {
            content: [
              {
                type: "text",
                text: `Node "${params.nodeId}" not found in tree`,
              },
            ],
            isError: true,
          };
        }

        // Apply updates
        Object.assign(node, params.updates);

        // Try to re-validate
        let report = null;
        try {
          const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "mece-"));
          const tmpFile = path.join(tmpDir, "input.json");
          await fs.writeFile(tmpFile, JSON.stringify(parsed), "utf-8");
          report = await runValidator(tmpFile);
          await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
        } catch {
          // Validation unavailable, continue without
        }

        return {
          structuredContent: {
            type: "refinement",
            decomposition: parsed,
            validation: report,
          },
          content: [
            {
              type: "text",
              text: `Node "${params.nodeId}" updated: ${JSON.stringify(params.updates)}`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text", text: `Refinement failed: ${msg}` }],
          isError: true,
        };
      }
    },
  );

  // =========================================================================
  // Tool 4: mece-export-sdk (model + app)
  // =========================================================================
  registerAppTool(
    server,
    "mece-export-sdk",
    {
      title: "MECE Export SDK",
      description:
        "Generate Claude Agent SDK Python scaffolding from a MECE decomposition tree. Produces runnable code with agents, orchestration, and error handling.",
      inputSchema: {
        decomposition: z.string().describe(
          "The full MECE decomposition JSON string to export",
        ),
      },
      _meta: { ui: { resourceUri } },
    },
    async (params: { decomposition: string }): Promise<CallToolResult> => {
      try {
        const parsed: Decomposition = JSON.parse(params.decomposition);
        const code = generateSdkCode(parsed);
        const filename = `${sanitizeFilename(parsed.metadata.scope)}_agents.py`;

        return {
          structuredContent: {
            type: "export",
            code,
            filename,
          },
          content: [
            {
              type: "text",
              text: `Generated Agent SDK scaffolding: ${filename} (${code.split("\n").length} lines)`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text", text: `Export failed: ${msg}` }],
          isError: true,
        };
      }
    },
  );

  // =========================================================================
  // Resource: serve bundled HTML
  // =========================================================================
  registerAppResource(
    server,
    resourceUri,
    resourceUri,
    { mimeType: RESOURCE_MIME_TYPE },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, "mcp-app.html"),
        "utf-8",
      );
      return {
        contents: [{ uri: resourceUri, mimeType: RESOURCE_MIME_TYPE, text: html }],
      };
    },
  );

  return server;
}

// ===========================================================================
// Helpers
// ===========================================================================

function countNodes(node: Node): number {
  if (node.node_type === "atom") return 1;
  return 1 + node.children.reduce((acc, c) => acc + countNodes(c), 0);
}

function findNode(node: Node, id: string): Node | null {
  if (node.id === id) return node;
  if (node.node_type === "branch") {
    for (const child of node.children) {
      const found = findNode(child, id);
      if (found) return found;
    }
  }
  return null;
}

function sanitizeFilename(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 50);
}
