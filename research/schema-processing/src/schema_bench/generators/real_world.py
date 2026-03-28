"""Generate real-world-style JSON (GeoJSON FeatureCollection)."""

import random

import orjson


def _make_feature(rng: random.Random, idx: int) -> dict:
    """Generate a GeoJSON feature with Point or Polygon geometry."""
    if rng.random() < 0.6:
        # Point
        geometry = {
            "type": "Point",
            "coordinates": [
                round(rng.uniform(-180, 180), 6),
                round(rng.uniform(-90, 90), 6),
            ],
        }
    else:
        # Polygon (simple rectangle)
        lon = rng.uniform(-180, 179)
        lat = rng.uniform(-89, 89)
        w = rng.uniform(0.001, 0.1)
        h = rng.uniform(0.001, 0.1)
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [round(lon, 6), round(lat, 6)],
                [round(lon + w, 6), round(lat, 6)],
                [round(lon + w, 6), round(lat + h, 6)],
                [round(lon, 6), round(lat + h, 6)],
                [round(lon, 6), round(lat, 6)],
            ]],
        }

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": idx,
            "name": f"feature_{idx}",
            "description": f"A test feature at index {idx}",
            "category": rng.choice(["residential", "commercial", "industrial", "park", "water"]),
            "area_sqm": round(rng.random() * 50000, 2) if geometry["type"] == "Polygon" else None,
            "population": rng.randint(0, 50000) if rng.random() > 0.5 else None,
            "tags": [rng.choice(["urban", "rural", "suburban", "historic", "new"]) for _ in range(rng.randint(0, 3))],
        },
    }


def generate_real_world(target_size: int, seed: int = 42) -> bytes:
    """Generate a GeoJSON FeatureCollection."""
    rng = random.Random(seed)
    result = {"type": "FeatureCollection", "features": []}
    i = 0
    while True:
        result["features"].append(_make_feature(rng, i))
        i += 1
        if i % 50 == 0:
            data = orjson.dumps(result, option=orjson.OPT_INDENT_2)
            if len(data) >= target_size:
                return data
    return orjson.dumps(result, option=orjson.OPT_INDENT_2)
