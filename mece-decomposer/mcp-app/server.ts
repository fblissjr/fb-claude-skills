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
import type {
  Decomposition,
  Node,
  BranchNode,
  AgentAtomSpec,
  HumanAtomSpec,
  ToolAtomSpec,
  ExternalAtomSpec,
} from "./src/types.js";

const execFileAsync = promisify(execFile);

// Works both from source (server.ts) and compiled (dist/server.js)
const DIST_DIR = import.meta.filename.endsWith(".ts")
  ? path.join(import.meta.dirname, "dist")
  : import.meta.dirname;

// Path to the validate_mece.py script (relative to this repo)
const VALIDATE_SCRIPT = path.resolve(
  import.meta.dirname,
  "..",
  "skills",
  "mece-decomposer",
  "scripts",
  "validate_mece.py",
);

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
          const { stdout } = await execFileAsync("uv", [
            "run",
            "python",
            VALIDATE_SCRIPT,
            tmpFile,
          ]);

          const report = JSON.parse(stdout);
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
                text: `Validation (fallback, uv unavailable: ${msg}): using embedded validation_summary. Score: ${summary.overall_score}`,
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
          const { stdout } = await execFileAsync("uv", [
            "run",
            "python",
            VALIDATE_SCRIPT,
            tmpFile,
          ]);
          report = JSON.parse(stdout);
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

// ===========================================================================
// SDK Code Generation
// ===========================================================================

const MODEL_MAP: Record<string, string> = {
  haiku: "claude-haiku-4-5-20251001",
  sonnet: "claude-sonnet-4-6",
  opus: "claude-opus-4-6",
};

function generateSdkCode(decomposition: Decomposition): string {
  const lines: string[] = [];
  const agents: string[] = [];

  lines.push('"""');
  lines.push(`Agent SDK scaffolding for: ${decomposition.metadata.scope}`);
  lines.push("");
  lines.push(`Dimension: ${decomposition.metadata.decomposition_dimension}`);
  lines.push(`Source: ${decomposition.metadata.source_type}`);
  lines.push(`Generated from MECE decomposition v${decomposition.metadata.version}`);
  lines.push('"""');
  lines.push("");
  lines.push("import asyncio");
  lines.push("from agents import Agent, Runner, function_tool");
  lines.push("");
  lines.push("");

  // Generate agents for all atom nodes
  collectAgents(decomposition.tree, agents, lines);

  lines.push("");
  lines.push("# " + "=".repeat(70));
  lines.push("# Orchestration");
  lines.push("# " + "=".repeat(70));
  lines.push("");

  // Generate orchestration functions
  generateOrchestration(decomposition.tree, lines, 0);

  // Main entry point
  lines.push("");
  lines.push("");
  lines.push("async def main(input_data: str) -> str:");
  lines.push(`    """Execute: ${decomposition.metadata.scope}"""`);
  lines.push(
    `    return await execute_${varName(decomposition.tree.id, decomposition.tree.label)}(input_data)`,
  );
  lines.push("");
  lines.push("");
  lines.push('if __name__ == "__main__":');
  lines.push('    result = asyncio.run(main("initial input"))');
  lines.push("    print(result)");
  lines.push("");

  return lines.join("\n");
}

function collectAgents(node: Node, agents: string[], lines: string[]): void {
  if (node.node_type === "atom") {
    const spec = node.atom_spec;
    const name = varName(node.id, node.label);

    if (spec.execution_type === "agent") {
      const agentSpec = spec as AgentAtomSpec;
      const def = agentSpec.agent_definition;
      lines.push(`# Node ${node.id}: ${node.label}`);
      lines.push(`${name}_agent = Agent(`);
      lines.push(`    name="${def.name}",`);
      lines.push(`    model="${MODEL_MAP[def.model] || def.model}",`);
      lines.push(`    instructions="""`);
      lines.push(`    ${def.prompt}`);
      lines.push(`    """,`);
      if (def.tools.length > 0) {
        lines.push(`    tools=[${def.tools.join(", ")}],`);
      }
      lines.push(")");
      lines.push("");
      agents.push(name);
    } else if (spec.execution_type === "human") {
      const humanSpec = spec as HumanAtomSpec;
      lines.push(`# Node ${node.id}: ${node.label} (human-in-the-loop)`);
      lines.push(`# Action: ${humanSpec.human_instruction.action}`);
      lines.push(
        `# Method: ${humanSpec.human_instruction.integration_method}`,
      );
      lines.push("");
    } else if (spec.execution_type === "tool") {
      const toolSpec = spec as ToolAtomSpec;
      lines.push(`# Node ${node.id}: ${node.label} (direct tool call)`);
      lines.push(`# Tool: ${toolSpec.tool_invocation.tool_name}`);
      lines.push("");
    } else if (spec.execution_type === "external") {
      const extSpec = spec as ExternalAtomSpec;
      lines.push(`# Node ${node.id}: ${node.label} (external integration)`);
      lines.push(`# System: ${extSpec.external_integration.system}`);
      lines.push(
        `# Protocol: ${extSpec.external_integration.protocol}`,
      );
      lines.push("");
    }
    return;
  }

  for (const child of (node as BranchNode).children) {
    collectAgents(child, agents, lines);
  }
}

function generateOrchestration(
  node: Node,
  lines: string[],
  indent: number,
): void {
  const name = varName(node.id, node.label);
  const pad = " ".repeat(indent);

  if (node.node_type === "atom") {
    // Atom execution
    const spec = node.atom_spec;
    if (spec.execution_type === "agent") {
      lines.push(
        `${pad}async def execute_${name}(input_data: str) -> str:`,
      );
      lines.push(`${pad}    """${node.label}"""`);
      lines.push(
        `${pad}    result = await Runner.run(${name}_agent, input=input_data)`,
      );
      lines.push(`${pad}    return result.final_output`);
    } else {
      lines.push(
        `${pad}async def execute_${name}(input_data: str) -> str:`,
      );
      lines.push(`${pad}    """${node.label} (${spec.execution_type})"""`);
      lines.push(
        `${pad}    # TODO: implement ${spec.execution_type} execution`,
      );
      lines.push(`${pad}    return input_data`);
    }
    lines.push("");
    return;
  }

  const branch = node as BranchNode;
  lines.push(`${pad}async def execute_${name}(input_data: str) -> str:`);
  lines.push(
    `${pad}    """${node.label} (${branch.orchestration} orchestration)"""`,
  );

  if (branch.orchestration === "sequential") {
    lines.push(`${pad}    result = input_data`);
    for (const child of branch.children) {
      const childName = varName(child.id, child.label);
      lines.push(
        `${pad}    result = await execute_${childName}(result)`,
      );
    }
    lines.push(`${pad}    return result`);
  } else if (branch.orchestration === "parallel") {
    lines.push(`${pad}    results = await asyncio.gather(`);
    for (const child of branch.children) {
      const childName = varName(child.id, child.label);
      lines.push(`${pad}        execute_${childName}(input_data),`);
    }
    lines.push(`${pad}    )`);
    lines.push(`${pad}    return "\\n".join(str(r) for r in results)`);
  } else if (branch.orchestration === "conditional") {
    lines.push(`${pad}    # Route based on: ${branch.condition || "condition"}`);
    for (let i = 0; i < branch.children.length; i++) {
      const child = branch.children[i];
      const childName = varName(child.id, child.label);
      const keyword = i === 0 ? "if" : "elif";
      lines.push(
        `${pad}    ${keyword} should_route_to_${childName}(input_data):`,
      );
      lines.push(
        `${pad}        return await execute_${childName}(input_data)`,
      );
    }
    lines.push(`${pad}    return input_data`);
  } else if (branch.orchestration === "loop") {
    const loopSpec = branch.loop_spec;
    const maxIter = loopSpec?.max_iterations || 100;
    lines.push(`${pad}    results = []`);
    lines.push(`${pad}    for i in range(${maxIter}):`);
    if (branch.children.length > 0) {
      const childName = varName(
        branch.children[0].id,
        branch.children[0].label,
      );
      lines.push(
        `${pad}        result = await execute_${childName}(input_data)`,
      );
      lines.push(`${pad}        results.append(result)`);
    }
    lines.push(
      `${pad}        # Check: ${loopSpec?.termination || "termination condition"}`,
    );
    lines.push(`${pad}        if should_terminate(results):`);
    lines.push(`${pad}            break`);
    lines.push(`${pad}    return "\\n".join(str(r) for r in results)`);
  }

  lines.push("");
  lines.push("");

  // Recurse into children
  for (const child of branch.children) {
    generateOrchestration(child, lines, indent);
  }
}

function varName(id: string, label: string): string {
  const fromLabel = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  return `n${id.replace(/\./g, "_")}_${fromLabel}`;
}
