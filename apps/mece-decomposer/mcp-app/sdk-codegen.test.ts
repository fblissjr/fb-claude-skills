/**
 * Tests for the Claude Agent SDK code generator behind `mece-export-sdk`.
 *
 * The generator used to emit OpenAI Agents SDK code (`from agents import Agent,
 * Runner`) while every doc called it Claude Agent SDK scaffolding. It also
 * emitted atom tools as bare Python names (`tools=[Read, Write]`) and called
 * `should_route_to_*` / `should_terminate` helpers it never defined, so the
 * scaffold raised NameError on first run.
 *
 * The generated Python is executed against a fake `claude_agent_sdk` module
 * (below), so these tests check what the code does, not just how it reads,
 * and need only `python3` on PATH.
 */

import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { generateSdkCode } from "./sdk-codegen.ts";
import type { AtomNode, BranchNode, Decomposition, Node } from "./src/types.ts";

// Stand-in for claude_agent_sdk: records every ClaudeAgentOptions built, and
// answers each query() with a ResultMessage of "<model>(<prompt>)" after one
// non-result message, as the real stream does.
const FAKE_SDK = `
CREATED = []

class ClaudeAgentOptions:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        CREATED.append(kwargs)

class ResultMessage:
    def __init__(self, result):
        self.result = result
        self.is_error = False
        self.subtype = "success"

async def query(*, prompt, options):
    yield object()
    yield ResultMessage(f"{options.model}({prompt})")
`;

// Loads the generated module without running its __main__ block, then runs the
// requested probe and prints one JSON line.
const HARNESS = `
import asyncio, json, runpy, symtable, builtins, sys
sys.path.insert(0, sys.argv[1])
import claude_agent_sdk as sdk
code_path, probe = sys.argv[2], sys.argv[3]
source = open(code_path).read()

if probe == "undefined_globals":
    top = symtable.symtable(source, code_path, "exec")
    defined = {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported()}
    defined |= set(dir(builtins))
    missing = set()
    def walk(table):
        for s in table.get_symbols():
            if s.is_referenced() and s.is_global() and s.get_name() not in defined:
                missing.add(s.get_name())
        for child in table.get_children():
            walk(child)
    for child in top.get_children():
        walk(child)
    print(json.dumps(sorted(missing)))
else:
    module = runpy.run_path(code_path, run_name="generated")
    result = asyncio.run(module["main"]("in")) if probe == "run" else None
    print(json.dumps({"options": sdk.CREATED, "result": result}))
`;

const workdir = fs.mkdtempSync(path.join(os.tmpdir(), "mece-codegen-"));
fs.mkdirSync(path.join(workdir, "claude_agent_sdk"));
fs.writeFileSync(path.join(workdir, "claude_agent_sdk", "__init__.py"), FAKE_SDK);
fs.writeFileSync(path.join(workdir, "harness.py"), HARNESS);
afterAll(() => fs.rmSync(workdir, { recursive: true, force: true }));

let counter = 0;
function runProbe(code: string, probe: "load" | "run" | "undefined_globals"): any {
  const file = path.join(workdir, `generated_${counter++}.py`);
  fs.writeFileSync(file, code);
  const proc = spawnSync("python3", [path.join(workdir, "harness.py"), workdir, file, probe], {
    encoding: "utf-8",
  });
  if (proc.status !== 0) {
    throw new Error(`generated code failed (${probe}):\n${proc.stderr}\n--- code ---\n${code}`);
  }
  return JSON.parse(proc.stdout.trim().split("\n").pop()!);
}

// -- Fixtures --

const base = { description: "", depth: 1, parent_id: "1" };
const io = { estimated_duration: "1m", inputs: [], outputs: [], error_modes: [] };

function agent(id: string, label: string, model: "haiku" | "sonnet" | "opus", extra: Partial<{
  prompt: string; tools: string[]; max_turns: number;
}> = {}): AtomNode {
  return {
    ...base, id, label, node_type: "atom",
    atom_spec: {
      ...io, execution_type: "agent",
      agent_definition: {
        name: label.toLowerCase().replace(/ /g, "_"), description: label,
        prompt: extra.prompt ?? `Do ${label}.`, tools: extra.tools ?? [],
        model, model_rationale: "", max_turns: extra.max_turns,
      },
    },
  };
}

function branch(id: string, label: string, orchestration: BranchNode["orchestration"],
  children: Node[], extra: Partial<BranchNode> = {}): BranchNode {
  return {
    ...base, id, label, node_type: "branch", orchestration,
    orchestration_rationale: "", children, ...extra,
  };
}

function decomposition(tree: Node): Decomposition {
  return {
    metadata: {
      scope: "Test scope", trigger: "", completion_criteria: "",
      decomposition_dimension: "temporal", dimension_rationale: "",
      source_type: "document", version: "1.0", created_at: "",
    },
    tree,
    cross_branch_dependencies: [],
    validation_summary: {
      me_score: 1, ce_score: 1, overall_score: 1, levels_assessed: 1, total_nodes: 1,
      total_atoms: 1, total_branches: 0, max_depth: 1, max_fan_out: 1, issues: [],
    },
  };
}

// Every branch type and every atom type, so the undefined-name check sees all
// the code paths the generator has.
const everyShape = decomposition(branch("1", "Root", "sequential", [
  agent("1.1", "Draft", "sonnet", { tools: ["Read", "Write"], max_turns: 5 }),
  branch("1.2", "Checks", "parallel", [
    agent("1.2.1", "Lint", "haiku"),
    { ...base, id: "1.2.2", label: "Approve", node_type: "atom", atom_spec: {
      ...io, execution_type: "human", human_instruction: {
        action: "approve", context: "", decision_criteria: "", integration_method: "manual",
      } } },
  ]),
  branch("1.3", "Route", "conditional", [
    agent("1.3.1", "Escalate", "opus"),
    { ...base, id: "1.3.2", label: "Store", node_type: "atom", atom_spec: {
      ...io, execution_type: "tool", tool_invocation: { tool_name: "write_row", parameters: {} },
    } },
  ], { condition: "severity is high" }),
  branch("1.4", "Poll", "loop", [
    { ...base, id: "1.4.1", label: "Fetch", node_type: "atom", atom_spec: {
      ...io, execution_type: "external", external_integration: {
        system: "CRM", operation: "get", protocol: "rest_api",
      } } },
  ], { loop_spec: { iterator: "page", termination: "no more pages", max_iterations: 3 } }),
]));

// -- Tests --

describe("generateSdkCode", () => {
  test("targets the Claude Agent SDK, not the OpenAI Agents SDK", () => {
    // The reported bug. `agents` is the OpenAI Agents SDK's import name.
    const code = generateSdkCode(everyShape);
    expect(code).toContain("from claude_agent_sdk import");
    expect(code).not.toMatch(/^from agents import/m);
    expect(code).not.toContain("Runner.run");
  });

  test("every global the generated module references is defined", () => {
    // Catches the NameErrors: bare tool identifiers and undefined routing helpers.
    expect(runProbe(generateSdkCode(everyShape), "undefined_globals")).toEqual([]);
  });

  test("an agent atom becomes ClaudeAgentOptions with its tier, tools, turns and prompt", () => {
    // The prompt carries a triple quote and a backslash: the old generator pasted
    // prompts inside """...""", which a triple quote in the prompt breaks.
    const prompt = 'Summarise the "notes" file.\nKeep """quoted""" text and C:\\path as is.';
    const code = generateSdkCode(decomposition(
      agent("1", "Draft", "sonnet", { prompt, tools: ["Read", "Write"], max_turns: 5 }),
    ));
    const { options } = runProbe(code, "load");
    expect(options).toEqual([{
      model: "claude-sonnet-5",
      system_prompt: prompt,
      tools: ["Read", "Write"],
      allowed_tools: ["Read", "Write"],
      max_turns: 5,
    }]);
  });

  test("an agent atom with no tools gets none of the built-ins", () => {
    // tools=[] disables every built-in; omitting it would hand the atom all of them.
    const code = generateSdkCode(decomposition(agent("1", "Classify", "haiku")));
    const [opts] = runProbe(code, "load").options;
    expect(opts.tools).toEqual([]);
    expect(opts.model).toBe("claude-haiku-4-5");
  });

  test("sequential chains outputs and parallel fans the same input out", () => {
    // What the orchestration functions are for: step N's result is step N+1's input.
    const tree = branch("1", "Root", "sequential", [
      agent("1.1", "First", "haiku"),
      branch("1.2", "Both", "parallel", [
        agent("1.2.1", "Left", "sonnet"),
        agent("1.2.2", "Right", "opus"),
      ]),
    ]);
    const { result } = runProbe(generateSdkCode(decomposition(tree)), "run");
    expect(result).toBe(
      "claude-sonnet-5(claude-haiku-4-5(in))\nclaude-opus-5-5(claude-haiku-4-5(in))",
    );
  });
});
