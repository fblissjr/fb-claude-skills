"""Generate nested API-response-style JSON (3-5 levels)."""

import random

import orjson


def _make_user(rng: random.Random, idx: int) -> dict:
    return {
        "id": idx,
        "name": f"user_{idx}",
        "email": f"user_{idx}@example.com",
        "active": rng.choice([True, False]),
        "profile": {
            "bio": f"Bio for user {idx} - " + " ".join(f"word{rng.randint(0,999)}" for _ in range(10)),
            "avatar_url": f"https://example.com/avatars/{idx}.png",
            "settings": {
                "theme": rng.choice(["dark", "light", "auto"]),
                "language": rng.choice(["en", "es", "fr", "de", "ja"]),
                "notifications": {
                    "email": rng.choice([True, False]),
                    "push": rng.choice([True, False]),
                    "sms": rng.choice([True, False]),
                },
            },
            "address": {
                "street": f"{rng.randint(1, 9999)} Main St",
                "city": rng.choice(["New York", "London", "Tokyo", "Berlin", "Paris", "Sydney"]),
                "country": rng.choice(["US", "UK", "JP", "DE", "FR", "AU"]),
                "zip": f"{rng.randint(10000, 99999)}",
            },
        },
        "metadata": {
            "created_at": f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:00:00Z",
            "last_login": f"2025-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:00:00Z",
            "login_count": rng.randint(1, 5000),
            "tags": [f"tag_{rng.randint(0, 50)}" for _ in range(rng.randint(1, 5))],
        },
    }


def generate_nested(target_size: int, seed: int = 42) -> bytes:
    """Generate nested API-response JSON with users array."""
    rng = random.Random(seed)
    result = {"api_version": "2.0", "status": "ok", "data": {"users": [], "pagination": {}}}
    i = 0
    while True:
        result["data"]["users"].append(_make_user(rng, i))
        i += 1
        if i % 20 == 0:
            result["data"]["pagination"] = {
                "total": i,
                "page": 1,
                "per_page": i,
                "total_pages": 1,
            }
            data = orjson.dumps(result, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(result, option=orjson.OPT_INDENT_2)
