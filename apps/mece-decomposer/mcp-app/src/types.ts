// TypeScript types matching output_schema.md exactly

// -- Metadata --

export type DecompositionDimension =
  | "temporal"
  | "functional"
  | "stakeholder"
  | "state"
  | "input_output"
  | "custom";

export type SourceType =
  | "sme_interview"
  | "document"
  | "verbal"
  | "observation"
  | "hybrid";

export interface Metadata {
  scope: string;
  trigger: string;
  completion_criteria: string;
  decomposition_dimension: DecompositionDimension;
  dimension_rationale: string;
  source_type: SourceType;
  inclusions?: string[];
  exclusions?: string[];
  version: string;
  created_at: string;
}

// -- Nodes --

export type Orchestration = "sequential" | "parallel" | "conditional" | "loop";

export interface LoopSpec {
  iterator: string;
  termination: string;
  max_iterations?: number;
}

interface NodeBase {
  id: string;
  label: string;
  description: string;
  depth: number;
  parent_id: string | null;
}

export interface BranchNode extends NodeBase {
  node_type: "branch";
  orchestration: Orchestration;
  orchestration_rationale: string;
  condition?: string | null;
  loop_spec?: LoopSpec | null;
  children: Node[];
}

export interface AtomNode extends NodeBase {
  node_type: "atom";
  atom_spec: AtomSpec;
}

export type Node = BranchNode | AtomNode;

// -- AtomSpec (discriminated by execution_type) --

export type ExecutionType = "agent" | "human" | "tool" | "external";

interface AtomSpecBase {
  estimated_duration: string;
  inputs: string[];
  outputs: string[];
  error_modes: string[];
}

export interface AgentDefinition {
  name: string;
  description: string;
  prompt: string;
  tools: string[];
  model: "haiku" | "sonnet" | "opus";
  model_rationale: string;
  max_turns?: number;
}

export interface AgentAtomSpec extends AtomSpecBase {
  execution_type: "agent";
  agent_definition: AgentDefinition;
}

export interface HumanInstruction {
  action: string;
  context: string;
  decision_criteria: string;
  escalation?: string;
  integration_method: "ask_user_question" | "webhook" | "manual";
}

export interface HumanAtomSpec extends AtomSpecBase {
  execution_type: "human";
  human_instruction: HumanInstruction;
}

export interface ToolInvocation {
  tool_name: string;
  parameters: Record<string, unknown>;
  retry_policy?: "none" | "fixed" | "exponential";
  max_retries?: number;
}

export interface ToolAtomSpec extends AtomSpecBase {
  execution_type: "tool";
  tool_invocation: ToolInvocation;
}

export interface ExternalIntegration {
  system: string;
  operation: string;
  protocol: "rest_api" | "grpc" | "message_queue" | "file_system" | "database";
  timeout?: string;
  fallback?: string;
}

export interface ExternalAtomSpec extends AtomSpecBase {
  execution_type: "external";
  external_integration: ExternalIntegration;
}

export type AtomSpec =
  | AgentAtomSpec
  | HumanAtomSpec
  | ToolAtomSpec
  | ExternalAtomSpec;

// -- Cross-Branch Dependencies --

export type DependencyType = "data" | "sequencing" | "resource" | "approval";

export interface CrossBranchDependency {
  from_id: string;
  to_id: string;
  dependency_type: DependencyType;
  description: string;
  artifact?: string | null;
}

// -- Validation --

export type Severity = "error" | "warning" | "info";

export type IssueType =
  | "overlap"
  | "gap"
  | "fan_out"
  | "depth"
  | "atomicity"
  | "dependency"
  | "schema";

export interface Issue {
  severity: Severity;
  location: string;
  issue_type: IssueType;
  message: string;
}

export interface ValidationSummary {
  me_score: number;
  ce_score: number;
  overall_score: number;
  levels_assessed: number;
  total_nodes: number;
  total_atoms: number;
  total_branches: number;
  max_depth: number;
  max_fan_out: number;
  issues: Issue[];
}

// -- Top-Level Decomposition --

export interface Decomposition {
  metadata: Metadata;
  tree: Node;
  cross_branch_dependencies: CrossBranchDependency[];
  validation_summary: ValidationSummary;
}

// -- Structured Content Types (for MCP tool results) --

export interface DecompositionContent {
  type: "decomposition";
  decomposition: Decomposition;
}

export interface ValidationContent {
  type: "validation";
  report: {
    valid: boolean;
    summary: {
      errors: number;
      warnings: number;
      info: number;
      total_nodes: number;
      total_atoms: number;
      total_branches: number;
      max_depth: number;
      max_fan_out: number;
    };
    issues: Issue[];
  };
}

export interface RefinementContent {
  type: "refinement";
  decomposition: Decomposition;
  validation: ValidationContent["report"];
}

export interface ExportContent {
  type: "export";
  code: string;
  filename: string;
}

export type StructuredContent =
  | DecompositionContent
  | ValidationContent
  | RefinementContent
  | ExportContent;
