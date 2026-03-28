"""Generate deeply nested JSON (10+ levels)."""

import random

import orjson


def _make_deep_chain(rng: random.Random, depth: int, leaf_idx: int) -> dict:
    """Build a chain of nested objects to the given depth."""
    labels = [
        "config", "system", "module", "component", "layer",
        "section", "group", "item", "detail", "spec",
        "params", "options", "settings", "metadata", "properties",
        "inner", "core", "data", "state", "context",
    ]
    node = {
        "id": leaf_idx,
        "value": f"leaf_{leaf_idx}_{rng.randint(0, 99999)}",
        "score": round(rng.random() * 100, 2),
        "active": rng.choice([True, False]),
        "description": f"Description at depth {depth} for item {leaf_idx}",
    }
    for d in range(depth - 1, -1, -1):
        label = labels[d % len(labels)]
        node = {label: node}
    return node


def generate_deep(target_size: int, seed: int = 42) -> bytes:
    """Generate JSON with deep nesting chains."""
    rng = random.Random(seed)
    depth = 15
    result = {"schema": "deep_test", "version": 1, "chains": []}
    i = 0
    while True:
        result["chains"].append(_make_deep_chain(rng, depth, i))
        i += 1
        if i % 10 == 0:
            data = orjson.dumps(result, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(result, option=orjson.OPT_INDENT_2)
