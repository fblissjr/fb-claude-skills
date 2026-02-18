#!/usr/bin/env python3
"""
Structural validation of MECE decomposition JSON output.

Validates schema compliance, hierarchical ID consistency,
cross-branch dependency references, fan-out limits, and computes
aggregate ME/CE scores.

Usage:
    uv run scripts/validate_mece.py <path_to_json>
    uv run scripts/validate_mece.py <path_to_json> --output report.json
"""

import sys
from pathlib import Path
from typing import Any

import orjson

# -- Constants --

VALID_NODE_TYPES = {"branch", "atom"}
VALID_ORCHESTRATIONS = {"sequential", "parallel", "conditional", "loop"}
VALID_EXECUTION_TYPES = {"agent", "human", "tool", "external"}
VALID_DECOMPOSITION_DIMENSIONS = {
    "temporal",
    "functional",
    "stakeholder",
    "state",
    "input_output",
    "custom",
}
VALID_SOURCE_TYPES = {
    "sme_interview",
    "document",
    "verbal",
    "observation",
    "hybrid",
}
VALID_DEPENDENCY_TYPES = {"data", "sequencing", "resource", "approval"}
VALID_SEVERITIES = {"error", "warning", "info"}
VALID_ISSUE_TYPES = {
    "overlap",
    "gap",
    "fan_out",
    "depth",
    "atomicity",
    "dependency",
    "schema",
}
VALID_MODELS = {"haiku", "sonnet", "opus"}
VALID_INTEGRATION_METHODS = {"ask_user_question", "webhook", "manual"}
VALID_RETRY_POLICIES = {"none", "fixed", "exponential"}
VALID_PROTOCOLS = {"rest_api", "grpc", "message_queue", "file_system", "database"}

MAX_CHILDREN = 7
MIN_CHILDREN = 2
MAX_DEPTH = 5
MAX_TOOLS_PER_ATOM = 5
MAX_PROMPT_WORDS = 500
MAX_PARALLEL_FAN_OUT = 7


# -- Issue Tracking --


class ValidationReport:
    def __init__(self) -> None:
        self.issues: list[dict[str, str]] = []
        self.node_count = 0
        self.atom_count = 0
        self.branch_count = 0
        self.max_depth = 0
        self.max_fan_out = 0
        self.all_node_ids: set[str] = set()

    def add_issue(
        self, severity: str, location: str, issue_type: str, message: str
    ) -> None:
        self.issues.append(
            {
                "severity": severity,
                "location": location,
                "issue_type": issue_type,
                "message": message,
            }
        )

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i["severity"] == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i["severity"] == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i["severity"] == "info")

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.error_count == 0,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "total_nodes": self.node_count,
                "total_atoms": self.atom_count,
                "total_branches": self.branch_count,
                "max_depth": self.max_depth,
                "max_fan_out": self.max_fan_out,
            },
            "issues": self.issues,
        }


# -- Validators --


def check_required_string(
    obj: dict, key: str, location: str, report: ValidationReport
) -> bool:
    if key not in obj:
        report.add_issue("error", location, "schema", f"Missing required field: {key}")
        return False
    if not isinstance(obj[key], str):
        report.add_issue(
            "error", location, "schema", f"Field {key} must be a string"
        )
        return False
    if not obj[key].strip():
        report.add_issue(
            "error", location, "schema", f"Field {key} must not be empty"
        )
        return False
    return True


def check_required_enum(
    obj: dict,
    key: str,
    valid_values: set[str],
    location: str,
    report: ValidationReport,
) -> bool:
    if not check_required_string(obj, key, location, report):
        return False
    if obj[key] not in valid_values:
        report.add_issue(
            "error",
            location,
            "schema",
            f"Field {key} value '{obj[key]}' not in {sorted(valid_values)}",
        )
        return False
    return True


def check_string_list(
    obj: dict, key: str, location: str, report: ValidationReport, required: bool = True
) -> bool:
    if key not in obj:
        if required:
            report.add_issue(
                "error", location, "schema", f"Missing required field: {key}"
            )
            return False
        return True
    val = obj[key]
    if not isinstance(val, list):
        report.add_issue("error", location, "schema", f"Field {key} must be an array")
        return False
    for i, item in enumerate(val):
        if not isinstance(item, str):
            report.add_issue(
                "error", location, "schema", f"Field {key}[{i}] must be a string"
            )
            return False
    return True


def validate_metadata(metadata: Any, report: ValidationReport) -> None:
    location = "metadata"
    if not isinstance(metadata, dict):
        report.add_issue("error", location, "schema", "metadata must be an object")
        return

    check_required_string(metadata, "scope", location, report)
    check_required_string(metadata, "trigger", location, report)
    check_required_string(metadata, "completion_criteria", location, report)
    check_required_enum(
        metadata,
        "decomposition_dimension",
        VALID_DECOMPOSITION_DIMENSIONS,
        location,
        report,
    )
    check_required_string(metadata, "dimension_rationale", location, report)
    check_required_enum(metadata, "source_type", VALID_SOURCE_TYPES, location, report)
    check_string_list(metadata, "inclusions", location, report, required=False)
    check_string_list(metadata, "exclusions", location, report, required=False)
    check_required_string(metadata, "version", location, report)
    check_required_string(metadata, "created_at", location, report)


def validate_agent_definition(
    agent_def: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(agent_def, dict):
        report.add_issue(
            "error", location, "schema", "agent_definition must be an object"
        )
        return

    check_required_string(agent_def, "name", location, report)
    check_required_string(agent_def, "description", location, report)
    check_required_string(agent_def, "prompt", location, report)
    check_string_list(agent_def, "tools", location, report)
    check_required_enum(agent_def, "model", VALID_MODELS, location, report)
    check_required_string(agent_def, "model_rationale", location, report)

    # Check tool count
    tools = agent_def.get("tools", [])
    if isinstance(tools, list) and len(tools) > MAX_TOOLS_PER_ATOM:
        report.add_issue(
            "warning",
            location,
            "atomicity",
            f"Agent has {len(tools)} tools (max recommended: {MAX_TOOLS_PER_ATOM}). "
            "Consider splitting into multiple agents.",
        )

    # Check prompt length
    prompt = agent_def.get("prompt", "")
    if isinstance(prompt, str):
        word_count = len(prompt.split())
        if word_count > MAX_PROMPT_WORDS:
            report.add_issue(
                "warning",
                location,
                "atomicity",
                f"Agent prompt is {word_count} words (max recommended: {MAX_PROMPT_WORDS}). "
                "Consider simplifying.",
            )


def validate_human_instruction(
    instruction: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(instruction, dict):
        report.add_issue(
            "error", location, "schema", "human_instruction must be an object"
        )
        return

    check_required_string(instruction, "action", location, report)
    check_required_string(instruction, "context", location, report)
    check_required_string(instruction, "decision_criteria", location, report)
    check_required_enum(
        instruction,
        "integration_method",
        VALID_INTEGRATION_METHODS,
        location,
        report,
    )


def validate_tool_invocation(
    invocation: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(invocation, dict):
        report.add_issue(
            "error", location, "schema", "tool_invocation must be an object"
        )
        return

    check_required_string(invocation, "tool_name", location, report)
    if "parameters" not in invocation or not isinstance(
        invocation.get("parameters"), dict
    ):
        report.add_issue(
            "error", location, "schema", "tool_invocation.parameters must be an object"
        )

    if "retry_policy" in invocation:
        check_required_enum(
            invocation, "retry_policy", VALID_RETRY_POLICIES, location, report
        )


def validate_external_integration(
    integration: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(integration, dict):
        report.add_issue(
            "error", location, "schema", "external_integration must be an object"
        )
        return

    check_required_string(integration, "system", location, report)
    check_required_string(integration, "operation", location, report)
    check_required_enum(
        integration, "protocol", VALID_PROTOCOLS, location, report
    )


def validate_atom_spec(
    atom_spec: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(atom_spec, dict):
        report.add_issue("error", location, "schema", "atom_spec must be an object")
        return

    check_required_string(atom_spec, "estimated_duration", location, report)
    check_string_list(atom_spec, "inputs", location, report)
    check_string_list(atom_spec, "outputs", location, report)
    check_string_list(atom_spec, "error_modes", location, report)

    if not check_required_enum(
        atom_spec, "execution_type", VALID_EXECUTION_TYPES, location, report
    ):
        return

    exec_type = atom_spec["execution_type"]

    if exec_type == "agent":
        if "agent_definition" not in atom_spec:
            report.add_issue(
                "error",
                location,
                "schema",
                "Atom with execution_type 'agent' must have agent_definition",
            )
        else:
            validate_agent_definition(atom_spec["agent_definition"], location, report)

    elif exec_type == "human":
        if "human_instruction" not in atom_spec:
            report.add_issue(
                "error",
                location,
                "schema",
                "Atom with execution_type 'human' must have human_instruction",
            )
        else:
            validate_human_instruction(
                atom_spec["human_instruction"], location, report
            )

    elif exec_type == "tool":
        if "tool_invocation" not in atom_spec:
            report.add_issue(
                "error",
                location,
                "schema",
                "Atom with execution_type 'tool' must have tool_invocation",
            )
        else:
            validate_tool_invocation(atom_spec["tool_invocation"], location, report)

    elif exec_type == "external":
        if "external_integration" not in atom_spec:
            report.add_issue(
                "error",
                location,
                "schema",
                "Atom with execution_type 'external' must have external_integration",
            )
        else:
            validate_external_integration(
                atom_spec["external_integration"], location, report
            )


def validate_loop_spec(
    loop_spec: Any, location: str, report: ValidationReport
) -> None:
    if not isinstance(loop_spec, dict):
        report.add_issue("error", location, "schema", "loop_spec must be an object")
        return

    check_required_string(loop_spec, "iterator", location, report)
    check_required_string(loop_spec, "termination", location, report)


def validate_node(
    node: Any,
    expected_parent_id: str | None,
    expected_depth: int,
    report: ValidationReport,
) -> None:
    if not isinstance(node, dict):
        report.add_issue("error", "tree", "schema", "Node must be an object")
        return

    node_id = node.get("id", "<missing>")
    location = f"node:{node_id}"

    report.node_count += 1

    # Common fields
    check_required_string(node, "id", location, report)
    check_required_string(node, "label", location, report)
    check_required_string(node, "description", location, report)

    if not check_required_enum(node, "node_type", VALID_NODE_TYPES, location, report):
        return

    # Track node ID
    if node_id in report.all_node_ids:
        report.add_issue(
            "error", location, "schema", f"Duplicate node ID: {node_id}"
        )
    report.all_node_ids.add(node_id)

    # Check depth
    actual_depth = node.get("depth")
    if actual_depth is None:
        report.add_issue("error", location, "schema", "Missing required field: depth")
    elif actual_depth != expected_depth:
        report.add_issue(
            "error",
            location,
            "schema",
            f"Depth mismatch: declared {actual_depth}, expected {expected_depth}",
        )

    if expected_depth > report.max_depth:
        report.max_depth = expected_depth

    if expected_depth > MAX_DEPTH:
        report.add_issue(
            "warning",
            location,
            "depth",
            f"Node depth {expected_depth} exceeds recommended max of {MAX_DEPTH}",
        )

    # Check parent_id
    actual_parent = node.get("parent_id")
    if actual_parent != expected_parent_id:
        report.add_issue(
            "error",
            location,
            "schema",
            f"Parent ID mismatch: declared '{actual_parent}', "
            f"expected '{expected_parent_id}'",
        )

    # Check hierarchical ID consistency
    if expected_parent_id is not None and isinstance(node_id, str):
        if not node_id.startswith(expected_parent_id + "."):
            report.add_issue(
                "warning",
                location,
                "schema",
                f"ID '{node_id}' does not follow parent prefix pattern "
                f"'{expected_parent_id}.X'",
            )

    # Type-specific validation
    node_type = node["node_type"]

    if node_type == "branch":
        report.branch_count += 1
        validate_branch(node, node_id, expected_depth, report)
    elif node_type == "atom":
        report.atom_count += 1
        validate_atom(node, location, report)


def validate_branch(
    node: dict, node_id: str, depth: int, report: ValidationReport
) -> None:
    location = f"node:{node_id}"

    check_required_enum(
        node, "orchestration", VALID_ORCHESTRATIONS, location, report
    )
    check_required_string(node, "orchestration_rationale", location, report)

    orchestration = node.get("orchestration", "")

    if orchestration == "conditional" and "condition" not in node:
        report.add_issue(
            "warning",
            location,
            "schema",
            "Conditional branch should have a 'condition' field",
        )

    if orchestration == "loop":
        if "loop_spec" not in node:
            report.add_issue(
                "error",
                location,
                "schema",
                "Loop branch must have a 'loop_spec' field",
            )
        else:
            validate_loop_spec(node["loop_spec"], location, report)

    # Validate children
    children = node.get("children")
    if children is None:
        report.add_issue(
            "error", location, "schema", "Branch node must have 'children' array"
        )
        return

    if not isinstance(children, list):
        report.add_issue(
            "error", location, "schema", "'children' must be an array"
        )
        return

    child_count = len(children)

    if child_count < MIN_CHILDREN:
        report.add_issue(
            "error",
            location,
            "fan_out",
            f"Branch has {child_count} children (minimum: {MIN_CHILDREN})",
        )

    if child_count > MAX_CHILDREN:
        report.add_issue(
            "error",
            location,
            "fan_out",
            f"Branch has {child_count} children (maximum: {MAX_CHILDREN})",
        )

    if child_count > report.max_fan_out:
        report.max_fan_out = child_count

    # Check parallel fan-out specifically
    if orchestration == "parallel" and child_count > MAX_PARALLEL_FAN_OUT:
        report.add_issue(
            "error",
            location,
            "fan_out",
            f"Parallel branch has {child_count} children "
            f"(max parallel: {MAX_PARALLEL_FAN_OUT})",
        )

    # Branch must not have atom_spec
    if "atom_spec" in node:
        report.add_issue(
            "error", location, "schema", "Branch node must not have 'atom_spec'"
        )

    # Recurse into children
    for child in children:
        validate_node(child, node_id, depth + 1, report)


def validate_atom(node: dict, location: str, report: ValidationReport) -> None:
    # Atom must have atom_spec
    if "atom_spec" not in node:
        report.add_issue(
            "error", location, "schema", "Atom node must have 'atom_spec'"
        )
    else:
        validate_atom_spec(node["atom_spec"], location, report)

    # Atom must not have children
    if "children" in node:
        report.add_issue(
            "error", location, "schema", "Atom node must not have 'children'"
        )


def validate_dependencies(
    dependencies: Any, report: ValidationReport
) -> None:
    if not isinstance(dependencies, list):
        report.add_issue(
            "error",
            "cross_branch_dependencies",
            "schema",
            "cross_branch_dependencies must be an array",
        )
        return

    for i, dep in enumerate(dependencies):
        location = f"dependency[{i}]"

        if not isinstance(dep, dict):
            report.add_issue("error", location, "schema", "Dependency must be an object")
            continue

        check_required_string(dep, "from_id", location, report)
        check_required_string(dep, "to_id", location, report)
        check_required_enum(
            dep, "dependency_type", VALID_DEPENDENCY_TYPES, location, report
        )
        check_required_string(dep, "description", location, report)

        # Check that referenced IDs exist in the tree
        from_id = dep.get("from_id", "")
        to_id = dep.get("to_id", "")

        if from_id and from_id not in report.all_node_ids:
            report.add_issue(
                "error",
                location,
                "dependency",
                f"from_id '{from_id}' does not reference a valid node",
            )

        if to_id and to_id not in report.all_node_ids:
            report.add_issue(
                "error",
                location,
                "dependency",
                f"to_id '{to_id}' does not reference a valid node",
            )

        # Check self-reference
        if from_id and from_id == to_id:
            report.add_issue(
                "error",
                location,
                "dependency",
                f"Self-referencing dependency: '{from_id}' -> '{to_id}'",
            )

        # Check that from and to are in different branches (cross-branch)
        if from_id and to_id and from_id in report.all_node_ids and to_id in report.all_node_ids:
            from_parts = from_id.split(".")
            to_parts = to_id.split(".")
            if len(from_parts) > 1 and len(to_parts) > 1 and from_parts[0] == to_parts[0]:
                # Same top-level branch -- may not be cross-branch
                # Only warn if they share the same immediate parent
                if len(from_parts) >= 2 and len(to_parts) >= 2:
                    from_parent = ".".join(from_parts[:-1])
                    to_parent = ".".join(to_parts[:-1])
                    if from_parent == to_parent:
                        report.add_issue(
                            "info",
                            location,
                            "dependency",
                            f"Dependency between siblings ({from_id} -> {to_id}) "
                            "-- this is intra-branch, not cross-branch. "
                            "Consider using orchestration order instead.",
                        )


def validate_validation_summary(
    summary: Any, report: ValidationReport
) -> None:
    location = "validation_summary"
    if not isinstance(summary, dict):
        report.add_issue(
            "error", location, "schema", "validation_summary must be an object"
        )
        return

    for field in ["me_score", "ce_score", "overall_score"]:
        if field not in summary:
            report.add_issue(
                "error", location, "schema", f"Missing required field: {field}"
            )
        elif not isinstance(summary[field], (int, float)):
            report.add_issue(
                "error", location, "schema", f"Field {field} must be a number"
            )
        elif not (0.0 <= summary[field] <= 1.0):
            report.add_issue(
                "warning",
                location,
                "schema",
                f"Field {field} value {summary[field]} is outside 0.0-1.0 range",
            )

    for field in [
        "levels_assessed",
        "total_nodes",
        "total_atoms",
        "total_branches",
        "max_depth",
        "max_fan_out",
    ]:
        if field not in summary:
            report.add_issue(
                "error", location, "schema", f"Missing required field: {field}"
            )
        elif not isinstance(summary[field], int):
            report.add_issue(
                "error", location, "schema", f"Field {field} must be an integer"
            )

    # Validate issues array if present
    issues = summary.get("issues", [])
    if not isinstance(issues, list):
        report.add_issue(
            "error", location, "schema", "validation_summary.issues must be an array"
        )
        return

    for i, issue in enumerate(issues):
        issue_location = f"validation_summary.issues[{i}]"
        if not isinstance(issue, dict):
            report.add_issue(
                "error", issue_location, "schema", "Issue must be an object"
            )
            continue
        check_required_enum(
            issue, "severity", VALID_SEVERITIES, issue_location, report
        )
        check_required_string(issue, "location", issue_location, report)
        check_required_enum(
            issue, "issue_type", VALID_ISSUE_TYPES, issue_location, report
        )
        check_required_string(issue, "message", issue_location, report)


def cross_check_summary(
    summary: Any, report: ValidationReport
) -> None:
    """Cross-check declared validation_summary values against computed tree stats."""
    if not isinstance(summary, dict):
        return

    checks = [
        ("total_nodes", report.node_count),
        ("total_atoms", report.atom_count),
        ("total_branches", report.branch_count),
        ("max_depth", report.max_depth),
        ("max_fan_out", report.max_fan_out),
    ]

    for field, computed in checks:
        declared = summary.get(field)
        if isinstance(declared, int) and declared != computed:
            report.add_issue(
                "warning",
                "validation_summary",
                "schema",
                f"Declared {field}={declared} does not match computed value {computed}",
            )


def validate_decomposition(data: Any) -> ValidationReport:
    """Validate a complete MECE decomposition JSON document."""
    report = ValidationReport()

    if not isinstance(data, dict):
        report.add_issue("error", "root", "schema", "Root must be a JSON object")
        return report

    # Check required top-level fields
    for field in ["metadata", "tree", "cross_branch_dependencies", "validation_summary"]:
        if field not in data:
            report.add_issue(
                "error", "root", "schema", f"Missing required top-level field: {field}"
            )

    # Validate each section
    if "metadata" in data:
        validate_metadata(data["metadata"], report)

    if "tree" in data:
        validate_node(data["tree"], None, 0, report)

    # Dependencies must be validated AFTER tree (needs node IDs)
    if "cross_branch_dependencies" in data:
        validate_dependencies(data["cross_branch_dependencies"], report)

    if "validation_summary" in data:
        validate_validation_summary(data["validation_summary"], report)
        cross_check_summary(data["validation_summary"], report)

    return report


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/validate_mece.py <path_to_json> [--output report.json]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    output_path = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])

    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    try:
        raw = json_path.read_bytes()
        data = orjson.loads(raw)
    except orjson.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)

    report = validate_decomposition(data)
    result = report.to_dict()

    output_bytes = orjson.dumps(result, option=orjson.OPT_INDENT_2)

    if output_path:
        output_path.write_bytes(output_bytes)
        print(f"Validation report written to: {output_path}")
    else:
        sys.stdout.buffer.write(output_bytes)
        sys.stdout.write("\n")

    # Summary line to stderr
    status = "PASS" if result["valid"] else "FAIL"
    print(
        f"\n[{status}] "
        f"{result['summary']['errors']} errors, "
        f"{result['summary']['warnings']} warnings, "
        f"{result['summary']['info']} info | "
        f"{result['summary']['total_nodes']} nodes "
        f"({result['summary']['total_atoms']} atoms, "
        f"{result['summary']['total_branches']} branches) | "
        f"max depth: {result['summary']['max_depth']}, "
        f"max fan-out: {result['summary']['max_fan_out']}",
        file=sys.stderr,
    )

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
