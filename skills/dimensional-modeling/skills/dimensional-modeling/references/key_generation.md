last updated: 2026-02-14

# key generation

How to generate and use surrogate keys in a Kimball-style star schema.

## the two key functions

Every store needs exactly two functions:

```python
import hashlib

def dimension_key(*natural_keys) -> str:
    """MD5 surrogate key from natural key components.

    Deterministic: same inputs always produce the same key.
    NULL-safe: None values are replaced with '-1' sentinel.
    Composable: dimension_key(source_name, url) works for composite keys.
    """
    parts = [str(k) if k is not None else "-1" for k in natural_keys]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


def hash_diff(**attributes) -> str:
    """MD5 of non-key attributes for SCD Type 2 change detection.

    Pass the mutable attributes of a dimension row. If the hash changes,
    the dimension has changed and needs a new SCD Type 2 row.
    """
    parts = [f"{k}={v}" for k, v in sorted(attributes.items()) if v is not None]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
```

## natural keys vs surrogate keys

**Natural key**: the business identifier that uniquely identifies an entity in the real world.
- `source_name` for a documentation source
- `(skill_name, skill_path)` for a skill
- `(source_key, url)` for a page within a source

**Surrogate key**: the hash of the natural key, used for joins.
- `hash_key = dimension_key(source_name)` for dim_source
- `hash_key = dimension_key(skill_name)` for dim_skill
- `hash_key = dimension_key(source_key, url)` for dim_page

## why MD5?

- **Deterministic**: same natural key always produces the same surrogate. No sequence coordination between processes.
- **Portable**: keys are meaningful across databases, environments, and time. Rebuild the DB from scratch and all keys match.
- **Collision-resistant enough**: MD5 has known collision weaknesses for cryptographic use, but for surrogate key generation in a bounded domain (hundreds of dimensions, not billions), the 2^64 collision resistance is more than sufficient.
- **Compact**: 32 hex characters. Fits in TEXT columns, readable in debugging.

## composite keys

When a dimension is identified by multiple attributes, pass them all to `dimension_key`:

```python
# Page is identified by which source it belongs to AND its URL
page_key = dimension_key(source_key, page_url)

# Skill dependency is identified by parent + child
dep_key = dimension_key(parent_skill_key, child_skill_key)
```

The key function joins all parts with `|` before hashing, so `dimension_key("a", "b")` produces a different hash than `dimension_key("a|b")`.

## NULL handling

None values are replaced with the `-1` sentinel string. This ensures:
- `dimension_key("a", None)` is deterministic and consistent
- `dimension_key("a", None)` differs from `dimension_key("a", "")`
- No NULL-related surprises in hash computation

## hash_diff for change detection

`hash_diff` takes the **non-key, mutable** attributes of a dimension row. When the hash changes, SCD Type 2 kicks in.

```python
# For dim_skill, the mutable attributes are skill_path and auto_update
# skill_name is the natural key, so it's NOT in hash_diff
current_diff = hash_diff(skill_path="/new/path", auto_update=True)

# Compare to stored hash_diff
if current_diff != stored_diff:
    # Close old row, open new row (SCD Type 2)
    pass
```

**What goes in hash_diff**: attributes that, when changed, represent a meaningful business change you want to track.

**What stays out**: the natural key (it identifies the entity, doesn't describe it), timestamps, and metadata columns.

## degenerate dimensions

When the natural key IS the only interesting attribute, skip the dimension table entirely. Carry the key directly in fact rows.

Common degenerate dimensions:
- `session_id` -- UUID of the Claude Code session
- `model` -- model name (e.g., "claude-opus-4-6")
- `project_dir` -- project directory path

These appear in fact tables as plain TEXT columns. No surrogate key needed because there's no dimension table to join to.

## key design checklist

When adding a new dimension:

1. What is the natural key? (The real-world identifier)
2. Is it a single attribute or composite? (`dimension_key(a)` vs `dimension_key(a, b)`)
3. What are the mutable attributes? (These go in `hash_diff`)
4. Is it high-cardinality with no mutable attributes? (Use degenerate dimension instead)
5. Will multiple fact tables reference it? (If yes, definitely needs a full dimension table)
