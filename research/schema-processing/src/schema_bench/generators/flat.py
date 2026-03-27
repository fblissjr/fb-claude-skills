"""Generate flat key-value JSON (config-like)."""

import random

import orjson


def generate_flat(target_size: int, seed: int = 42) -> bytes:
    """Generate a flat object with alternating value types."""
    rng = random.Random(seed)
    obj = {}
    i = 0
    while True:
        key = f"key_{i:06d}"
        match i % 4:
            case 0:
                obj[key] = rng.randint(-1_000_000, 1_000_000)
            case 1:
                obj[key] = f"value_{rng.randint(0, 999999):06d}"
            case 2:
                obj[key] = rng.random() * 1000
            case 3:
                obj[key] = rng.choice([True, False])
        i += 1
        if i % 100 == 0:
            data = orjson.dumps(obj, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(obj, option=orjson.OPT_INDENT_2)
