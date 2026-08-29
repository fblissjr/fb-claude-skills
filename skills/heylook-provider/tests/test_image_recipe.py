"""Executes the Pillow resize recipe exactly as it ships in client_recipes.md.

The recipe is prose, not an importable module, so nothing else can catch it
drifting. It shipped with `keep_png` reading `.format` AFTER
`ImageOps.exif_transpose`, which returns a new image whose `.format` is None --
so the check was always false, every PNG was re-encoded to JPEG, and the PNG
branch had never executed. The file's own note had labelled the image recipes
transcribed-not-executed; the label was right and the risk landed.

This exists because the fix then shipped with an unbacked claim in its place --
"executed on Pillow 12.3.0" with the run in a scratch directory that is not in
the tree, which is the same defect one file over. The claim is now recoverable:
this file IS the artifact, it extracts the code from the markdown rather than
copying it, and Pillow is pinned to the version the sentence names.

Run: uv run pytest skills/heylook-provider/tests/ -q
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

import pytest
from PIL import Image

DOC = (
    Path(__file__).resolve().parents[1]
    / "skills" / "heylook-provider" / "references" / "client_recipes.md"
)
MAX_EDGE = 2048


def _prepare_image():
    """Compile the shipped recipe. Extracting rather than copying is the whole
    point: a copy here would drift from the text it claims to verify."""
    blocks = re.findall(r"```python\n(.*?)```", DOC.read_text(), re.S)
    recipe = [b for b in blocks if "def prepare_image" in b]
    assert len(recipe) == 1, f"expected one prepare_image block, found {len(recipe)}"
    ns: dict = {}
    exec(compile(recipe[0], "client_recipes.md:prepare_image", "exec"), ns)
    return ns["prepare_image"]


def _encode(fmt: str, size: tuple[int, int], **kw) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (240, 240, 245)).save(buf, format=fmt, **kw)
    return buf.getvalue()


def _decode(data: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(data)))


@pytest.mark.parametrize("fmt,size,expect", [
    ("PNG", (3000, 1800), "image/png"),    # the regressed case: screenshot, oversized
    ("PNG", (800, 600), "image/png"),      # and below MAX_EDGE, where thumbnail no-ops
    ("JPEG", (3000, 1800), "image/jpeg"),
    ("JPEG", (800, 600), "image/jpeg"),
])
def test_format_survives_the_transform(fmt, size, expect):
    """PNG in, PNG out. The bug re-encoded every PNG to JPEG, which the
    recipe's own comment singles out as showing ringing on screenshots."""
    data, media_type = _prepare_image()(_encode(fmt, size))
    assert media_type == expect
    assert _decode(data).format == expect.split("/")[1].upper()


@pytest.mark.parametrize("size", [(3000, 1800), (800, 600)])
def test_longest_edge_is_capped_and_small_images_pass_through(size):
    data, _ = _prepare_image()(_encode("JPEG", size))
    out = _decode(data)
    assert max(out.size) <= MAX_EDGE
    if max(size) <= MAX_EDGE:
        assert out.size == size, "thumbnail must never enlarge"


def test_exif_orientation_is_applied():
    """Phone cameras store a landscape sensor read plus a rotation flag. A
    decode that ignores it hands the model a sideways image."""
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 200), (10, 20, 30))
    exif = img.getexif()
    exif[274] = 6  # rotate 90deg
    img.save(buf, format="JPEG", exif=exif)
    data, _ = _prepare_image()(buf.getvalue())
    assert _decode(data).size == (200, 400)


def test_the_recipe_reads_format_before_transforming():
    """The defect was an ORDERING one, so pin the order rather than only the
    outcome: a future edit that moves the read back below exif_transpose
    reproduces the bug while every assertion above still passes on JPEG."""
    blocks = re.findall(r"```python\n(.*?)```", DOC.read_text(), re.S)
    recipe = next(b for b in blocks if "def prepare_image" in b)
    # Anchor on the assignment and the CALL. A first draft compared bare
    # "keep_png" against "exif_transpose" and failed on correct code, because
    # the comment explaining the ordering names exif_transpose above the line
    # it is explaining.
    assert recipe.index("keep_png =") < recipe.index("ImageOps.exif_transpose(")
