"""The always-on ratchet: a working-tree proxy for per-plugin always-on cost,
held to a tracked baseline that may only go down unless a commit raises it.

Written after a session trimmed a lot of always-loaded text and nothing stopped
it growing back. `claude plugin details` is the authoritative cost report but
cannot gate a commit (it reads the installed copy, cannot see uninstalled
plugins, has no JSON output, and counts hooks as zero), so the ratchet measures
the working tree instead.

Convention: each test's docstring states its claim, and a `# Breaks if deleted:`
comment says what regression would then go unnoticed. The arm tests are the
load-bearing ones -- a ratchet that cannot go red is decoration.
"""

import orjson
import pytest

from skill_maintainer import always_on
from skill_maintainer.always_on import BASELINE_PATH, MeasureError, measure

# Aliased: the source functions are named `test_*`, and pytest would collect
# them as test cases. Same reason test_repo_hygiene_provenance.py aliases.
from skill_maintainer.tests import check_always_on_ratchet
from skill_maintainer.tests import test_repo_hygiene as run_repo_hygiene_checks


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _marketplace(root, names):
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_bytes(orjson.dumps(
        {"plugins": [{"name": n, "source": f"./plugins/{n}", "version": "0.1.0"} for n in names]}
    ))


def _plugin(root, name, manifest_extra=None):
    d = root / "plugins" / name
    (d / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "version": "0.1.0"}
    manifest.update(manifest_extra or {})
    (d / ".claude-plugin" / "plugin.json").write_bytes(orjson.dumps(manifest))
    return d


def _md(path, frontmatter: dict, body="Body text.\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"] + [f"{k}: {v}" for k, v in frontmatter.items()] + ["---", "", body]
    path.write_text("\n".join(lines), encoding="utf-8")


def _skill(plugin_dir, skill, frontmatter):
    _md(plugin_dir / "skills" / skill / "SKILL.md", {"name": skill, **frontmatter})


def _hooks(path, event_map):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps({"hooks": event_map}))


def _group(n):
    """One matcher group carrying `n` handlers."""
    return {"hooks": [{"type": "command", "command": "true"} for _ in range(n)]}


def _baseline(root, data):
    p = root / BASELINE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(orjson.dumps(data))


def _ceil(listing_chars, **others):
    """A complete baseline row: every metric in METRICS, zero unless given.

    Built from METRICS so a fixture that is not about a missing key stays
    complete when a metric is added; the missing-key test writes its row out
    literally instead.
    """
    row = {m: 0 for m in always_on.METRICS}
    row.update(listing_chars=listing_chars, **others)
    return row


def _mcp(path, servers, *, wrapped=True):
    """An MCP config file declaring `servers` (names), wrapped or as a bare map."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = {n: {"command": "true"} for n in servers}
    path.write_bytes(orjson.dumps({"mcpServers": table} if wrapped else table))


def _one_plugin_repo(tmp_path, desc="a" * 10):
    """A repo with one plugin 'alpha' whose listing is exactly len(desc)."""
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _skill(d, "s", {"description": desc})
    return d


def _rows(results):
    return [r for r in results if r.check == "always-on ratchet"]


# ---------------------------------------------------------------------------
# measure(): listing_chars
# ---------------------------------------------------------------------------


def test_listing_sums_description_and_when_to_use_across_skills(tmp_path):
    """listing_chars is len(description) + len(when_to_use), summed per plugin."""
    # Breaks if deleted: when_to_use (appended to the listing upstream) could
    # drop out of the sum and a trigger-phrase dump would grow unmeasured.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _skill(d, "one", {"description": "x" * 30, "when_to_use": "y" * 12})
    _skill(d, "two", {"description": "z" * 7})
    assert measure(tmp_path)["alpha"]["listing_chars"] == 30 + 12 + 7


def test_disabled_skill_contributes_nothing(tmp_path):
    """A skill with disable-model-invocation: true never enters the listing."""
    # Breaks if deleted: the exclusion could invert or vanish; the parser
    # returns the STRING "true", so a truthiness test would also exclude
    # an explicit "false".
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _skill(d, "on", {"description": "x" * 20})
    _skill(d, "off", {"description": "y" * 500, "disable-model-invocation": "true"})
    _skill(d, "explicit", {"description": "w" * 3, "disable-model-invocation": "false"})
    assert measure(tmp_path)["alpha"]["listing_chars"] == 20 + 3


def test_agents_counted_recursively_description_only(tmp_path):
    """Plugin agents load recursively from agents/, and their description is listed."""
    # Breaks if deleted: a nested agent (agents/review/x.md) could go
    # uncounted, or an agent's body could be counted as listing text.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _md(d / "agents" / "top.md", {"name": "top", "description": "a" * 11}, body="b" * 999)
    _md(d / "agents" / "review" / "deep.md", {"name": "deep", "description": "c" * 13})
    assert measure(tmp_path)["alpha"]["listing_chars"] == 11 + 13


def test_commands_are_listed_like_skills(tmp_path):
    """commands/*.md enter the skill listing unless disable-model-invocation is set."""
    # Breaks if deleted: a command's description (the listing carries
    # `writing:voice`, a command, beside the skills) would grow unmeasured.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _md(d / "commands" / "go.md", {"description": "g" * 17})
    _md(d / "commands" / "gate.md", {"description": "h" * 40, "disable-model-invocation": "true"})
    assert measure(tmp_path)["alpha"]["listing_chars"] == 17


def test_root_skill_md_counts_only_without_a_skills_dir(tmp_path):
    """A plugin-root SKILL.md is a single-skill plugin only when skills/ is absent."""
    # Breaks if deleted: a root SKILL.md beside skills/ (which Claude Code
    # ignores) could be double-counted, or a real single-skill plugin missed.
    _marketplace(tmp_path, ["single", "both"])
    single = _plugin(tmp_path, "single")
    _md(single / "SKILL.md", {"name": "single", "description": "s" * 9})
    both = _plugin(tmp_path, "both")
    _md(both / "SKILL.md", {"name": "both", "description": "r" * 100})
    _skill(both, "inner", {"description": "i" * 5})
    got = measure(tmp_path)
    assert got["single"]["listing_chars"] == 9
    assert got["both"]["listing_chars"] == 5


def test_manifest_component_paths_are_refused_not_ignored(tmp_path):
    """A manifest `commands`/`agents`/`skills` path fails loudly rather than undercounting."""
    # Breaks if deleted: a plugin that moved its commands via plugin.json
    # would measure zero there and read as a trim.
    _marketplace(tmp_path, ["alpha"])
    _plugin(tmp_path, "alpha", {"commands": ["./extras/"]})
    with pytest.raises(MeasureError, match="commands"):
        measure(tmp_path)


# ---------------------------------------------------------------------------
# measure(): emitting_hooks, always_monitors
# ---------------------------------------------------------------------------


def test_emitting_hooks_counts_handlers_on_context_events_only(tmp_path):
    """Only SessionStart, UserPromptSubmit, UserPromptExpansion and PostModelSwitch count."""
    # Breaks if deleted: a PreToolUse handler (silent stdout) could be
    # counted, or a second SessionStart handler in one group missed.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _hooks(d / "hooks" / "hooks.json", {
        "SessionStart": [_group(2)],
        "UserPromptSubmit": [_group(1)],
        "UserPromptExpansion": [_group(1)],
        "PostModelSwitch": [_group(1)],
        "PreToolUse": [_group(3)],
        "PostToolUse": [_group(1)],
        "Stop": [_group(1)],
    })
    assert measure(tmp_path)["alpha"]["emitting_hooks"] == 5


def test_manifest_hooks_path_adds_to_default_file(tmp_path):
    """plugin.json `hooks` adds to hooks/hooks.json, and naming the default twice counts once."""
    # Breaks if deleted: a SessionStart hook moved into a manifest-declared
    # file would vanish from the count.
    _marketplace(tmp_path, ["alpha", "beta"])
    a = _plugin(tmp_path, "alpha", {"hooks": "./config/more.json"})
    _hooks(a / "hooks" / "hooks.json", {"SessionStart": [_group(1)]})
    _hooks(a / "config" / "more.json", {"UserPromptSubmit": [_group(1)]})
    b = _plugin(tmp_path, "beta", {"hooks": "./hooks/hooks.json"})
    _hooks(b / "hooks" / "hooks.json", {"SessionStart": [_group(1)]})
    got = measure(tmp_path)
    assert got["alpha"]["emitting_hooks"] == 2
    assert got["beta"]["emitting_hooks"] == 1


def test_always_monitors_counts_default_and_always(tmp_path):
    """A monitor with no `when`, or `when: always`, starts every session; on-skill-invoke does not."""
    # Breaks if deleted: a lazily started monitor could be counted as
    # always-on, or the default `when` (absent = always) missed.
    _marketplace(tmp_path, ["alpha", "beta"])
    a = _plugin(tmp_path, "alpha")
    (a / "monitors").mkdir()
    (a / "monitors" / "monitors.json").write_bytes(orjson.dumps([
        {"name": "m1", "command": "true", "description": "d"},
        {"name": "m2", "command": "true", "description": "d", "when": "always"},
        {"name": "m3", "command": "true", "description": "d", "when": "on-skill-invoke:s"},
    ]))
    # Inline experimental.monitors REPLACES the default file upstream.
    b = _plugin(tmp_path, "beta", {"experimental": {"monitors": [
        {"name": "m", "command": "true", "description": "d"},
    ]}})
    (b / "monitors").mkdir()
    (b / "monitors" / "monitors.json").write_bytes(orjson.dumps([
        {"name": "x", "command": "true", "description": "d"},
        {"name": "y", "command": "true", "description": "d"},
    ]))
    got = measure(tmp_path)
    assert got["alpha"]["always_monitors"] == 2
    assert got["beta"]["always_monitors"] == 1


# ---------------------------------------------------------------------------
# measure(): per_call_emitters, mcp_servers
# ---------------------------------------------------------------------------


def test_per_call_emitters_counts_post_tool_events_apart_from_emitting_hooks(tmp_path):
    """PostToolUse, PostToolUseFailure and PostToolBatch handlers count here, and only here."""
    # Breaks if deleted: a PostToolUse additionalContext hook (it speaks on
    # every matching tool call) could grow unmeasured, or leak into
    # emitting_hooks, whose cost scales with sessions rather than tool calls.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha", {"hooks": {"hooks": {"PostToolBatch": [_group(1)]}}})
    _hooks(d / "hooks" / "hooks.json", {
        "PostToolUse": [_group(2), _group(1)],
        "PostToolUseFailure": [_group(1)],
        "PreToolUse": [_group(4)],
        "SessionStart": [_group(1)],
        "Stop": [_group(1)],
    })
    got = measure(tmp_path)["alpha"]
    assert got["per_call_emitters"] == 2 + 1 + 1 + 1
    assert got["emitting_hooks"] == 1


def test_mcp_servers_reads_plugin_mcp_json_in_both_shapes(tmp_path):
    """`.mcp.json` counts its servers under `mcpServers`, or as a bare top-level map."""
    # Breaks if deleted: a bundled server (its tool names and instructions
    # load every session) could be added unmeasured, or a file written as a
    # bare server map read as zero servers.
    _marketplace(tmp_path, ["alpha", "beta"])
    _mcp(_plugin(tmp_path, "alpha") / ".mcp.json", ["one", "two"])
    beta = _plugin(tmp_path, "beta")
    _mcp(beta / ".mcp.json", ["solo"], wrapped=False)
    # A `$schema` key beside a bare map names no server.
    raw = orjson.loads((beta / ".mcp.json").read_bytes())
    (beta / ".mcp.json").write_bytes(orjson.dumps({"$schema": "https://example.invalid/s", **raw}))
    got = measure(tmp_path)
    assert got["alpha"]["mcp_servers"] == 2
    assert got["beta"]["mcp_servers"] == 1


def test_manifest_mcp_servers_path_list_and_inline_forms_union_by_name(tmp_path):
    """plugin.json `mcpServers` as path, list, or inline object adds to `.mcp.json`, distinct by name."""
    # Breaks if deleted: a server declared in plugin.json (the documented
    # string|array|object forms) could go uncounted, or one named in two
    # places counted twice and a later dedupe read as a trim.
    _marketplace(tmp_path, ["alpha", "beta", "gamma"])
    a = _plugin(tmp_path, "alpha", {"mcpServers": "./config/extra.json"})
    _mcp(a / ".mcp.json", ["base"])
    _mcp(a / "config" / "extra.json", ["extra", "base"])
    b = _plugin(tmp_path, "beta", {"mcpServers": [
        "./.mcp.json", "./more.json", {"inline": {"command": "true"}},
    ]})
    _mcp(b / ".mcp.json", ["base"])
    _mcp(b / "more.json", ["more"], wrapped=False)
    _plugin(tmp_path, "gamma", {"mcpServers": {"x": {"command": "true"}, "y": {"url": "https://h"}}})
    got = measure(tmp_path)
    assert got["alpha"]["mcp_servers"] == 2
    assert got["beta"]["mcp_servers"] == 3
    assert got["gamma"]["mcp_servers"] == 2


@pytest.mark.parametrize("manifest,mcp_json", [
    ({"mcpServers": "./nowhere.json"}, None),
    ({}, b'{"mcpServers": ["not", "a", "map"]}'),
    ({}, b'{"mcpServers": {"bad": "not an object"}}'),
])
def test_unreadable_mcp_declaration_is_a_measure_error(tmp_path, manifest, mcp_json):
    """A missing declared path or a mis-shaped server map fails loudly rather than counting zero."""
    # Breaks if deleted: a typo in the manifest path or a malformed
    # .mcp.json would measure as zero servers and read as a trim.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha", manifest)
    if mcp_json is not None:
        (d / ".mcp.json").write_bytes(mcp_json)
    with pytest.raises(MeasureError):
        measure(tmp_path)


# ---------------------------------------------------------------------------
# The arm
# ---------------------------------------------------------------------------


def test_arm_fails_when_a_metric_exceeds_its_ceiling(tmp_path):
    """Growth past the baseline fails, naming plugin, metric, current and ceiling."""
    # Breaks if deleted: the ratchet could stop ratcheting -- the only
    # property the whole feature exists for.
    _one_plugin_repo(tmp_path, desc="a" * 1234)
    _baseline(tmp_path, {"alpha": _ceil(1000)})
    rows = _rows(check_always_on_ratchet(tmp_path))
    failed = [r for r in rows if not r.passed]
    assert failed, [r.detail for r in rows]
    assert not [r for r in rows if r.passed], "a failing run must not also emit a PASS row"
    r = failed[0]
    assert r.name == "alpha"
    assert "listing_chars" in r.detail and "1,234" in r.detail and "1,000" in r.detail


@pytest.mark.parametrize("metric", ["mcp_servers", "per_call_emitters"])
def test_arm_fails_when_a_new_metric_exceeds_its_ceiling(tmp_path, metric):
    """mcp_servers and per_call_emitters are ratcheted like the original three."""
    # Breaks if deleted: a metric could be measured and shown in the table
    # yet left out of METRICS, so growing it never fails the arm.
    d = _one_plugin_repo(tmp_path)
    _mcp(d / ".mcp.json", ["one", "two"])
    _hooks(d / "hooks" / "hooks.json", {"PostToolUse": [_group(2)]})
    _baseline(tmp_path, {"alpha": {**_ceil(10, mcp_servers=2, per_call_emitters=2), metric: 1}})
    failed = [r for r in _rows(check_always_on_ratchet(tmp_path)) if not r.passed]
    assert len(failed) == 1, [r.detail for r in failed]
    assert failed[0].name == "alpha" and metric in failed[0].detail and "ceiling 1" in failed[0].detail


def test_arm_fails_per_plugin_when_a_baseline_entry_lacks_a_metric(tmp_path):
    """An entry written before a metric existed fails for that plugin, naming the metric and --write."""
    # Breaks if deleted: a baseline predating a metric could either pass
    # (the new metric unratcheted until someone happens to rewrite it) or
    # fail as an unreadable file that hides which plugin and key is short.
    _one_plugin_repo(tmp_path)
    _baseline(tmp_path, {"alpha": {"listing_chars": 10, "emitting_hooks": 0, "always_monitors": 0}})
    rows = _rows(check_always_on_ratchet(tmp_path))
    assert len(rows) == 1 and not rows[0].passed, [(r.passed, r.detail) for r in rows]
    r = rows[0]
    assert r.name == "alpha", r.detail
    assert "mcp_servers" in r.detail and "per_call_emitters" in r.detail, r.detail
    assert "ratchet --write" in r.detail, r.detail


def test_arm_fails_on_plugin_missing_from_baseline_and_on_stale_entry(tmp_path):
    """A new plugin's cost is a decision; a removed plugin's ceiling is dead weight."""
    # Breaks if deleted: a new plugin could land with unbounded always-on
    # cost, or a retired plugin's ceiling linger as spare headroom.
    _one_plugin_repo(tmp_path)
    _baseline(tmp_path, {"gone": _ceil(5)})
    rows = _rows(check_always_on_ratchet(tmp_path))
    by_name = {r.name: r for r in rows if not r.passed}
    assert "alpha" in by_name and "not in" in by_name["alpha"].detail
    assert "gone" in by_name and "marketplace" in by_name["gone"].detail


@pytest.mark.parametrize("content", [None, b"{not json", b'{"alpha": {"listing_chars": "ten"}}'])
def test_arm_fails_on_missing_or_unparseable_baseline(tmp_path, content):
    """No readable baseline is a failure, never a green."""
    # Breaks if deleted: deleting or corrupting the baseline file would
    # silently switch the ratchet off.
    _one_plugin_repo(tmp_path)
    if content is not None:
        p = tmp_path / BASELINE_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    rows = _rows(check_always_on_ratchet(tmp_path))
    # Exactly one file-level row. A per-plugin "not in baseline" row would
    # also be red here, but by accident: with an empty marketplace it would
    # vanish and the missing file would read green.
    assert len(rows) == 1 and not rows[0].passed, [(r.passed, r.detail) for r in rows]
    assert rows[0].name == "" and str(BASELINE_PATH) in rows[0].detail


def test_arm_pass_line_states_scope_and_headroom(tmp_path):
    """The green names plugins measured, total listing vs total ceiling, and headroom."""
    # Breaks if deleted: a green that scanned zero plugins would read the
    # same as one that scanned all, and slack left after a trim would stay
    # invisible, so nobody tightens.
    _marketplace(tmp_path, ["alpha", "beta"])
    _skill(_plugin(tmp_path, "alpha"), "s", {"description": "a" * 10})
    _skill(_plugin(tmp_path, "beta"), "s", {"description": "b" * 20})
    _baseline(tmp_path, {
        "alpha": _ceil(10),
        "beta": _ceil(25),
    })
    rows = _rows(check_always_on_ratchet(tmp_path))
    assert len(rows) == 1 and rows[0].passed, [(r.passed, r.detail) for r in rows]
    d = rows[0].detail
    assert "2 plugins" in d and "30/35" in d and "1 with headroom" in d, d


def test_arm_pass_line_totals_mcp_servers_and_per_call_emitters(tmp_path):
    """The green also carries current/ceiling totals for the two per-call and per-server metrics."""
    # Breaks if deleted: slack in the new metrics would stay invisible in the
    # one line a green run prints, so nobody tightens it.
    _marketplace(tmp_path, ["alpha"])
    d = _plugin(tmp_path, "alpha")
    _mcp(d / ".mcp.json", ["one"])
    _hooks(d / "hooks" / "hooks.json", {"PostToolUse": [_group(2)]})
    _baseline(tmp_path, {"alpha": _ceil(0, mcp_servers=3, per_call_emitters=2)})
    rows = _rows(check_always_on_ratchet(tmp_path))
    assert len(rows) == 1 and rows[0].passed, [(r.passed, r.detail) for r in rows]
    d = rows[0].detail
    assert "mcp servers 1/3" in d and "per-call hooks 2/2" in d, d


def test_measure_error_becomes_a_failing_row(tmp_path):
    """A plugin the proxy cannot read fails the arm instead of crashing the suite."""
    # Breaks if deleted: one malformed hooks.json could abort every later
    # repo arm and print no summary at all.
    _one_plugin_repo(tmp_path)
    (tmp_path / "plugins" / "alpha" / "hooks").mkdir()
    (tmp_path / "plugins" / "alpha" / "hooks" / "hooks.json").write_bytes(b"{nope")
    _baseline(tmp_path, {"alpha": _ceil(10)})
    rows = _rows(check_always_on_ratchet(tmp_path))
    assert rows and not rows[0].passed and "hooks.json" in rows[0].detail


def test_arm_is_wired_into_the_repo_category(tmp_path):
    """`skill-maintain test`'s repo category runs the ratchet."""
    # Breaks if deleted: the arm could exist, pass its own tests, and never
    # be called by the suite anyone actually runs.
    _one_plugin_repo(tmp_path)
    assert _rows(run_repo_hygiene_checks(tmp_path)), "no always-on ratchet row in the repo category"


# ---------------------------------------------------------------------------
# skill-maintain ratchet
# ---------------------------------------------------------------------------


def test_write_records_current_values_and_reports_changes(tmp_path, capsys):
    """--write sets every ceiling to the current value, sorted, and says what moved."""
    # Breaks if deleted: --write could leave the baseline unsorted (noisy
    # diffs), skip a plugin, or tighten silently so a reviewer cannot see
    # a raise in the command output.
    _marketplace(tmp_path, ["beta", "alpha"])
    _skill(_plugin(tmp_path, "alpha"), "s", {"description": "a" * 10})
    _skill(_plugin(tmp_path, "beta"), "s", {"description": "b" * 4})
    _baseline(tmp_path, {"alpha": _ceil(99)})
    with pytest.raises(SystemExit) as exc:
        always_on.main(["--dir", str(tmp_path), "--write"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "alpha" in out and "99 -> 10" in out, out
    assert "beta" in out and "added" in out, out
    raw = (tmp_path / BASELINE_PATH).read_bytes()
    data = orjson.loads(raw)
    assert list(data) == ["alpha", "beta"]
    assert data["alpha"] == {
        "always_monitors": 0, "emitting_hooks": 0, "listing_chars": 10,
        "mcp_servers": 0, "per_call_emitters": 0,
    }
    assert raw == orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    assert all(r.passed for r in _rows(check_always_on_ratchet(tmp_path)))


def test_table_shows_headroom_and_exits_red_when_over(tmp_path, capsys):
    """The read-only table prints ceiling and headroom, and exits 1 when the arm would fail."""
    # Breaks if deleted: `skill-maintain ratchet` could print a table and
    # exit 0 over a ceiling, so a script gating on it would pass.
    _one_plugin_repo(tmp_path, desc="a" * 12)
    _baseline(tmp_path, {"alpha": _ceil(10)})
    with pytest.raises(SystemExit) as exc:
        always_on.main(["--dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert exc.value.code == 1, out
    assert "alpha" in out and "-2" in out, out


def test_table_has_a_column_group_per_metric_and_tolerates_a_short_entry(tmp_path, capsys):
    """The table heads mcp and percall columns, and prints `-` where a ceiling is missing."""
    # Breaks if deleted: the table could drop the new metrics, or crash with
    # a KeyError on exactly the baseline (one predating a metric) whose
    # table the reader most needs before running --write.
    _one_plugin_repo(tmp_path)
    _baseline(tmp_path, {"alpha": {"listing_chars": 10, "emitting_hooks": 0, "always_monitors": 0}})
    with pytest.raises(SystemExit) as exc:
        always_on.main(["--dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert exc.value.code == 1, out
    header = out.splitlines()[0].split()
    assert "mcp" in header and "percall" in header, header
    assert "FAIL  alpha" in out and "mcp_servers" in out, out


def test_write_reports_a_newly_recorded_metric_as_recorded(tmp_path, capsys):
    """--write over a short entry fills the missing keys and says `recorded`, not `raised`."""
    # Breaks if deleted: the one-time migration diff would print `None -> 0
    # (raised)` lines, reading as a ceiling going up when none existed.
    _one_plugin_repo(tmp_path)
    _baseline(tmp_path, {"alpha": {"listing_chars": 10, "emitting_hooks": 0, "always_monitors": 0}})
    with pytest.raises(SystemExit):
        always_on.main(["--dir", str(tmp_path), "--write"])
    out = capsys.readouterr().out
    assert "alpha.mcp_servers: recorded 0" in out, out
    assert "raised" not in out and "None" not in out, out
    assert orjson.loads((tmp_path / BASELINE_PATH).read_bytes())["alpha"] == _ceil(10)


def test_repo_without_a_marketplace_gets_no_row(tmp_path):
    """No marketplace.json means nothing to measure, and the arm stays silent."""
    # Breaks if deleted: `skill-maintain test --dir` on a plain skills repo
    # (no marketplace, a legitimate shape check_version_alignment also
    # accepts) would sit permanently red on a check with no subject.
    (tmp_path / "skills").mkdir()
    assert _rows(check_always_on_ratchet(tmp_path)) == []


def test_ratchet_subcommand_is_wired_and_documented():
    """`skill-maintain ratchet` dispatches to always_on and appears in --help."""
    # Breaks if deleted: the module could ship with no way to run it, and
    # `--write` (the only sanctioned way to move a ceiling) be unreachable.
    from skill_maintainer.cli import COMMANDS, HELP

    assert COMMANDS.get("ratchet") == "skill_maintainer.always_on"
    assert "ratchet" in HELP and "ratchet --write" in HELP
