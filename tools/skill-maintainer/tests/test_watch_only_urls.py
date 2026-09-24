"""`watch_only_urls`: pages followed on every refresh without being a citation claim.

Claim: `upstream_urls` does two jobs at once. It says which pages to fetch, and
-- through the provenance join -- it asserts that `best_practices.md` relies on
each of them, so a fetched page no section cites lands in `unattributed`, which
the repo treats as a finding (usually a wrong citation). The owner reads more
pages than the file cites. Putting those in `upstream_urls` makes the
`unattributed` bucket permanently non-empty, and a bucket that is always full
stops being read.

`watch_only_urls` splits the jobs: fetched, hashed, snapshotted and reported
exactly like a tracked page, but excluded from `unattributed`. A section that
does cite one gets the full tracked treatment, so citing a watch-only page is
never silently unbound or untracked. A URL in both lists is ambiguous intent
and is reported by name rather than deduplicated.

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
    record_fetch,
)
from skill_maintainer.provenance import format_report, join_provenance, parse_annotations
from skill_maintainer.tests import test_repo_hygiene as run_repo_hygiene_checks
from skill_maintainer import upstream

TRACKED_URL = "https://code.claude.com/docs/en/skills"
WATCH_URL = "https://code.claude.com/docs/en/artifacts"
CITED_WATCH_URL = "https://code.claude.com/docs/en/channels"


def _write_config(root, cfg):
    d = root / ".skill-maintainer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_bytes(orjson.dumps(cfg))


def _write_best_practices(root, content):
    d = root / ".skill-maintainer"
    d.mkdir(parents=True, exist_ok=True)
    (d / "best_practices.md").write_text(content, encoding="utf-8")


def _write_hashes(root, hashes):
    d = root / ".skill-maintainer" / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / "upstream_hashes.json").write_bytes(orjson.dumps(hashes))


def _ann(section, url, verified_hash):
    return (
        f"## {section}\n"
        f"<!-- class: harness | source: {url} | verified_hash: {verified_hash} "
        f"| last_verified: 2026-09-24 -->\n"
    )


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


def test_uncited_watch_only_page_is_not_unattributed():
    # Breaks if deleted: the feature's whole purpose. Without it a watch-only
    # page falls back into `unattributed` and the bucket fills with non-findings.
    doc = _ann("skills", TRACKED_URL, "aaaa")
    hashes = {TRACKED_URL: "aaaa", WATCH_URL: "bbbb"}
    result = join_provenance(parse_annotations(doc), hashes, watch_only=[WATCH_URL])
    assert result.unattributed == []
    assert result.watch_only == [WATCH_URL]
    report = format_report(result)
    assert "0 fetched-but-unattributed" in report
    assert "1 watch-only" in report


def test_cited_watch_only_page_binds_like_a_tracked_page():
    # Breaks if deleted: citing a watch-only page must not go dark. A join that
    # dropped watch-only hashes would report the section `untracked`, and one
    # that skipped them entirely would never report it `moved`.
    doc = _ann("channels ok", CITED_WATCH_URL, "cccc") + _ann("channels old", CITED_WATCH_URL, "0000")
    hashes = {CITED_WATCH_URL: "cccc"}
    result = join_provenance(parse_annotations(doc), hashes, watch_only=[CITED_WATCH_URL])
    assert [f.section for f in result.current] == ["channels ok"]
    assert [f.section for f in result.moved] == ["channels old"]
    assert result.untracked == []
    # Cited, so it is an ordinary tracked page now -- not counted as watch-only.
    assert result.watch_only == []


# --- the test_repo_hygiene arm ---------------------------------------------


def test_repo_arm_scopes_to_the_same_page_set_as_upstream(tmp_path):
    # Breaks if deleted: the arm and `upstream.py` must agree on the page set.
    # An arm reading only `upstream_urls` would call a cited watch-only page an
    # untracked source; one that ignored `watch_only_urls` would list the
    # uncited one as unattributed.
    _write_config(tmp_path, {
        "upstream_urls": [TRACKED_URL],
        "watch_only_urls": [WATCH_URL, CITED_WATCH_URL],
    })
    _write_hashes(tmp_path, {TRACKED_URL: "aaaa", WATCH_URL: "bbbb", CITED_WATCH_URL: "cccc"})
    _write_best_practices(tmp_path, _ann("skills", TRACKED_URL, "aaaa") + _ann("channels", CITED_WATCH_URL, "cccc"))
    record_fetch(tmp_path)
    prov = {r.check: r for r in run_repo_hygiene_checks(tmp_path)}["best_practices provenance"]
    assert prov.passed, prov.detail
    assert "2 current" in prov.detail
    assert "0 untracked source" in prov.detail
    assert "0 unattributed" in prov.detail
    assert "1 watch-only" in prov.detail


def test_repo_arm_fails_on_overlap_and_names_the_url(tmp_path):
    # Breaks if deleted: `test_repo_hygiene` has no exception boundary, so the
    # ConfigError must become a failing row naming the URL -- not a crash that
    # takes out every other repo arm, and not a quiet pass.
    _write_config(tmp_path, {
        "upstream_urls": [TRACKED_URL, WATCH_URL],
        "watch_only_urls": [WATCH_URL],
    })
    _write_hashes(tmp_path, {TRACKED_URL: "aaaa", WATCH_URL: "bbbb"})
    _write_best_practices(tmp_path, _ann("skills", TRACKED_URL, "aaaa"))
    prov = {r.check: r for r in run_repo_hygiene_checks(tmp_path)}["best_practices provenance"]
    assert not prov.passed
    assert WATCH_URL in prov.detail


# --- skill-maintain upstream -----------------------------------------------


def _fake_llms(*urls):
    body = "\n".join(f"Source: {u}\n# {u.rsplit('/', 1)[-1]}\ncontent of {u}\n" for u in urls)

    def fake_get(url, **kwargs):
        return httpx.Response(200, text=body, request=httpx.Request("GET", url))

    return fake_get


def test_upstream_fetches_snapshots_and_labels_watch_only(tmp_path, monkeypatch, capsys):
    # Breaks if deleted: pins that watch-only pages are fetched, hashed and
    # snapshotted like tracked ones, labelled in the report, and kept out of
    # the provenance summary's unattributed count on the real CLI path.
    _write_config(tmp_path, {"upstream_urls": [TRACKED_URL], "watch_only_urls": [WATCH_URL]})
    _write_best_practices(tmp_path, _ann("skills", TRACKED_URL, "aaaa"))
    monkeypatch.setattr(upstream.httpx, "get", _fake_llms(TRACKED_URL, WATCH_URL))

    with pytest.raises(SystemExit) as exc:
        upstream.main(["--dir", str(tmp_path), "--no-log"])
    assert exc.value.code == 0
    out = capsys.readouterr().out

    assert "Watched: 2 pages (1 watch-only)" in out
    assert "[NEW] artifacts (watch-only)" in out
    assert "[NEW] skills  (" in out
    assert "0 fetched-but-unattributed" in out
    assert "1 watch-only" in out
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
