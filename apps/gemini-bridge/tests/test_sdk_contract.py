"""Our constants against the pinned SDK's generated types.

`google-genai` is pinned exactly, because this API breaks. An exact pin is only
worth its inconvenience if bumping it *tells you what moved* -- otherwise it is
a version number nobody dares change. These arms are that signal: they fail on
the bump, naming the field that shifted, instead of the failure arriving later
as a 400 from the server on a real call someone paid for.

Everything here reads `google.genai._gaos.types.interactions`, which is
generated code and private by convention. That is deliberate and is the house
position: `_gaos` is the highest-authority *static* source for this API's
shape, above the docs and above the OpenAPI spec, both of which have been
caught omitting things it gets right. If the module path itself moves, these
arms error rather than skip -- a contract test that quietly stops running is
the failure mode being guarded against.

They pin shape, never behaviour. `temperature` is in no SDK type and the API
accepts it anyway; only `scripts/probe.py` settles that class of question.
"""

from __future__ import annotations

import typing

import pytest

from gemini_bridge import media, recipes

interactions = pytest.importorskip(
    "google.genai._gaos.types.interactions",
    reason="the pinned SDK's generated interaction types are the contract under "
           "test; if this import fails the layout moved and the pin needs review",
)


def _literals(annotation) -> set[str]:
    """The string members of a `Union[Literal[...], UnrecognizedStr]`.

    Every mime and enum type in this API is shaped that way -- the escape
    hatch is why a wrong value is not caught client-side, and why pinning the
    known set here is worth doing at all.
    """
    out: set[str] = set()
    for arg in typing.get_args(annotation):
        out |= {a for a in typing.get_args(arg) if isinstance(a, str)}
    return out


@pytest.mark.parametrize(
    "sdk_type,ours,label",
    [
        ("ImageContentMimeType", media.IMAGE_MIME, "image"),
        ("VideoContentMimeType", media.VIDEO_MIME, "video"),
        ("AudioContentMimeType", media.AUDIO_MIME, "audio"),
        ("DocumentContentMimeType", media.DOCUMENT_MIME, "document"),
    ],
)
def test_accepted_mime_types_match_the_sdk(sdk_type, ours, label):
    """Drift either way is a defect.

    A type the SDK gained and we lack is a file we refuse for no reason,
    reported to the user as "unsupported" when it is not. One we list and the
    SDK dropped is a file we accept and the server rejects, after the upload.
    """
    sdk = _literals(getattr(interactions, sdk_type))
    assert sdk == set(ours), (
        f"{label} mime drift -- sdk only: {sorted(sdk - set(ours))}, "
        f"ours only: {sorted(set(ours) - sdk)}"
    )


def test_resolution_values_match_the_sdk():
    sdk = _literals(interactions.MediaResolution)
    assert sdk == set(recipes.RESOLUTIONS)


def test_generation_config_keys_are_all_real():
    """Recipes pass these straight through into `generation_config`.

    A key that is not in the SDK's type is a 400 waiting for whoever writes the
    recipe that uses it, and the error will name the request, not the recipe.
    """
    sdk = set(interactions.GenerationConfigParam.__annotations__)
    unknown = recipes.GENERATION_CONFIG_KEYS - sdk
    assert not unknown, f"not real generation_config keys: {sorted(unknown)}"


@pytest.mark.parametrize("content_type", ["AudioContentParam", "DocumentContentParam"])
def test_audio_and_documents_still_take_no_resolution(content_type):
    """`to_content_block` strips resolution for these two kinds.

    A recipe sets one resolution for every attachment, so an audio file
    inherits it. If the SDK ever gains the field the strip becomes a silent
    downgrade rather than a correctness fix, and this says so.
    """
    fields = getattr(interactions, content_type).__annotations__
    assert "resolution" not in fields


def test_video_and_images_do_take_resolution():
    """The other half of the same claim -- without this, a strip applied to
    everything would pass the arm above and cost real quality."""
    for content_type in ("VideoContentParam", "ImageContentParam"):
        fields = getattr(interactions, content_type).__annotations__
        assert "resolution" in fields, content_type


def test_documented_model_ids_exist_in_the_sdk():
    """Docs used to name `gemini-3.6-pro`, which is in no SDK release checked.

    The `Model` type is a Literal union **plus** an `UnrecognizedStr` escape
    hatch, so a wrong id passes validation locally and fails at the server --
    the worst place to learn it. Any id this plugin recommends must be real.
    """
    known = _literals(interactions.Model)
    for model_id in (recipes.Recipe.model, "gemini-pro-latest", "gemini-flash-latest"):
        assert model_id in known, f"{model_id} is not a known model id"
