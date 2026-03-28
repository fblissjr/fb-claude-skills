"""Query definitions with equivalent expressions per tool and schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryDef:
    name: str
    description: str
    schemas: list[str]  # which data schemas this query applies to
    jq: str | None
    jg: str | None
    jaq: str | None
    gron: str | None  # grep pattern after gron flattening
    jmespath_expr: str | None  # python jmespath expression


# Each query tests an equivalent operation across tools.
# None means the tool does not support this query pattern.
QUERIES: list[QueryDef] = [
    QueryDef(
        name="simple_field",
        description="Extract a top-level field",
        schemas=["flat", "nested", "array_heavy", "mixed", "deep", "wide", "real_world"],
        jq=".key_000000 // .api_version // .[0].timestamp // .stream // .schema // .[0]._id // .type",
        jg="key_000000 | api_version | type | stream | schema",
        jaq=".key_000000 // .api_version // .[0].timestamp // .stream // .schema // .[0]._id // .type",
        gron=r"\.key_000000\b|\.api_version\b|\.type\b|\.stream\b|\.schema\b",
        jmespath_expr="key_000000 || api_version || type || stream || schema",
    ),
    QueryDef(
        name="nested_path",
        description="Extract a nested field 3+ levels deep",
        schemas=["nested"],
        jq=".data.users[0].profile.address.city",
        jg="data.users[0].profile.address.city",
        jaq=".data.users[0].profile.address.city",
        gron=r"\.data\.users\[0\]\.profile\.address\.city",
        jmespath_expr="data.users[0].profile.address.city",
    ),
    QueryDef(
        name="recursive_descent",
        description="Find all occurrences of a key at any depth",
        schemas=["nested", "deep", "mixed"],
        jq="[.. | .description? // empty]",
        jg="(* | [*])*.description",
        jaq="[.. | .description? // empty]",
        gron=r"\.description ",
        jmespath_expr=None,  # jmespath lacks recursive descent
    ),
    QueryDef(
        name="wildcard_array",
        description="Access all elements of an array field",
        schemas=["array_heavy"],
        jq=".[].timestamp",
        jg="[*].timestamp",
        jaq=".[].timestamp",
        gron=r"\[\d+\]\.timestamp",
        jmespath_expr="[*].timestamp",
    ),
    QueryDef(
        name="array_index",
        description="Access a specific array element",
        schemas=["array_heavy", "nested"],
        jq=".[0]",
        jg="[0]",
        jaq=".[0]",
        gron=r"\[0\]",
        jmespath_expr="[0]",
    ),
    QueryDef(
        name="array_slice",
        description="Access a range of array elements",
        schemas=["array_heavy"],
        jq=".[0:5]",
        jg="[0:5]",
        jaq=".[0:5]",
        gron=None,  # gron can't natively do slices
        jmespath_expr="[0:5]",
    ),
    QueryDef(
        name="multi_field",
        description="Select multiple fields (union/alternation)",
        schemas=["nested"],
        jq=".data.users[0] | {name, email}",
        jg="data.users[0].(name | email)",
        jaq=".data.users[0] | {name, email}",
        gron=r"\.data\.users\[0\]\.(name|email)",
        jmespath_expr=None,  # jmespath multi-select is different syntax
    ),
    QueryDef(
        name="deep_nested_path",
        description="Access deeply nested field (10+ levels)",
        schemas=["deep"],
        jq=".chains[0].config.system.module.component.layer.section.group.item.detail.spec.value",
        jg="chains[0].config.system.module.component.layer.section.group.item.detail.spec.value",
        jaq=".chains[0].config.system.module.component.layer.section.group.item.detail.spec.value",
        gron=r"\.chains\[0\]\.config\.system\.module\.component\.layer\.section\.group\.item\.detail\.spec\.value",
        jmespath_expr="chains[0].config.system.module.component.layer.section.group.item.detail.spec.value",
    ),
    QueryDef(
        name="geo_all_types",
        description="Extract all geometry types from GeoJSON",
        schemas=["real_world"],
        jq=".features[].geometry.type",
        jg="features[*].geometry.type",
        jaq=".features[].geometry.type",
        gron=r"\.features\[\d+\]\.geometry\.type",
        jmespath_expr="features[*].geometry.type",
    ),
    QueryDef(
        name="geo_recursive_coords",
        description="Find all coordinates recursively in GeoJSON",
        schemas=["real_world"],
        jq="[.. | .coordinates? // empty]",
        jg="(* | [*])*.coordinates",
        jaq="[.. | .coordinates? // empty]",
        gron=r"\.coordinates",
        jmespath_expr=None,  # no recursive descent
    ),
]


def get_queries_for_schema(schema: str) -> list[QueryDef]:
    """Return queries applicable to a given schema type."""
    return [q for q in QUERIES if schema in q.schemas]


# Schema-specific overrides for simple_field (each schema has different top-level keys)
SIMPLE_FIELD_OVERRIDES: dict[str, dict[str, str | None]] = {
    "flat": {"jq": ".key_000000", "jg": "key_000000", "jaq": ".key_000000", "gron": r"\.key_000000\b", "jmespath_expr": "key_000000"},
    "nested": {"jq": ".api_version", "jg": "api_version", "jaq": ".api_version", "gron": r"\.api_version\b", "jmespath_expr": "api_version"},
    "array_heavy": {"jq": ".[0].timestamp", "jg": "[0].timestamp", "jaq": ".[0].timestamp", "gron": r"\[0\]\.timestamp", "jmespath_expr": "[0].timestamp"},
    "mixed": {"jq": ".stream", "jg": "stream", "jaq": ".stream", "gron": r"\.stream\b", "jmespath_expr": "stream"},
    "deep": {"jq": ".schema", "jg": "schema", "jaq": ".schema", "gron": r'\.schema\b', "jmespath_expr": "schema"},
    "wide": {"jq": ".[0]._id", "jg": "[0]._id", "jaq": ".[0]._id", "gron": r"\[0\]\._id", "jmespath_expr": "[0]._id"},
    "real_world": {"jq": ".type", "jg": "type", "jaq": ".type", "gron": r'^json\.type\b', "jmespath_expr": "type"},
}


def get_tool_cmd(query: QueryDef, tool: str, schema: str, filepath: str) -> str | None:
    """Build the CLI command for a given tool, query, schema, and file.

    Returns None if the tool doesn't support this query.
    """
    # Apply schema-specific overrides for simple_field
    if query.name == "simple_field" and schema in SIMPLE_FIELD_OVERRIDES:
        overrides = SIMPLE_FIELD_OVERRIDES[schema]
    else:
        overrides = None

    def _get(field: str) -> str | None:
        if overrides and field in overrides:
            return overrides[field]
        return getattr(query, field)

    if tool == "jq":
        expr = _get("jq")
        return f"jq '{expr}' {filepath}" if expr else None
    elif tool == "jg":
        expr = _get("jg")
        return f"jg '{expr}' {filepath}" if expr else None
    elif tool == "jaq":
        expr = _get("jaq")
        return f"jaq '{expr}' {filepath}" if expr else None
    elif tool == "gron":
        pattern = _get("gron")
        if pattern is None:
            return None
        return f"gron {filepath} | grep -E '{pattern}'"
    elif tool == "jmespath":
        expr = _get("jmespath_expr")
        if expr is None:
            return None
        # Use python one-liner for jmespath
        return (
            f"python3 -c \""
            f"import jmespath, json, sys; "
            f"data = json.load(open('{filepath}')); "
            f"print(json.dumps(jmespath.search('{expr}', data)))\""
        )
    return None


TOOLS = ["jq", "jg", "jaq", "gron", "jmespath"]
