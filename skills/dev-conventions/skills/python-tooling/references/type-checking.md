# Python type-checking gotchas

last updated: 2026-07-26

## Pydantic `str` enums

Assign enum members, never the bare string they coerce from:

```python
status = SkillStatus.ACTIVE   # not status = "active"
```

Pydantic accepts `"active"` at runtime and coerces it, so both spellings work
and the difference never shows up in tests. The coercion is invisible to
Pyright, which sees `str` where the field is typed `SkillStatus`. Using the
member is what puts the value under static analysis, so a typo like `"actve"`
fails at check time instead of becoming a validation error in whatever code
path happens to run first.

## Pydantic `Field()` defaults must be keyword arguments

```python
cache_type: str = Field(default="standard")   # Pyright sees the default
cache_type: str = Field("standard")           # Pyright treats the field as REQUIRED
```

PEP 681 `dataclass_transform` only recognises `default` passed by keyword. With
the positional form, every construction site reports "Arguments missing for
parameters", and it reads like unfixable Pydantic/Pyright noise. It is not:
measured on one real project, converting the positional sites removed 15
diagnostics, and a single missing `dict[str, Any]` annotation on a splatted test
constant accounted for 419 more. Before suppressing a wall of `reportCallIssue`,
check for these two shapes.

## Splatting an inferred `dict[str, str]`

```python
BASE: ClassVar[dict[str, Any]] = {"model_path": "/fake/model"}
Model(**BASE, temperature=0.5)
```

Without the annotation the dict infers as `dict[str, str]`, and unpacking it
into a constructor whose other fields are `int`/`float`/`bool` errors on every
one of them, at every call site. One annotation, hundreds of diagnostics.

## Pyright config precedence

`pyrightconfig.json` **always** outranks `[tool.pyright]` in `pyproject.toml`
when both exist. If a `[tool.pyright]` block appears to have no effect, look for
a `pyrightconfig.json` — including one a tool dropped there and git-excluded.
