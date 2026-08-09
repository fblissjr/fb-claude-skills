"""Video, audio, and the Files API path they travel on.

The claim under test, in one sentence: a video attaches by uploading it once,
waiting for it to become usable, sending its uri, and leaving a local handle
that can delete it again.

Each arm below pins one part of that sentence, and every one of them guards a
failure that costs something irreversible or invisible:

- Uploading is a **disclosure**, not a cache miss. Bytes reach Google before
  the interaction does, and they stay 48h. Losing the handle means losing the
  ability to take them back, so the run record and the cache are written even
  when the call after them fails.
- Reuse is keyed on **content**, so it can never serve a handle for different
  bytes -- but it can serve an expired one, which is why the server is asked
  before a cached handle is trusted.
- Waiting for ACTIVE is not optional. `upload()` returning does not mean the
  file is usable, and sending too early burns the upload.

The mocks here answer the SDK shape recorded by probe 11 in `scripts/probe.py`
(`files.upload` -> object with name/uri/mime_type; `files.get(name=)` -> object
with state; `files.delete(name=)`), which is the only shape verified live.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import orjson
import pytest

from gemini_bridge import auth, cli, files, ledger, media, prompts, runs


# -- fakes ------------------------------------------------------------------


class FakeFiles:
    """A Files API that behaves like the probed one, with the clock removed.

    `states` is the sequence returned by successive `get` calls, so a test can
    say "PROCESSING twice, then ACTIVE" without sleeping.
    """

    def __init__(self, states=("ACTIVE",), upload_error=None, mime="video/mp4"):
        self.states = list(states)
        self.upload_error = upload_error
        self.mime = mime
        self.uploaded: list[str] = []
        self.deleted: list[str] = []
        self.existing: set[str] = set()

    def upload(self, *, file):
        if self.upload_error:
            raise self.upload_error
        self.uploaded.append(file)
        name = f"files/u{len(self.uploaded)}"
        self.existing.add(name)
        return SimpleNamespace(
            name=name, uri=f"https://generativelanguage/{name}", mime_type=self.mime
        )

    def get(self, *, name):
        if name not in self.existing:
            raise RuntimeError(f"404 {name}")
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return SimpleNamespace(state=state)

    def delete(self, *, name):
        self.deleted.append(name)
        self.existing.discard(name)


def fake_client(fake_files, *, status="completed", text="fine", interaction_id=None,
                capture=None):
    class FakeInteractions:
        def create(self, **kw):
            if capture is not None:
                capture.append(kw)
            return SimpleNamespace(
                id=interaction_id, status=status, output_text=text,
                usage=SimpleNamespace(model_dump=lambda: {"total_input_tokens": 5}),
            )

    return SimpleNamespace(interactions=FakeInteractions(), files=fake_files)


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    (tmp_path / "home" / ".config").mkdir(parents=True)
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    monkeypatch.setattr(cli, "_bundled_recipe_dirs", lambda: [recipes_dir])
    monkeypatch.setattr(
        auth, "resolve",
        lambda *a, **k: auth.Credentials(api_key="fake", kind="env:TEST"),
    )
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00\x00\x00 ftypisom" + b"v" * 512)
    return SimpleNamespace(root=tmp_path, video=video)


def install(monkeypatch, client):
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=lambda **_kw: client)
    ))


def ask(project, *argv):
    return cli.main(["--project-root", str(project.root), "ask", *argv])


def run_dir(project, label="adhoc"):
    return next((project.root / runs.RUNS_DIRNAME).glob(f"*-{label}*"))


def sent_request(capture):
    assert capture, "nothing was sent"
    return capture[-1]


# -- the end-to-end path ----------------------------------------------------


def test_video_is_uploaded_and_sent_as_a_uri(project, monkeypatch):
    """The whole feature in one arm: upload, then reference, never inline."""
    ff = FakeFiles()
    capture: list[dict] = []
    install(monkeypatch, fake_client(ff, capture=capture))

    assert ask(project, "-f", str(project.video), "what happens here") == 0

    assert ff.uploaded == [str(project.video)]
    blocks = sent_request(capture)["input"]
    video_block = next(b for b in blocks if b["type"] == "video")
    assert video_block["uri"] == "https://generativelanguage/files/u1"
    assert "data" not in video_block, "the bytes must not travel twice"


def test_server_mime_type_wins_over_the_extension_sniff(project, monkeypatch):
    """Our sniffer maps .mov to video/mov because that is what the Interactions
    API accepts; the upload endpoint reports what it actually detected. The
    block must describe the file the server is holding."""
    mov = project.root / "clip.mov"
    mov.write_bytes(b"\x00\x00\x00 ftypqt  " + b"v" * 64)
    ff = FakeFiles(mime="video/quicktime")
    capture: list[dict] = []
    install(monkeypatch, fake_client(ff, capture=capture))

    assert ask(project, "-f", str(mov), "q") == 0
    block = next(b for b in sent_request(capture)["input"] if b["type"] == "video")
    assert block["mime_type"] == "video/quicktime"


def test_audio_travels_the_same_road(project, monkeypatch):
    audio = project.root / "take.wav"
    audio.write_bytes(b"RIFF" + b"a" * 128)
    ff = FakeFiles(mime="audio/wav")
    capture: list[dict] = []
    install(monkeypatch, fake_client(ff, capture=capture))

    assert ask(project, "-f", str(audio), "transcribe") == 0
    block = next(b for b in sent_request(capture)["input"] if b["type"] == "audio")
    assert block["uri"].startswith("https://")
    assert "resolution" not in block


def test_upload_waits_for_the_file_to_become_active(project, monkeypatch):
    """`upload()` returning does not mean the file is usable. Sending its uri
    while it is still PROCESSING fails the interaction after the bytes were
    already spent -- the one failure that costs the upload twice."""
    ff = FakeFiles(states=["PROCESSING", "PROCESSING", "ACTIVE"])
    slept: list[float] = []
    monkeypatch.setattr(files, "_sleep", slept.append)
    install(monkeypatch, fake_client(ff))

    assert ask(project, "-f", str(project.video), "q") == 0
    assert len(slept) == 2, "it must actually wait, not poll once and hope"


def test_a_failed_upload_state_is_not_sent(project, monkeypatch, capsys):
    ff = FakeFiles(states=["FAILED"])
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 1
    assert "FAILED" in capsys.readouterr().err


def test_processing_forever_times_out_instead_of_hanging(project, monkeypatch, capsys):
    ff = FakeFiles(states=["PROCESSING"])
    monkeypatch.setattr(files, "_sleep", lambda _s: None)
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "--upload-timeout", "0", "q") == 1
    assert "upload-timeout" in capsys.readouterr().err


# -- the disclosure record --------------------------------------------------


def test_the_handle_survives_a_failed_call(project, monkeypatch):
    """The upload happened; the interaction did not. The bytes are at Google
    for 48h regardless, so the handle that can delete them must be on disk --
    otherwise a transient API error silently orphans a 200MB video."""
    ff = FakeFiles()

    class Boom:
        def create(self, **_kw):
            raise RuntimeError("upstream exploded")

    install(monkeypatch, SimpleNamespace(interactions=Boom(), files=ff))
    assert ask(project, "-f", str(project.video), "q") == 1

    cache = files.Cache.load(project.root / runs.RUNS_DIRNAME)
    assert [u.name for u in cache.live(0)] == ["files/u1"]
    recorded = orjson.loads((run_dir(project) / "uploads.json").read_bytes())
    assert recorded[0]["name"] == "files/u1"


def test_run_directory_records_the_uri_not_the_bytes(project, monkeypatch):
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "q") == 0
    request = orjson.loads((run_dir(project) / "request.json").read_bytes())
    entry = request["input"]["attachments"][0]
    assert entry["uri"] == "https://generativelanguage/files/u1"
    assert "data" not in orjson.dumps(request).decode()


def test_an_upload_failure_is_recorded_in_the_ledger(project, monkeypatch):
    ff = FakeFiles(upload_error=RuntimeError("connection reset"))
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 1
    entry = ledger.read(project.root / runs.RUNS_DIRNAME)[0]
    assert entry["status"] == "upload_failed"
    assert "connection reset" in entry["error"]


# -- reuse ------------------------------------------------------------------


def test_identical_bytes_are_uploaded_once(project, monkeypatch):
    """The iterative case this exists for: four questions about one screen
    recording should cost one upload."""
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "first question") == 0
    assert ask(project, "-f", str(project.video), "second question") == 0
    assert len(ff.uploaded) == 1


def test_changed_bytes_get_a_new_handle(project, monkeypatch):
    """Keyed on content, so a re-render cannot be answered from the old file.
    A path-keyed cache would silently analyse the previous take."""
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 0
    project.video.write_bytes(b"\x00\x00\x00 ftypisom" + b"DIFFERENT" * 64)
    assert ask(project, "-f", str(project.video), "q") == 0
    assert len(ff.uploaded) == 2


def test_a_handle_the_server_lost_is_re_uploaded(project, monkeypatch):
    """The one staleness a content hash cannot detect: expiry, or someone
    deleting the file. Reusing it blind turns a cheap optimisation into a hard
    failure on a call that would otherwise have worked."""
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 0
    ff.existing.clear()  # expired at Google, still in our cache
    assert ask(project, "-f", str(project.video), "q") == 0
    assert len(ff.uploaded) == 2


def test_cache_will_not_offer_a_handle_near_expiry(tmp_path):
    """A file that lapses between the check and the call fails the interaction
    after the upload was skipped -- worse than re-uploading."""
    cache = files.Cache(path=tmp_path / files.CACHE_NAME)
    cache.put(files.Upload(
        name="files/old", uri="u", mime_type="video/mp4", sha256="abc",
        size_bytes=1, uploaded_at=0.0, display_name="clip.mp4",
    ))
    assert cache.get("abc", files.LIFETIME_S - files.REUSE_MARGIN_S - 1)
    assert cache.get("abc", files.LIFETIME_S - files.REUSE_MARGIN_S) is None


def test_a_corrupt_cache_is_a_cold_cache(tmp_path):
    """Losing the cache must cost an upload, never a call."""
    path = tmp_path / files.CACHE_NAME
    path.write_text("{not json")
    assert files.Cache.load(tmp_path).entries == {}


def test_cache_holds_no_paths(project, monkeypatch):
    """The runs tree is written into whatever project is being analysed. A
    full path there records the local username for no benefit the content hash
    does not already provide."""
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "q") == 0
    raw = (project.root / runs.RUNS_DIRNAME / files.CACHE_NAME).read_text()
    assert str(project.root) not in raw
    assert "clip.mp4" in raw, "the basename is kept so the list is legible"


# -- the uploads command ----------------------------------------------------


def test_uploads_lists_then_deletes(project, monkeypatch, capsys):
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 0

    assert cli.main(["--project-root", str(project.root), "uploads"]) == 0
    assert "clip.mp4" in capsys.readouterr().out

    assert cli.main(["--project-root", str(project.root), "uploads", "--delete"]) == 0
    assert ff.deleted == ["files/u1"]
    assert files.Cache.load(project.root / runs.RUNS_DIRNAME).live(0) == []


def test_a_failed_delete_keeps_the_handle(project, monkeypatch):
    """Dropped only on a confirmed delete. A handle removed optimistically
    after a failed delete is an orphan nothing can name again."""
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "q") == 0

    def boom(*, name):
        raise RuntimeError("network down")

    ff.delete = boom
    assert cli.main(["--project-root", str(project.root), "uploads", "--delete"]) == 1
    assert files.Cache.load(project.root / runs.RUNS_DIRNAME).live(0)


# -- prompts ----------------------------------------------------------------


def test_media_with_no_question_gets_a_kind_specific_default(project, monkeypatch,
                                                             capsys):
    """Refusing here is unhelpful pedantry; defaulting silently is worse. It
    does both: it runs, and it says what a contextual question would add."""
    capture: list[dict] = []
    install(monkeypatch, fake_client(FakeFiles(), capture=capture))
    assert ask(project, "-f", str(project.video)) == 0

    text = next(b for b in sent_request(capture)["input"] if b["type"] == "text")
    assert text["text"] == prompts.DEFAULTS["video"]
    err = capsys.readouterr().err
    assert "no question was given" in err
    assert "--system" in err, "the forgotten lever must be named, not implied"


def test_no_question_and_no_media_is_still_refused(project, monkeypatch, capsys):
    """The default exists because there is media to describe. With nothing
    attached there is no question to guess at."""
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project) == 1
    assert "no question" in capsys.readouterr().err


def test_an_explicit_question_is_never_replaced(project, monkeypatch):
    capture: list[dict] = []
    install(monkeypatch, fake_client(FakeFiles(), capture=capture))
    assert ask(project, "-f", str(project.video), "does the drawer overshoot?") == 0
    text = next(b for b in sent_request(capture)["input"] if b["type"] == "text")
    assert text["text"] == "does the drawer overshoot?"


def test_mixed_kinds_fall_back_to_the_generic_default():
    """The video default tells the model to timestamp everything, which is
    wrong advice for the PDF beside it."""
    assert prompts.default_question(["video", "document"]) not in (
        prompts.DEFAULTS["video"], prompts.DEFAULTS["document"],
    )


def test_video_default_asks_for_timestamps():
    """Prose about a video is nearly unusable to a caller who wants to seek to
    the moment described. This is the wording doing the work."""
    assert "MM:SS" in prompts.DEFAULTS["video"]
    assert "MM:SS" in prompts.DEFAULTS["audio"]


# -- dry run ----------------------------------------------------------------


def test_dry_run_uploads_nothing(project, monkeypatch, capsys):
    """--dry-run's promise is that nothing leaves the machine. An upload is
    the largest thing that could leave it, and it happens before the
    interaction -- so the promise has to hold one step earlier than it used
    to."""
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))
    assert ask(project, "-f", str(project.video), "--dry-run", "q") == 0
    assert ff.uploaded == []
    out = capsys.readouterr().out
    assert "upload" in out, "it must say an upload would happen"
    assert media.DRY_RUN_URI not in out, "the placeholder must never be shown"


# -- budget -----------------------------------------------------------------


def test_a_long_video_warns_before_it_is_sent(project, monkeypatch, capsys):
    """The defaults here are already the cheap ones, so the only thing that
    runs up a bill is clip length -- and that is invisible until the invoice.
    The warning has to land before the send, while it is still actionable."""
    from gemini_bridge import budget

    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 600.0)
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "q") == 0
    err = capsys.readouterr().err
    assert "estimated input tokens" in err
    assert "ffmpeg" in err, "naming the lever is the point; 'this is large' is not"


def test_a_short_clip_does_not_nag(project, monkeypatch, capsys):
    """A warning on every call is a warning nobody reads."""
    from gemini_bridge import budget

    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 8.0)
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "q") == 0
    assert "estimated input tokens" not in capsys.readouterr().err


def test_dry_run_shows_the_estimate(project, monkeypatch, capsys):
    """--dry-run is where a cost question should be answered, since it is the
    one path that promises to send nothing."""
    from gemini_bridge import budget

    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 120.0)
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "--dry-run", "q") == 0
    out = capsys.readouterr().out
    assert "2m00s" in out
    assert "estimate" in out


def test_estimate_survives_a_missing_ffprobe(project, monkeypatch):
    """ffprobe is optional. A missing local tool must never be the reason a
    paid feature stops working, so the estimate degrades to a size guess."""
    from gemini_bridge import budget

    monkeypatch.setattr(budget.shutil, "which", lambda _n: None)
    est = budget.estimate(media.inspect(project.video))
    assert est.duration_s is None
    assert est.tokens > 0


# -- mixed attachment sets --------------------------------------------------


def test_one_call_can_mix_images_and_video(project, monkeypatch):
    """Nothing about this tool is one-modality-per-call.

    Each attachment is routed on its own kind -- images inline, video by uri --
    inside a single request, and the caller does not choose or even see the
    routing. The docs used to present a table of one row per modality, which
    reads as mutually exclusive; this pins that it never was.
    """
    a, b = project.root / "before.png", project.root / "after.png"
    for p in (a, b):
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    pdf = project.root / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 32)

    ff = FakeFiles()
    capture: list[dict] = []
    install(monkeypatch, fake_client(ff, capture=capture))

    assert ask(
        project,
        "-f", str(a), "-f", str(b), "-f", str(project.video), "-f", str(pdf),
        "does the recording match the two mockups and the spec?",
    ) == 0

    blocks = sent_request(capture)["input"]
    assert [x["type"] for x in blocks] == [
        "image", "image", "video", "document", "text",
    ], "attachment order must survive, with the question last"
    assert ff.uploaded == [str(project.video)], "only the video needed uploading"
    assert all("data" in x for x in blocks if x["type"] in {"image", "document"})
    assert "uri" in blocks[2] and "data" not in blocks[2]


def test_subjects_and_context_can_be_different_kinds(project, monkeypatch):
    """-c is the lever for a mixed set: the reference material rides at the
    cheaper resolution while the subject keeps the expensive one."""
    shot = project.root / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    ff = FakeFiles()
    capture: list[dict] = []
    install(monkeypatch, fake_client(ff, capture=capture))

    assert ask(
        project, "-f", str(project.video), "-c", str(shot),
        "--resolution", "high", "--context-resolution", "low",
        "does the recording end on the state in the reference shot?",
    ) == 0

    blocks = sent_request(capture)["input"]
    assert blocks[0]["type"] == "video" and blocks[0]["resolution"] == "high"
    assert blocks[1]["type"] == "image" and blocks[1]["resolution"] == "low"


def test_a_mixed_set_gets_the_generic_default_question(project, monkeypatch):
    """The video default demands MM:SS timestamps, which is wrong advice for
    the PDF beside it. Mixed sets fall back rather than picking a winner."""
    pdf = project.root / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    capture: list[dict] = []
    install(monkeypatch, fake_client(FakeFiles(), capture=capture))

    assert ask(project, "-f", str(project.video), "-f", str(pdf)) == 0
    text = next(b for b in sent_request(capture)["input"] if b["type"] == "text")
    assert text["text"] == prompts.default_question(["video", "document"])
    assert text["text"] != prompts.DEFAULTS["video"]


# -- the spend gate, end to end ---------------------------------------------


def _authorize(tmp_path, monkeypatch, *, max_tokens=200000, ts=None):
    import time as _t
    from gemini_bridge import authorization
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    d = authorization.state_dir("s-e2e")
    d.mkdir(parents=True, exist_ok=True)
    (d / authorization.AUTH_FILENAME).write_bytes(orjson.dumps(
        {"ts": ts if ts is not None else _t.time(),
         "max_tokens": max_tokens, "origin": "user_typed_command"}
    ))


def test_an_expensive_call_is_refused_before_anything_uploads(
    project, monkeypatch, capsys, tmp_path
):
    """The gate must precede the upload, not merely the interaction.

    An upload is already a disclosure -- the bytes live at Google for 48h
    whether or not the call that followed them happened. A gate that fired
    after the upload would be protecting the cheaper half.
    """
    from gemini_bridge import budget
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 600.0)
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))

    assert ask(project, "-f", str(project.video), "q") == 1
    assert ff.uploaded == [], "nothing may leave the machine on a refused call"
    err = capsys.readouterr().err
    assert "gemini-authorize" in err
    assert "estimated input tokens" in err


def test_an_authorized_expensive_call_goes_through(
    project, monkeypatch, tmp_path
):
    from gemini_bridge import budget
    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 600.0)
    _authorize(tmp_path, monkeypatch)
    ff = FakeFiles()
    install(monkeypatch, fake_client(ff))

    assert ask(project, "-f", str(project.video), "q") == 0
    assert ff.uploaded == [str(project.video)]
    entry = ledger.read(project.root / runs.RUNS_DIRNAME)[0]
    assert entry["authorization_tier"] == "expensive-authorized"


def test_a_cheap_call_needs_no_authorization(project, monkeypatch, tmp_path):
    """The common path must not change. If a screenshot needs a slash command,
    the gate gets switched off and protects nothing."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    shot = project.root / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    install(monkeypatch, fake_client(FakeFiles()))

    assert ask(project, "-f", str(shot), "what is this") == 0
    assert ledger.read(project.root / runs.RUNS_DIRNAME)[0]["authorization_tier"] \
        == "cheap"


def test_store_is_gated_even_when_tiny(project, monkeypatch, capsys, tmp_path):
    """Irreversibility, not size. A one-line question with --store leaves an
    interaction that interactions.delete cannot remove."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "--store", "a short question") == 1
    assert "cannot be undone" in capsys.readouterr().err


def test_the_gate_can_be_turned_off_in_project_config(
    project, monkeypatch, tmp_path
):
    """It is the user's money and the user's call."""
    from gemini_bridge import budget
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 600.0)
    (project.root / ".gemini-bridge.toml").write_text(
        "[authorization]\nrequired = false\n"
    )
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "q") == 0


def test_dry_run_says_whether_the_real_call_would_be_gated(
    project, monkeypatch, capsys, tmp_path
):
    """Learning this by being refused costs a round trip. --dry-run sends
    nothing, so it is the right place to answer it."""
    from gemini_bridge import budget
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "s-e2e")
    monkeypatch.setattr(budget, "duration_seconds", lambda _a: 600.0)
    install(monkeypatch, fake_client(FakeFiles()))
    assert ask(project, "-f", str(project.video), "--dry-run", "q") == 0
    assert "gemini-authorize" in capsys.readouterr().out
