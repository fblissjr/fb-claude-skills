"""Generate wide JSON objects (many keys at same level)."""

import random

import orjson


def generate_wide(target_size: int, seed: int = 42) -> bytes:
    """Generate objects with many sibling keys, nested in an array."""
    rng = random.Random(seed)
    records = []
    record_idx = 0
    while True:
        record = {"_id": record_idx}
        # Each record has many fields at the same level
        num_fields = min(500, max(50, target_size // 200))
        for f in range(num_fields):
            prefix = f"field_{f:04d}"
            record[prefix] = {
                "value": rng.randint(-10000, 10000),
                "label": f"Label {f} for record {record_idx}",
                "enabled": rng.choice([True, False]),
            }
        records.append(record)
        record_idx += 1
        if record_idx % 5 == 0:
            data = orjson.dumps(records, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(records, option=orjson.OPT_INDENT_2)
