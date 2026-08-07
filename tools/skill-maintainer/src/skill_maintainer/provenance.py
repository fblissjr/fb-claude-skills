"""Join best_practices.md section provenance against fetched upstream hashes.

The file carries per-section annotations naming the upstream page each section
was derived from. Before this module nothing read them, so the only freshness
signal was a `last updated` date on line 1 — which establishes that someone
edited the file, not that anyone checked it against its source. On 2026-08-07
twelve of fourteen annotations read 2026-04-19 while every cited page had moved
twice, and the file-level date read four days old and green.

The join answers the question the date cannot: **has the page this section came
from changed since the section was checked against it?**

Annotation grammar, inside an HTML comment, fields separated by `|`:

    <!-- class: harness | source: <url> | verified_hash: <hex> | last_verified: <date> -->

`class` is `harness`, `model`, or `craft`. Only `harness` sections are joined —
`model` and `craft` have no upstream page by construction, and counting them as
gaps would inflate every bucket with sections that are working as intended.

`verified_hash` is the page hash the section was last checked against. It is
deliberately optional and deliberately not backfillable: a section that has
never been verified against a specific fetch reports as **unbound**, not as
current. Guessing a hash for it would manufacture the exact false confidence
this module exists to remove.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# `## x` or `### x`, capturing the title.
_HEADING = re.compile(r"^#{2,3}\s+(.*?)\s*$")
# An annotation comment; fields parsed separately so order never matters.
_ANNOTATION = re.compile(r"<!--\s*(class:.*?)\s*-->")


@dataclass(frozen=True)
class Annotation:
    section: str
    evidence_class: str
    source: str | None
    verified_hash: str | None
    last_verified: str | None


@dataclass(frozen=True)
class Finding:
    section: str
    source: str
    verified_hash: str | None = None
    current_hash: str | None = None
    last_verified: str | None = None


@dataclass
class JoinResult:
    """Every bucket is reported, including the empty ones.

    A join that printed only findings would be indistinguishable from a run that
    parsed nothing — the failure this repo calls a green that cannot state its
    scope. Callers are expected to print counts for all five.
    """

    moved: list[Finding] = field(default_factory=list)
    current: list[Finding] = field(default_factory=list)
    unbound: list[Finding] = field(default_factory=list)
    untracked: list[Finding] = field(default_factory=list)
    unattributed: list[str] = field(default_factory=list)
    """Pages fetched every run that no section cites.

    Named `unattributed`, not `uncited`, because the obvious reading of "cited
    by nothing" — delete the page — is usually the WRONG action. The bucket has
    two diagnoses with opposite remedies and identical output:

    1. The page really is unused. Drop it from `upstream_urls`.
    2. **The file asserts a fact this page documents while citing some other
       page for it.** Fix the citation; dropping the page would delete a source
       you are actually relying on and leave the bad attribution in place.

    Measured 2026-08-07, the first time the bucket was acted on: six pages
    reported, and five were case 2. `settings` is the canonical home of four
    settings keys the file asserts; `plugins-reference` states the manifest rule
    the file quotes; `plugin-marketplaces` holds the marketplace schema;
    `permissions` defines the rule syntax the `if` field uses. Only
    `discover-plugins` was case 1. A bucket whose obvious action is wrong five
    times out of six needs a name that does not suggest that action.

    Triage rule: for each page here, grep it for the terms the file asserts
    before dropping anything.
    """

    @property
    def harness_sections(self) -> int:
        return len(self.moved) + len(self.current) + len(self.unbound) + len(self.untracked)


def _parse_fields(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in blob.split("|"):
        key, sep, value = part.partition(":")
        if not sep:
            continue
        key = key.strip()
        # `source` values are URLs and contain `:` — partition on the FIRST
        # colon only, which is why partition is used rather than split(":").
        out[key] = value.strip()
    return out


def parse_annotations(text: str) -> list[Annotation]:
    """Extract one Annotation per annotation comment, tagged with its section.

    A section may carry several annotations (two source pages, or a harness line
    plus a craft line). Each becomes its own Annotation so a mixed-class section
    is represented honestly rather than collapsed to whichever line came first.
    """
    annotations: list[Annotation] = []
    section = ""
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            section = heading.group(1)
            continue
        m = _ANNOTATION.search(line)
        if not m:
            continue
        fields = _parse_fields(m.group(1))
        annotations.append(
            Annotation(
                section=section,
                evidence_class=fields.get("class", ""),
                source=fields.get("source"),
                verified_hash=fields.get("verified_hash"),
                last_verified=fields.get("last_verified"),
            )
        )
    return annotations


def join_provenance(
    annotations: list[Annotation],
    tracked: dict[str, str],
    repos: dict[str, str] | None = None,
) -> JoinResult:
    """Compare each harness annotation's source against observed state.

    Two namespaces, because a source is observable in two different ways:

    - `tracked` — `{url: content_hash}` written by `skill-maintain upstream`,
      for a fetched documentation page.
    - `repos` — `{path: head_sha}` from the `local_repos` entry
      `skill-maintain sources` writes, for a git repo cloned under `coderef/`.

    The second exists because the Agent Skills spec is a repo this project
    already clones, while its website is fetched by nothing. Three sections
    cited the website and were therefore permanently unverifiable; citing the
    repo makes them observable by the same mechanism, with a HEAD SHA standing
    in for a content hash.

    Repo hashes compare by PREFIX: state holds the full 40-character SHA and
    the annotation holds a readable short form.
    """
    # `upstream_hashes.json` is shared state: `sources.py` writes tracked-repo
    # HEAD SHAs into the same file under non-URL keys such as `local_repos`.
    # Callers pass only watched URLs; filtering here too means a caller that
    # forgets cannot turn repo state into a fabricated "page cited by nothing".
    tracked = {u: h for u, h in tracked.items() if u.startswith(("http://", "https://"))}
    repos = repos or {}

    result = JoinResult()
    cited: set[str] = set()

    for ann in annotations:
        if ann.evidence_class != "harness" or not ann.source:
            continue

        if ann.source in tracked:
            current, prefix_match = tracked[ann.source], False
        elif ann.source in repos:
            current, prefix_match = repos[ann.source], True
        else:
            result.untracked.append(
                Finding(ann.section, ann.source, ann.verified_hash, None, ann.last_verified)
            )
            continue

        cited.add(ann.source)
        finding = Finding(ann.section, ann.source, ann.verified_hash, current, ann.last_verified)
        if ann.verified_hash is None:
            result.unbound.append(finding)
            continue
        if prefix_match:
            matches = current.startswith(ann.verified_hash)
        else:
            matches = current == ann.verified_hash
        (result.current if matches else result.moved).append(finding)

    # Only pages are reported as unattributed. A tracked repo serves the whole
    # project, not just this file, so "no section cites it" is not a finding
    # about the repo.
    result.unattributed = sorted(set(tracked) - cited)
    return result


def format_report(result: JoinResult) -> str:
    """Render the join, counts first, so a green states what it covered."""
    lines = [
        f"Provenance join: {result.harness_sections} harness annotations, "
        f"{len(result.moved)} moved, {len(result.current)} current, "
        f"{len(result.unbound)} unbound, {len(result.untracked)} untracked source, "
        f"{len(result.unattributed)} fetched-but-unattributed",
    ]
    if result.moved:
        lines.append("\n  MOVED -- source changed since the section was verified:")
        for f in result.moved:
            lines.append(
                f"    {f.section}  ({f.source})  verified {f.last_verified} "
                f"@{f.verified_hash} -> now @{f.current_hash}"
            )
    if result.unbound:
        lines.append("\n  UNBOUND -- no verified_hash, so movement cannot be detected:")
        for f in result.unbound:
            lines.append(f"    {f.section}  ({f.source})  last_verified {f.last_verified}")
    if result.untracked:
        lines.append("\n  UNTRACKED SOURCE -- cited but never fetched:")
        for f in result.untracked:
            lines.append(f"    {f.section}  ({f.source})")
    if result.unattributed:
        lines.append(
            "\n  UNATTRIBUTED -- fetched every run, cited by no section. Usually the\n"
            "  citation is wrong, not the page: grep it for what the file asserts\n"
            "  before dropping anything."
        )
        for url in result.unattributed:
            lines.append(f"    {url}")
    return "\n".join(lines)
