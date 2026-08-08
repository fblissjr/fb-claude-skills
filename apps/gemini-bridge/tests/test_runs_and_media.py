from __future__ import annotations

import datetime as dt
from dataclasses import replace

import orjson
import pytest

from gemini_bridge import cli, ledger, media, runs


def test_runs_root_self_ignores(tmp_path):
    # Run directories land inside the project being analysed, which is usually
    # a git repo. They must exclude themselves without the user doing anything.
    runs.RunDir.create(tmp_path, "demo")
    ignore = tmp_path / runs.RUNS_DIRNAME / ".gitignore"
    assert ignore.is_file()
    assert ignore.read_text().strip().endswith("*")


def test_ignore_status_reports_a_missing_marker(tmp_path):
    """The self-ignore is one file, and deleting it exposes the tree silently.

    Nothing rewrites it until the next call, so `doctor` is the only place the
    window is visible. If this predicate ever returns True for an unprotected
    tree, that report becomes a false reassurance.
    """
    assert runs.ignore_status(tmp_path) == (False, True), "no tree yet is not a fault"

    runs.RunDir.create(tmp_path, "demo")
    assert runs.ignore_status(tmp_path) == (True, True)

    (tmp_path / runs.RUNS_DIRNAME / ".gitignore").unlink()
    assert runs.ignore_status(tmp_path) == (True, False)


def test_run_dirs_do_not_collide(tmp_path):
    now = dt.datetime(2026, 8, 1, 12, 0, 0)
    a = runs.RunDir.create(tmp_path, "demo", now)
    b = runs.RunDir.create(tmp_path, "demo", now)
    assert a.path != b.path


def test_run_records_roundtrip(tmp_path):
    run = runs.RunDir.create(tmp_path, "demo")
    run.write_prompt("system text", "the question")
    run.write_response("an answer")
    run.write_structured({"identical": True})
    run.write_interaction_id("v1_abc")
    assert run.interaction_id == "v1_abc"
    assert "the question" in run.prompt_path.read_text()
    assert (run.path / "response.md").read_text() == "an answer\n"


def test_stored_runs_only_lists_ones_with_ids(tmp_path):
    stateless = runs.RunDir.create(tmp_path, "a")
    stateful = runs.RunDir.create(tmp_path, "b")
    stateful.write_interaction_id("v1_xyz")
    stored = runs.stored_runs(tmp_path)
    assert [r.path for r in stored] == [stateful.path]
    assert stateless.path not in [r.path for r in stored]


def test_classify_known_types():
    assert media.classify("image/png") == "image"
    assert media.classify("video/mp4") == "video"
    assert media.classify("audio/wav") == "audio"
    assert media.classify("application/pdf") == "document"


def test_classify_rejects_unknown():
    with pytest.raises(media.MediaError):
        media.classify("application/zip")


def test_inspect_missing_file(tmp_path):
    with pytest.raises(media.MediaError, match="not a file"):
        media.inspect(tmp_path / "nope.png")


def test_image_becomes_inline_block(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    block = media.to_content_block(media.inspect(p, "low"))
    assert block["type"] == "image"
    assert block["mime_type"] == "image/png"
    assert block["resolution"] == "low"
    assert "data" in block


def test_video_is_never_inlined_however_small(tmp_path):
    """Routing video through the Files API is a verification decision.

    Only the uri shape was probed live (probe 11); inline video is a
    hypothesis from the SDK types and nothing more. A size-based rule would
    quietly send a 2KB clip down the unproven path, so the kind decides and
    the size does not get a vote. Delete this and the first tiny test clip
    someone tries becomes the thing that discovers whether inline works.
    """
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"0" * 16)
    att = media.inspect(p)
    assert media.needs_upload(att)
    with pytest.raises(media.MediaError, match="must be uploaded"):
        media.to_content_block(att)


def test_oversized_image_routes_to_upload_too(tmp_path):
    """The cap is the second, independent reason to upload.

    Before the Files API existed this was a dead end with an apologetic error.
    It must now be a route, or a 90MB PDF is still unusable.
    """
    p = tmp_path / "huge.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    att = media.Attachment(
        path=p, kind="document", mime_type="application/pdf",
        size_bytes=media.INLINE_LIMIT_BYTES + 1,
    )
    assert media.needs_upload(att)


def test_uploaded_attachment_becomes_a_uri_block(tmp_path):
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"0" * 16)
    att = replace(media.inspect(p, "low"), uri="https://files/abc")
    block = media.to_content_block(att)
    assert block == {
        "type": "video",
        "uri": "https://files/abc",
        "mime_type": "video/mp4",
        "resolution": "low",
    }
    assert "data" not in block, "a uri block must never also carry the bytes"


def test_audio_block_carries_no_resolution(tmp_path):
    """AudioContent has no resolution field; sending one is a 400, not an
    ignored extra. The recipe-level resolution applies to every attachment,
    so an audio file inherits it unless this strips it."""
    p = tmp_path / "clip.wav"
    p.write_bytes(b"RIFF")
    att = replace(media.inspect(p, "high"), uri="https://files/xyz")
    assert "resolution" not in media.to_content_block(att)


def test_guess_kinds_ignores_what_it_cannot_place(tmp_path):
    """It runs before the guards, on paths that may not exist and may not be
    supported. Anything it cannot place is dropped, never raised -- the real
    error belongs to inspect(), where it is actionable."""
    kinds = media.guess_kinds(["a.mp4", "b.png", "c.zip", "no-extension"])
    assert kinds == ["video", "image"]


def test_manifest_never_carries_payload(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    entry = media.inspect(p, "high").manifest_entry()
    assert set(entry) == {
        "path", "kind", "mime_type", "size_bytes", "resolution", "uri",
    }
    assert "data" not in entry


def test_context_files_take_the_cheaper_resolution(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    for f in (a, b):
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
    atts = media.resolve_attachments([str(a)], "high", [str(b)], "low")
    assert [x.resolution for x in atts] == ["high", "low"]


def test_formats_covers_every_kind_media_can_classify(capsys):
    """`formats` exists so the docs do not have to copy a list that rots.

    It earns that only if it is complete. The command enumerates the four mime
    tables by hand, so adding a fifth kind to `media.py` -- the one change that
    would make it silently partial -- is exactly what this catches. A format
    listing that omits a supported kind is worse than none, because it reads as
    "not supported" rather than "not listed".
    """
    assert cli.main(["formats"]) == 0
    out = capsys.readouterr().out
    every_mime = (
        media.IMAGE_MIME | media.VIDEO_MIME | media.AUDIO_MIME | media.DOCUMENT_MIME
    )
    missing = [m for m in every_mime if m not in out]
    assert not missing, f"accepted but unlisted: {sorted(missing)}"
    for kind in {media.classify(m) for m in every_mime}:
        assert kind in out, f"{kind} is classifiable but absent from `formats`"


def test_formats_names_the_remapped_extensions(capsys):
    """The alias table is the non-obvious part -- a user whose .wav was
    rejected needs to see that the mapping exists."""
    assert cli.main(["formats"]) == 0
    out = capsys.readouterr().out
    for wrong, right in media.MIME_ALIASES.items():
        assert wrong in out and right in out


def test_ledger_records_provenance_not_the_reference(tmp_path):
    path = ledger.record(
        tmp_path, run_id="r1", recipe="demo", model="m", status="completed",
        usage={"total_input_tokens": 10}, attachments=[], duration_ms=5,
        stateful=False, service_tier=None, thinking_level="minimal",
        credential_kind="key-command",
    )
    entry = orjson.loads(path.read_bytes().splitlines()[0])
    assert entry["credential_kind"] == "key-command"
    # The command names a vault and an item. It must never reach disk.
    assert "op://" not in path.read_text()


def test_ledger_survives_corrupt_lines(tmp_path):
    ledger.record(
        tmp_path, run_id="r1", recipe="demo", model="m", status="completed",
        usage={}, attachments=[], duration_ms=1, stateful=False,
        service_tier=None, thinking_level=None, credential_kind="env:X",
    )
    with (tmp_path / ledger.LEDGER_NAME).open("ab") as fh:
        fh.write(b"{not json\n")
    assert len(ledger.read(tmp_path)) == 1


def test_summarize_counts_errors_and_tokens(tmp_path):
    for status in ("completed", "failed"):
        ledger.record(
            tmp_path, run_id="r", recipe="demo", model="m", status=status,
            usage={"total_input_tokens": 100, "total_thought_tokens": 5},
            attachments=[], duration_ms=1, stateful=False, service_tier=None,
            thinking_level=None, credential_kind="env:X",
        )
    s = ledger.summarize(ledger.read(tmp_path))["demo"]
    assert s == {"calls": 2, "input": 200, "output": 0, "thought": 10, "errors": 1}
