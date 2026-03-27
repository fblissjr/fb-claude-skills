"""Data generation orchestrator."""

from __future__ import annotations

import os
from pathlib import Path

from schema_bench.generators import GENERATORS

# Target sizes in bytes
SIZE_TIERS: dict[str, int] = {
    "tiny": 100,
    "small": 10_000,
    "medium": 1_000_000,
    "large": 10_000_000,
    "xlarge": 100_000_000,
}


def generate_all(
    output_dir: Path,
    sizes: list[str] | None = None,
    schemas: list[str] | None = None,
    seed: int = 42,
) -> list[Path]:
    """Generate test data files.

    Returns list of generated file paths.
    """
    sizes = sizes or list(SIZE_TIERS.keys())
    schemas = schemas or list(GENERATORS.keys())
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for schema_name in schemas:
        if schema_name not in GENERATORS:
            print(f"  SKIP unknown schema: {schema_name}")
            continue
        gen_fn = GENERATORS[schema_name]
        for size_name in sizes:
            if size_name not in SIZE_TIERS:
                print(f"  SKIP unknown size: {size_name}")
                continue
            target = SIZE_TIERS[size_name]
            outpath = output_dir / f"{schema_name}_{size_name}.json"
            print(f"  Generating {schema_name}_{size_name} (target {target:,} bytes)...", end=" ", flush=True)
            data = gen_fn(target, seed=seed)
            outpath.write_bytes(data)
            actual = len(data)
            print(f"done ({actual:,} bytes)")
            generated.append(outpath)

    return generated
