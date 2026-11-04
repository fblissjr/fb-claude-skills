"""`watch_only_urls`: pages fetched on every refresh alongside `upstream_urls`.

The two lists are fetched, hashed and snapshotted the same way; a watch-only
page is labelled as such in the report. A URL in both lists is ambiguous intent
and is reported by name rather than deduplicated. (The split existed for the
best_practices.md provenance join, retired with that file; whether to keep two
lists is part of the /maintain decision.)

Each test states what breaks if it is deleted.
"""

import httpx
import orjson
import pytest

from skill_maintainer.config import (
    ConfigError,
    get_watch_only_urls,
    get_watch_pages,
    hashes_file,
    pages_dir,
)
from skill_maintainer import upstream

TRACKED_URL = "https://code.claude.com/docs/en/skills"
WATCH_URL = "https://code.claude.com/docs/en/artifacts"
CITED_WATCH_URL = "https://code.claude.com/docs/en/channels"


def _write_config(root, cfg):
    d = root / ".skill-maintainer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_bytes(orjson.dumps(cfg))


# --- config -----------------------------------------------------------------


def test_absent_key_means_empty(tmp_path):
    # Breaks if deleted: `init`'s generated config does not carry the key, so a
    # default other than [] would start fetching pages nobody asked for.
    _write_config(tmp_path, {"upstream_urls": [TRACKED_URL]})
    assert get_watch_only_urls(tmp_path) == []
    assert get_watch_pages(tmp_path) == ([TRACKED_URL], [])


def test_url_in_both_lists_is_a_named_config_error(tmp_path):
    # Breaks if deleted: a silent dedup would decide the ambiguity one way
    # without telling anyone -- either hiding a real unattributed page or
    # pinning a citation claim the owner meant to drop.
    _write_config(tmp_path, {
        "upstream_urls": [TRACKED_URL, WATCH_URL],
        "watch_only_urls": [WATCH_URL],
    })
    with pytest.raises(ConfigError) as exc:
        get_watch_pages(tmp_path)
    assert WATCH_URL in str(exc.value)
    assert TRACKED_URL not in str(exc.value)


# --- join -------------------------------------------------------------------


# --- the test_repo_hygiene arm ---------------------------------------------


# --- skill-maintain upstream -----------------------------------------------


def _fake_llms(*urls):
    body = "\n".join(f"Source: {u}\n# {u.rsplit('/', 1)[-1]}\ncontent of {u}\n" for u in urls)

    def fake_get(url, **kwargs):
        return httpx.Response(200, text=body, request=httpx.Request("GET", url))

    return fake_get


def test_upstream_fetches_snapshots_and_labels_watch_only(tmp_path, monkeypatch, capsys):
    # Breaks if deleted: pins that watch-only pages are fetched, hashed and
    # snapshotted like tracked ones and labelled in the report.
    _write_config(tmp_path, {"upstream_urls": [TRACKED_URL], "watch_only_urls": [WATCH_URL]})
    monkeypatch.setattr(upstream.httpx, "get", _fake_llms(TRACKED_URL, WATCH_URL))

    with pytest.raises(SystemExit) as exc:
        upstream.main(["--dir", str(tmp_path), "--no-log"])
    assert exc.value.code == 0
    out = capsys.readouterr().out

    assert "Watched: 2 pages (1 watch-only)" in out
    assert "[NEW] artifacts (watch-only)" in out
    assert "[NEW] skills  (" in out
    state = orjson.loads(hashes_file(tmp_path).read_bytes())
    assert WATCH_URL in state
    assert (pages_dir(tmp_path) / "artifacts.md").exists()


def test_upstream_exits_nonzero_on_overlap_naming_the_url(tmp_path, monkeypatch, capsys):
    # Breaks if deleted: the CLI must refuse an ambiguous config before fetching
    # or writing state, and say which URL is at fault.
    _write_config(tmp_path, {
        "upstream_urls": [TRACKED_URL, WATCH_URL],
        "watch_only_urls": [WATCH_URL],
    })

    def must_not_fetch(*a, **k):
        raise AssertionError("fetched despite a config error")

    monkeypatch.setattr(upstream.httpx, "get", must_not_fetch)
    with pytest.raises(SystemExit) as exc:
        upstream.main(["--dir", str(tmp_path), "--no-log"])
    assert exc.value.code != 0
    assert WATCH_URL in capsys.readouterr().err
    assert not hashes_file(tmp_path).exists()
