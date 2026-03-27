"""Generate heterogeneous mixed JSON (arrays + objects, varying schemas)."""

import random

import orjson


def _make_event(rng: random.Random, idx: int) -> dict:
    """Generate an event with varying structure based on type."""
    event_type = rng.choice(["click", "purchase", "pageview", "error", "signup"])
    base = {
        "event_id": idx,
        "type": event_type,
        "timestamp": f"2025-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}Z",
    }
    if event_type == "click":
        base["data"] = {
            "element": rng.choice(["button", "link", "image", "card"]),
            "page": f"/page/{rng.randint(1, 100)}",
            "coordinates": {"x": rng.randint(0, 1920), "y": rng.randint(0, 1080)},
        }
    elif event_type == "purchase":
        base["data"] = {
            "items": [
                {"sku": f"SKU-{rng.randint(1000, 9999)}", "qty": rng.randint(1, 5), "price": round(rng.random() * 200, 2)}
                for _ in range(rng.randint(1, 4))
            ],
            "total": round(rng.random() * 500, 2),
            "currency": rng.choice(["USD", "EUR", "GBP"]),
        }
    elif event_type == "pageview":
        base["data"] = {
            "url": f"https://example.com/page/{rng.randint(1, 500)}",
            "referrer": rng.choice([None, "https://google.com", "https://twitter.com"]),
            "duration_s": round(rng.random() * 300, 1),
        }
    elif event_type == "error":
        base["data"] = {
            "code": rng.choice(["E001", "E002", "E003", "E_TIMEOUT", "E_AUTH"]),
            "message": f"Error occurred in module {rng.choice(['auth', 'payment', 'render'])}",
            "stack": [f"at function_{i} (file_{rng.randint(1,20)}.js:{rng.randint(1,500)})" for i in range(rng.randint(2, 6))],
        }
    else:  # signup
        base["data"] = {
            "user": {"name": f"user_{idx}", "email": f"user_{idx}@example.com"},
            "plan": rng.choice(["free", "pro", "enterprise"]),
            "source": rng.choice(["organic", "referral", "ad"]),
        }
    return base


def generate_mixed(target_size: int, seed: int = 42) -> bytes:
    """Generate mixed-schema event stream."""
    rng = random.Random(seed)
    result = {"stream": "events", "version": "1.0", "events": []}
    i = 0
    while True:
        result["events"].append(_make_event(rng, i))
        i += 1
        if i % 50 == 0:
            data = orjson.dumps(result, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(result, option=orjson.OPT_INDENT_2)
