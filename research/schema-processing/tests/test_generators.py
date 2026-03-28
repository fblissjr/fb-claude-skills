"""Tests for data generators."""

import orjson
import pytest

from schema_bench.generators import GENERATORS


@pytest.mark.parametrize("schema_name", list(GENERATORS.keys()))
def test_generator_produces_valid_json(schema_name):
    """Each generator produces valid JSON."""
    gen_fn = GENERATORS[schema_name]
    data = gen_fn(target_size=1000, seed=42)
    # Should not raise
    parsed = orjson.loads(data)
    assert parsed is not None


@pytest.mark.parametrize("schema_name", list(GENERATORS.keys()))
def test_generator_meets_target_size(schema_name):
    """Each generator produces output >= target size."""
    gen_fn = GENERATORS[schema_name]
    target = 5000
    data = gen_fn(target_size=target, seed=42)
    assert len(data) >= target, f"{schema_name}: got {len(data)} bytes, expected >= {target}"


@pytest.mark.parametrize("schema_name", list(GENERATORS.keys()))
def test_generator_is_deterministic(schema_name):
    """Same seed produces same output."""
    gen_fn = GENERATORS[schema_name]
    data1 = gen_fn(target_size=2000, seed=42)
    data2 = gen_fn(target_size=2000, seed=42)
    assert data1 == data2


@pytest.mark.parametrize("schema_name", list(GENERATORS.keys()))
def test_generator_different_seeds_differ(schema_name):
    """Different seeds produce different output."""
    gen_fn = GENERATORS[schema_name]
    data1 = gen_fn(target_size=2000, seed=42)
    data2 = gen_fn(target_size=2000, seed=99)
    assert data1 != data2


def test_flat_structure():
    """Flat generator produces a flat object."""
    data = orjson.loads(GENERATORS["flat"](target_size=1000, seed=42))
    assert isinstance(data, dict)
    # All values should be scalars
    for v in data.values():
        assert isinstance(v, (int, float, str, bool))


def test_nested_structure():
    """Nested generator produces expected API-response structure."""
    data = orjson.loads(GENERATORS["nested"](target_size=2000, seed=42))
    assert "data" in data
    assert "users" in data["data"]
    assert isinstance(data["data"]["users"], list)
    user = data["data"]["users"][0]
    assert "profile" in user
    assert "address" in user["profile"]


def test_deep_structure():
    """Deep generator produces deeply nested chains."""
    data = orjson.loads(GENERATORS["deep"](target_size=2000, seed=42))
    assert "chains" in data
    chain = data["chains"][0]
    # Should be nested 15 levels deep
    depth = 0
    node = chain
    while isinstance(node, dict) and len(node) == 1:
        key = next(iter(node))
        node = node[key]
        depth += 1
    assert depth >= 10


def test_array_heavy_structure():
    """Array heavy generator produces array of log objects."""
    data = orjson.loads(GENERATORS["array_heavy"](target_size=2000, seed=42))
    assert isinstance(data, list)
    assert "timestamp" in data[0]
    assert "level" in data[0]


def test_real_world_geojson():
    """Real world generator produces valid GeoJSON structure."""
    data = orjson.loads(GENERATORS["real_world"](target_size=2000, seed=42))
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "geometry" in feat
    assert "properties" in feat
