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
import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import { z } from "zod";
import {
  findSkillPath,
  measureTokensDetailed,
  runQualityCheck,
} from "./src/utils/checks.js";

// Detect source vs compiled context
const IS_SOURCE = import.meta.filename.endsWith(".ts");

// Works both from source (server.ts in mcp-app/) and compiled (dist/index.cjs)
const DIST_DIR = IS_SOURCE
  ? path.join(import.meta.dirname, "dist")
  : import.meta.dirname;

// Plugin root: skill-dashboard/
// From source: mcp-app/ -> ../ -> skill-dashboard/
// From dist:   mcp-app/dist/ -> ../../ -> skill-dashboard/
const PLUGIN_ROOT = IS_SOURCE
  ? path.resolve(import.meta.dirname, "..")
  : path.resolve(import.meta.dirname, "..", "..");

// Repo root: skill-dashboard is at apps/skill-dashboard/
// So repo root is two levels up from PLUGIN_ROOT
const REPO_ROOT = process.env.SKILL_DASHBOARD_ROOT
  ?? path.resolve(PLUGIN_ROOT, "..", "..");

/**
 * Creates a new MCP server instance with all dashboard tools and resources.
 */
export function createServer(): McpServer {
  const server = new McpServer({
    name: "Skill Dashboard",
    version: "1.1.0",
  });

  const resourceUri = "ui://skill-dashboard/mcp-app.html";

  // =========================================================================
  // Tool: skill-quality-check
  // =========================================================================
  registerAppTool(
    server,
    "skill-quality-check",
    {
      title: "Skill Quality Check",
      description:
        "Run quality checks across all skills, plugins, and repo hygiene. Returns pass/fail results with token budgets, freshness, spec compliance, and description quality.",
      inputSchema: {
        filter: z
          .string()
          .optional()
          .describe(
            "Optional skill name substring filter to check only matching skills",
          ),
      },
      _meta: { ui: { resourceUri } },
    },
    async (params: { filter?: string }): Promise<CallToolResult> => {
      try {
        const result = runQualityCheck(REPO_ROOT, params.filter);
        const { summary } = result;

        return {
          structuredContent: {
            type: "quality-check",
            ...result,
          },
          content: [
            {
              type: "text",
              text: `Quality check: ${summary.passed} passed, ${summary.failed} failed across ${result.skills.length} skills, ${result.plugins.length} plugins`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [
            { type: "text", text: `Quality check failed: ${msg}` },
          ],
          isError: true,
        };
      }
    },
  );

  // =========================================================================
  // Tool: skill-measure
  // =========================================================================
  registerAppTool(
    server,
    "skill-measure",
    {
      title: "Skill Measure",
      description:
        "Per-file token breakdown for a single skill. Shows each .md file with character count, estimated tokens, and percentage of total.",
      inputSchema: {
        skillName: z.string().describe("Name of the skill to measure"),
      },
      _meta: { ui: { resourceUri } },
    },
    async (params: { skillName: string }): Promise<CallToolResult> => {
      try {
        const skillPath = findSkillPath(REPO_ROOT, params.skillName);
        if (!skillPath) {
          return {
            content: [
              {
                type: "text",
                text: `Skill not found: ${params.skillName}`,
              },
            ],
            isError: true,
          };
        }
        const skillDir = path.dirname(skillPath);
        const files = measureTokensDetailed(skillDir);
        const totalTokens = files.reduce((s, f) => s + f.tokens, 0);
        const relDir = path.relative(REPO_ROOT, skillDir);

        const fileList = files
          .map((f) => `${f.path}: ${f.tokens.toLocaleString()}`)
          .join(", ");

        return {
          structuredContent: {
            type: "skill-measure",
            skillName: params.skillName,
            skillDir: relDir,
            files,
            totalTokens,
            budget: { warn: 4000, critical: 8000 },
          },
          content: [
            {
              type: "text",
              text: `${params.skillName}: ${totalTokens.toLocaleString()} tokens across ${files.length} files (${fileList})`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [
            { type: "text", text: `Skill measure failed: ${msg}` },
          ],
          isError: true,
        };
      }
    },
  );

  // =========================================================================
  // Tool: skill-verify
  // =========================================================================
  registerAppTool(
    server,
    "skill-verify",
    {
      title: "Skill Verify",
      description:
        "Mark a skill as verified by updating metadata.last_verified in its SKILL.md frontmatter to today's date.",
      inputSchema: {
        skillName: z.string().describe("Name of the skill to verify"),
      },
      _meta: { ui: { resourceUri, visibility: ["app"] } },
    },
    async (params: { skillName: string }): Promise<CallToolResult> => {
      try {
        const skillPath = findSkillPath(REPO_ROOT, params.skillName);
        if (!skillPath) {
          return {
            content: [
              {
                type: "text",
                text: `Skill not found: ${params.skillName}`,
              },
            ],
            isError: true,
          };
        }

        const content = await fs.readFile(skillPath, "utf-8");
        const parsed = matter(content);
        const meta = (parsed.data.metadata || {}) as Record<string, unknown>;
        const prev = meta.last_verified;
        const previousDate =
          prev instanceof Date
            ? prev.toISOString().slice(0, 10)
            : prev
              ? String(prev)
              : null;
        const newDate = new Date().toISOString().slice(0, 10);
        meta.last_verified = newDate;
        parsed.data.metadata = meta;
        const updated = matter.stringify(parsed.content, parsed.data);
        await fs.writeFile(skillPath, updated, "utf-8");

        const relPath = path.relative(REPO_ROOT, skillPath);

        return {
          structuredContent: {
            type: "skill-verify",
            skillName: params.skillName,
            previousDate,
            newDate,
            path: relPath,
          },
          content: [
            {
              type: "text",
              text: `Verified ${params.skillName}: last_verified updated to ${newDate}`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [
            { type: "text", text: `Skill verify failed: ${msg}` },
          ],
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
        contents: [
          { uri: resourceUri, mimeType: RESOURCE_MIME_TYPE, text: html },
        ],
      };
    },
  );

  return server;
}
