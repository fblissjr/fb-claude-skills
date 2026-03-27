"""Tests for query definitions."""

import pytest

from schema_bench.queries import (
    QUERIES,
    SIMPLE_FIELD_OVERRIDES,
    TOOLS,
    get_queries_for_schema,
    get_tool_cmd,
)


def test_all_queries_have_at_least_two_tools():
    """Each query should be executable by at least 2 tools."""
    for q in QUERIES:
        tool_count = sum(1 for t in ["jq", "jg", "jaq", "gron", "jmespath_expr"]
                        if getattr(q, t if t != "jmespath_expr" else "jmespath_expr") is not None)
        assert tool_count >= 2, f"Query {q.name} has only {tool_count} tool(s)"


def test_all_queries_have_schemas():
    """Each query should apply to at least one schema."""
    for q in QUERIES:
        assert len(q.schemas) >= 1, f"Query {q.name} has no schemas"


def test_get_queries_for_schema():
    """get_queries_for_schema returns correct subset."""
    nested_queries = get_queries_for_schema("nested")
    assert len(nested_queries) > 0
    for q in nested_queries:
        assert "nested" in q.schemas


def test_simple_field_has_overrides_for_all_schemas():
    """simple_field query should have per-schema overrides."""
    sf = next(q for q in QUERIES if q.name == "simple_field")
    for schema in sf.schemas:
        assert schema in SIMPLE_FIELD_OVERRIDES, f"No override for {schema}"


def test_get_tool_cmd_returns_string_or_none():
    """get_tool_cmd returns a command string or None."""
    for q in QUERIES:
        for schema in q.schemas:
            for tool in TOOLS:
                cmd = get_tool_cmd(q, tool, schema, "/tmp/test.json")
                assert cmd is None or isinstance(cmd, str)


def test_jq_commands_start_with_jq():
    """jq commands should start with 'jq'."""
    q = next(q for q in QUERIES if q.name == "nested_path")
    cmd = get_tool_cmd(q, "jq", "nested", "/tmp/test.json")
    assert cmd is not None
    assert cmd.startswith("jq ")


def test_jg_commands_start_with_jg():
    """jg commands should start with 'jg'."""
    q = next(q for q in QUERIES if q.name == "nested_path")
    cmd = get_tool_cmd(q, "jg", "nested", "/tmp/test.json")
    assert cmd is not None
    assert cmd.startswith("jg ")


def test_gron_commands_use_pipe():
    """gron commands should pipe through grep."""
    q = next(q for q in QUERIES if q.name == "nested_path")
    cmd = get_tool_cmd(q, "gron", "nested", "/tmp/test.json")
    assert cmd is not None
    assert "gron" in cmd
    assert "grep" in cmd
