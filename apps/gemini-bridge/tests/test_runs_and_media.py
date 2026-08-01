from __future__ import annotations

import datetime as dt

import orjson
import pytest

from gemini_bridge import ledger, media, runs


def test_runs_root_self_ignores(tmp_path):
    # Run directories land inside the project being analysed, which is usually
    # a git repo. They must exclude themselves without the user doing anything.
    runs.RunDir.create(tmp_path, "demo")
    ignore = tmp_path / runs.RUNS_DIRNAME / ".gitignore"
    assert ignore.is_file()
    assert ignore.read_text().strip().endswith("*")


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


def test_video_refused_until_files_api(tmp_path):
    p = tmp_path / "clip.mp4"
    p.write_bytes(b"0" * 16)
    with pytest.raises(media.MediaError, match="Files API"):
        media.to_content_block(media.inspect(p))


def test_manifest_never_carries_payload(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    entry = media.inspect(p, "high").manifest_entry()
    assert set(entry) == {"path", "kind", "mime_type", "size_bytes", "resolution"}
    assert "data" not in entry


def test_context_files_take_the_cheaper_resolution(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    for f in (a, b):
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
    atts = media.resolve_attachments([str(a)], "high", [str(b)], "low")
    assert [x.resolution for x in atts] == ["high", "low"]


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
