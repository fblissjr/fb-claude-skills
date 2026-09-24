/**
 * Claude Agent SDK code generation for a MECE decomposition tree.
 * Kept apart from server.ts so it can be tested without starting the MCP server.
 *
 * Mapping rules: skills/mece-decomposer/references/agent_sdk_mapping.md. The
 * orchestration is plain asyncio driven by the tree; each agent atom is one
 * `query()` call with its own `ClaudeAgentOptions`.
 */

import type {
  Decomposition,
  Node,
  BranchNode,
  AgentAtomSpec,
  HumanAtomSpec,
  ToolAtomSpec,
  ExternalAtomSpec,
} from "./src/types.js";

// The model ID column in agent_sdk_mapping.md must match this table; update
// both together when a tier moves to a new model.
const MODEL_MAP: Record<string, string> = {
  haiku: "claude-haiku-4-5",
  sonnet: "claude-sonnet-5",
  opus: "claude-opus-5-5",
};

const RUN_AGENT = `async def run_agent(prompt: str, options: ClaudeAgentOptions) -> str:
    """Run one agent atom to completion and return its final text."""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"agent run failed: {message.subtype}")
            return message.result or ""
    raise RuntimeError("query() ended without a ResultMessage")`;

/** A Python string literal for any text: JSON string escapes are valid Python. */
function pyStr(s: string): string {
  return JSON.stringify(s);
}

/** Text safe to place after `#` on one line. */
function oneLine(s: string): string {
  return s.replace(/\s*[\r\n]+\s*/g, " ");
}

export function generateSdkCode(decomposition: Decomposition): string {
  const { metadata, tree } = decomposition;
  const lines: string[] = [
    `# Claude Agent SDK scaffolding for: ${oneLine(metadata.scope)}`,
    `# Dimension: ${oneLine(metadata.decomposition_dimension)}`,
    `# Source: ${oneLine(metadata.source_type)}`,
    `# Generated from MECE decomposition v${oneLine(metadata.version)}`,
    "#",
    "# Requires the claude-agent-sdk package, which drives the Claude Code CLI.",
    "# Functions that raise NotImplementedError mark the steps left to write.",
    "",
    "import asyncio",
    "",
    "from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query",
    "",
    "",
    RUN_AGENT,
    "",
    "",
  ];

  collectAgentOptions(tree, lines);

  lines.push("# " + "=".repeat(70));
  lines.push("# Orchestration");
  lines.push("# " + "=".repeat(70));
  lines.push("");
  lines.push("");

  generateOrchestration(tree, lines);

  lines.push(
    "async def main(input_data: str) -> str:",
    `    ${pyStr(`Execute: ${metadata.scope}`)}`,
    `    return await execute_${varName(tree.id, tree.label)}(input_data)`,
    "",
    "",
    'if __name__ == "__main__":',
    '    print(asyncio.run(main("initial input")))',
    "",
  );

  return lines.join("\n");
}

function collectAgentOptions(node: Node, lines: string[]): void {
  if (node.node_type === "branch") {
    for (const child of node.children) collectAgentOptions(child, lines);
    return;
  }
  if (node.atom_spec.execution_type !== "agent") return;

  const def = (node.atom_spec as AgentAtomSpec).agent_definition;
  const tools = `[${def.tools.map(pyStr).join(", ")}]`;
  lines.push(`# Node ${node.id}: ${oneLine(node.label)} (${oneLine(def.name)})`);
  if (def.description) lines.push(`# ${oneLine(def.description)}`);
  lines.push(`${varName(node.id, node.label)}_options = ClaudeAgentOptions(`);
  lines.push(`    model=${pyStr(MODEL_MAP[def.model] || def.model)},`);
  lines.push(`    system_prompt=${pyStr(def.prompt)},`);
  // tools limits which built-ins exist ([] means none); allowed_tools
  // pre-approves them so a headless run does not stop at a permission prompt.
  lines.push(`    tools=${tools},`);
  lines.push(`    allowed_tools=${tools},`);
  if (def.max_turns) lines.push(`    max_turns=${def.max_turns},`);
  lines.push(")");
  lines.push("");
  lines.push("");
}

function generateOrchestration(node: Node, lines: string[]): void {
  const name = varName(node.id, node.label);

  if (node.node_type === "atom") {
    const spec = node.atom_spec;
    lines.push(`async def execute_${name}(input_data: str) -> str:`);
    if (spec.execution_type === "agent") {
      lines.push(`    ${pyStr(node.label)}`);
      lines.push(`    return await run_agent(input_data, ${name}_options)`);
    } else {
      lines.push(`    ${pyStr(`${node.label} (${spec.execution_type})`)}`);
      for (const note of atomNotes(spec as HumanAtomSpec | ToolAtomSpec | ExternalAtomSpec)) {
        lines.push(`    # ${oneLine(note)}`);
      }
      lines.push(
        `    raise NotImplementedError(${pyStr(`${spec.execution_type} step ${node.id}: ${node.label}`)})`,
      );
    }
    lines.push("");
    lines.push("");
    return;
  }

  const branch = node as BranchNode;
  const childName = (child: Node) => varName(child.id, child.label);

  if (branch.orchestration === "conditional") {
    lines.push(`def route_${name}(input_data: str) -> str:`);
    lines.push(`    ${pyStr(`Return the id of the child of ${branch.id} to run.`)}`);
    lines.push(`    # Condition: ${oneLine(branch.condition || "not stated")}`);
    lines.push(`    # Children: ${branch.children.map((c) => `${c.id} ${oneLine(c.label)}`).join("; ")}`);
    lines.push(`    raise NotImplementedError(${pyStr(`routing for ${branch.id}: ${branch.label}`)})`);
    lines.push("");
    lines.push("");
  } else if (branch.orchestration === "loop") {
    lines.push(`def should_stop_${name}(results: list[str]) -> bool:`);
    lines.push(`    ${pyStr(`Return True when the loop at ${branch.id} is done.`)}`);
    lines.push(`    # Termination: ${oneLine(branch.loop_spec?.termination || "not stated")}`);
    lines.push(`    raise NotImplementedError(${pyStr(`termination for ${branch.id}: ${branch.label}`)})`);
    lines.push("");
    lines.push("");
  }

  lines.push(`async def execute_${name}(input_data: str) -> str:`);
  lines.push(`    ${pyStr(`${branch.label} (${branch.orchestration})`)}`);

  if (branch.orchestration === "sequential") {
    lines.push("    result = input_data");
    for (const child of branch.children) {
      lines.push(`    result = await execute_${childName(child)}(result)`);
    }
    lines.push("    return result");
  } else if (branch.orchestration === "parallel") {
    lines.push("    results = await asyncio.gather(");
    for (const child of branch.children) {
      lines.push(`        execute_${childName(child)}(input_data),`);
    }
    lines.push("    )");
    lines.push('    return "\\n".join(results)');
  } else if (branch.orchestration === "conditional") {
    lines.push(`    child = route_${name}(input_data)`);
    for (const child of branch.children) {
      lines.push(`    if child == ${pyStr(child.id)}:`);
      lines.push(`        return await execute_${childName(child)}(input_data)`);
    }
    lines.push(`    raise ValueError(f"no child {child!r} under ${branch.id}")`);
  } else if (branch.orchestration === "loop") {
    // Each iteration runs the children in order, as a sequential branch would.
    const maxIter = branch.loop_spec?.max_iterations || 100;
    lines.push("    results: list[str] = []");
    lines.push(`    for _ in range(${maxIter}):`);
    lines.push("        result = input_data");
    for (const child of branch.children) {
      lines.push(`        result = await execute_${childName(child)}(result)`);
    }
    lines.push("        results.append(result)");
    lines.push(`        if should_stop_${name}(results):`);
    lines.push("            break");
    lines.push('    return "\\n".join(results)');
  }

  lines.push("");
  lines.push("");

  for (const child of branch.children) {
    generateOrchestration(child, lines);
  }
}

function atomNotes(spec: HumanAtomSpec | ToolAtomSpec | ExternalAtomSpec): string[] {
  if (spec.execution_type === "human") {
    const h = spec.human_instruction;
    return [
      `Action: ${h.action}`,
      `Method: ${h.integration_method}. A human step is a gate the process defines, so`,
      "collect the decision here in the orchestrator (a prompt, webhook or queue).",
    ];
  }
  if (spec.execution_type === "tool") {
    return [`Tool: ${spec.tool_invocation.tool_name}. Call it directly; no agent needed.`];
  }
  const e = spec.external_integration;
  return [`System: ${e.system}, operation: ${e.operation}, protocol: ${e.protocol}`];
}

function varName(id: string, label: string): string {
  const fromLabel = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  return `n${id.replace(/[^A-Za-z0-9]+/g, "_")}_${fromLabel}`;
}
