"""Data generators for benchmark test files."""

from schema_bench.generators.flat import generate_flat
from schema_bench.generators.nested import generate_nested
from schema_bench.generators.deep import generate_deep
from schema_bench.generators.array_heavy import generate_array_heavy
from schema_bench.generators.mixed import generate_mixed
from schema_bench.generators.wide import generate_wide
from schema_bench.generators.real_world import generate_real_world

GENERATORS = {
    "flat": generate_flat,
    "nested": generate_nested,
    "deep": generate_deep,
    "array_heavy": generate_array_heavy,
    "mixed": generate_mixed,
    "wide": generate_wide,
    "real_world": generate_real_world,
}
