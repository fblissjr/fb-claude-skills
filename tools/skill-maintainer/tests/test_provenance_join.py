"""The provenance join: does a section's source page still hash as it did?

Claim: `best_practices.md` carries per-section annotations naming the upstream
page each section came from. Until now nothing read them, so the only freshness
signal on the whole file was a `last updated` date on line 1 — which says
someone edited the file, not that anyone checked it against its source.

Specimen the join exists to catch (2026-08-07): twelve of fourteen annotations
read 2026-04-19 while every cited page had moved twice, and the file-level date
read four days old and green. The gap ran seventeen days past the last fetch
before a human happened to ask.

Each test states what breaks if deleted:

- `test_moved_page_is_reported`: the whole point. Without it the join can stop
  detecting movement and every other arm still passes.
- `test_matching_hash_is_current`: the counterweight. A join that reports
  everything as moved is as useless as one that reports nothing, and is the
  more likely failure when comparison logic is edited.
- `test_section_without_hash_is_unbound`: an unverified section must not be
  silently counted as current. Silence here would recreate the original bug in
  a new place.
- `test_untracked_source_is_reported`: `agentskills.io` is cited by three
  sections and fetched by nothing. A join that ignores what it cannot see
  reports green over a blind spot.
- `test_tracked_page_cited_by_nothing`: the inverse waste — pages fetched every
  run that no section uses.
"""

from skill_maintainer.provenance import join_provenance, parse_annotations

DOC = """last updated: 2026-08-07

# best practices

## part 1

### hooks

<!-- class: harness | source: https://x.test/hooks | verified_hash: aaaa1111 | last_verified: 2026-08-07 -->

- [ ] something

### skills

<!-- class: harness | source: https://x.test/skills | last_verified: 2026-04-19 -->

- [ ] something else

### spec

<!-- class: harness | source: https://spec.test | last_verified: 2026-04-19 -->

## craft bit

<!-- class: craft | source: field-tested in a sibling repo, 2026-08-03 | last_verified: 2026-08-03 -->
"""

TRACKED = {
    "https://x.test/hooks": "aaaa1111",
    "https://x.test/skills": "bbbb2222",
    "https://x.test/orphan": "cccc3333",
}


def _join(doc=DOC, tracked=None):
    return join_provenance(parse_annotations(doc), tracked or TRACKED)


def test_parse_finds_sections_and_fields():
    anns = parse_annotations(DOC)
    by_section = {a.section: a for a in anns}
    assert "hooks" in by_section
    assert by_section["hooks"].source == "https://x.test/hooks"
    assert by_section["hooks"].verified_hash == "aaaa1111"
    assert by_section["hooks"].evidence_class == "harness"
    # A craft annotation's `source` is prose, not a URL — the real file has
    # exactly this shape ("field-tested in a sibling repo's claims-reminder
    # apparatus"). It must parse without being mistaken for a fetchable page.
    assert by_section["craft bit"].evidence_class == "craft"
    assert by_section["craft bit"].source.startswith("field-tested")


def test_moved_page_is_reported():
    """A bound section whose page hash changed is the finding."""
    tracked = dict(TRACKED, **{"https://x.test/hooks": "ffff9999"})
    result = _join(tracked=tracked)
    assert [m.section for m in result.moved] == ["hooks"]
    assert result.moved[0].verified_hash == "aaaa1111"
    assert result.moved[0].current_hash == "ffff9999"


def test_matching_hash_is_current():
    """The counterweight: an unchanged page must not be reported as moved."""
    result = _join()
    assert result.moved == []
    assert [c.section for c in result.current] == ["hooks"]


def test_section_without_hash_is_unbound():
    """No verified_hash means unverifiable — never silently 'current'."""
    result = _join()
    unbound = [u.section for u in result.unbound]
    assert "skills" in unbound
    assert "skills" not in [c.section for c in result.current]


def test_untracked_source_is_reported():
    """A cited source nothing fetches is a blind spot, not a pass."""
    result = _join()
    assert [u.section for u in result.untracked] == ["spec"]


def test_tracked_page_cited_by_nothing():
    """Pages fetched every run that no section uses are reported waste."""
    result = _join()
    assert result.uncited == ["https://x.test/orphan"]


def test_non_url_state_keys_are_not_reported_as_pages():
    """`upstream_hashes.json` is shared state, not a page list.

    `sources.py` writes tracked-repo HEAD SHAs into the same file under keys
    like `local_repos` and `skills`. Found live on first run: the join reported
    both as "tracked pages cited by nothing", which is a fabricated finding
    about state that was never a page. Callers pass only watched URLs, and the
    join refuses non-URL keys as a second line of defence.
    """
    tracked = dict(TRACKED, local_repos="deadbeef", skills="cafebabe")
    result = _join(tracked=tracked)
    assert result.uncited == ["https://x.test/orphan"]


def test_craft_sections_are_not_counted_as_gaps():
    """A craft section has no upstream by design and must not inflate any bucket.

    The fixture's craft annotation carries a prose `source`, so this arm fails
    if the class filter is dropped: the prose string would miss the tracked map
    and be reported as an untracked source — a fabricated finding. An earlier
    version of this test used a source-less craft annotation and stayed green
    under exactly that mutation, which is how it was caught.
    """
    result = _join()
    every = (
        [m.section for m in result.moved]
        + [c.section for c in result.current]
        + [u.section for u in result.unbound]
        + [u.section for u in result.untracked]
    )
    assert "craft bit" not in every
