"""`upstream_urls`: the one list of docs pages `skill-maintain upstream` follows.

It held a second list, `watch_only_urls`, until 2026-11-04. The split existed
for the best_practices.md provenance join, which told a cited page from one
merely read; with the join retired the two lists behaved the same, so they
were merged. A config still carrying the old key is refused by name.

Each test states what breaks if it is deleted.
"""

import httpx
import orjson
import pytest

from skill_maintainer.config import ConfigError, get_upstream_urls, hashes_file, pages_dir
from skill_maintainer import upstream

SKILLS_URL = "https://code.claude.com/docs/en/skills"
ARTIFACTS_URL = "https://code.claude.com/docs/en/artifacts"


def _write_config(root, cfg):
    d = root / ".skill-maintainer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_bytes(orjson.dumps(cfg))


def _fake_llms(*urls):
    body = "\n".join(f"Source: {u}\n# {u.rsplit('/', 1)[-1]}\ncontent of {u}\n" for u in urls)

    def fake_get(url, **kwargs):
        return httpx.Response(200, text=body, request=httpx.Request("GET", url))

    return fake_get


def test_a_leftover_watch_only_key_is_a_named_config_error(tmp_path):
    # Breaks if deleted: reading upstream_urls alone would silently stop
    # following every page still listed under the old key.
    _write_config(tmp_path, {"upstream_urls": [SKILLS_URL], "watch_only_urls": [ARTIFACTS_URL]})
    with pytest.raises(ConfigError) as exc:
        get_upstream_urls(tmp_path)
    assert "watch_only_urls" in str(exc.value)


def test_upstream_fetches_hashes_and_snapshots_every_listed_page(tmp_path, monkeypatch, capsys):
    # Breaks if deleted: pins the CLI path end to end on a fake llms-full.txt.
    _write_config(tmp_path, {"upstream_urls": [SKILLS_URL, ARTIFACTS_URL]})
    monkeypatch.setattr(upstream.httpx, "get", _fake_llms(SKILLS_URL, ARTIFACTS_URL))

    with pytest.raises(SystemExit) as exc:
        upstream.main(["--dir", str(tmp_path), "--no-log"])
    assert exc.value.code == 0
    out = capsys.readouterr().out

    assert "Watched: 2 pages, Found: 2" in out
    assert "[NEW] artifacts  (" in out and "[NEW] skills  (" in out
    state = orjson.loads(hashes_file(tmp_path).read_bytes())
    assert SKILLS_URL in state and ARTIFACTS_URL in state
    assert (pages_dir(tmp_path) / "artifacts.md").exists()


def test_upstream_refuses_a_leftover_key_before_fetching(tmp_path, monkeypatch, capsys):
    # Breaks if deleted: the CLI must refuse the config before fetching or
    # writing state, and say what to change.
    _write_config(tmp_path, {"upstream_urls": [SKILLS_URL], "watch_only_urls": [ARTIFACTS_URL]})

    def must_not_fetch(*a, **k):
        raise AssertionError("fetched despite a config error")

    monkeypatch.setattr(upstream.httpx, "get", must_not_fetch)
    with pytest.raises(SystemExit) as exc:
        upstream.main(["--dir", str(tmp_path), "--no-log"])
    assert exc.value.code != 0
    assert "watch_only_urls" in capsys.readouterr().err
    assert not hashes_file(tmp_path).exists()
