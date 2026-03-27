"""Generate large arrays of uniform objects (log-like)."""

import random

import orjson

_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
_SERVICES = ["api-gateway", "auth-service", "user-service", "payment-service", "notification-service"]
_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
_PATHS = ["/api/v1/users", "/api/v1/orders", "/api/v1/products", "/health", "/api/v1/auth/login"]


def generate_array_heavy(target_size: int, seed: int = 42) -> bytes:
    """Generate a JSON array of log-like objects."""
    rng = random.Random(seed)
    logs = []
    i = 0
    while True:
        logs.append({
            "timestamp": f"2025-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}.{rng.randint(0,999):03d}Z",
            "level": rng.choice(_LEVELS),
            "service": rng.choice(_SERVICES),
            "message": f"Request processed in {rng.randint(1, 5000)}ms",
            "request_id": f"{rng.randint(0, 0xFFFFFFFF):08x}-{rng.randint(0, 0xFFFF):04x}",
            "method": rng.choice(_METHODS),
            "path": rng.choice(_PATHS),
            "status_code": rng.choice([200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]),
            "duration_ms": round(rng.random() * 5000, 2),
            "metadata": {
                "user_id": rng.randint(1, 100000) if rng.random() > 0.3 else None,
                "trace_id": f"trace-{rng.randint(0, 0xFFFFFFFF):08x}",
                "span_id": f"span-{rng.randint(0, 0xFFFF):04x}",
            },
        })
        i += 1
        if i % 100 == 0:
            data = orjson.dumps(logs, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(logs, option=orjson.OPT_INDENT_2)
