"""Tests for the advisor transcript digest.

The digest is the whole reason this plugin exists: Claude Code cannot give a
stronger model both the model override and the conversation, so the session is
reconstructed from its transcript instead. Everything here pins a failure that
degrades advice *silently* -- the advisor still answers, it just answers without
knowing something it needed.

The first version of `digest.py` shipped with the bug in
`TestUserMessagesSurvive::test_ask_user_question_result_is_promoted_to_human`.
It classified AskUserQuestion results as tool output, so every constraint the
user stated through that channel was dropped. Nothing caught it but reading the
output by hand.

Run: uv run pytest skills/advisor/tests/ -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_DIGEST = Path(__file__).resolve().parents[1] / "skills" / "advisor" / "scripts" / "digest.py"
_spec = importlib.util.spec_from_file_location("advisor_digest", _DIGEST)
assert _spec and _spec.loader
digest = importlib.util.module_from_spec(_spec)
# Register before exec: @dataclass resolves its own module via
# sys.modules[cls.__module__], which is None for an unregistered module.
sys.modules["advisor_digest"] = digest
_spec.loader.exec_module(digest)


# --------------------------------------------------------------------------
# transcript fixture helpers
# --------------------------------------------------------------------------

def _rec(kind: str, content, **extra) -> dict:
    r = {
        "type": kind,
        "cwd": "/repo",
        "gitBranch": "main",
        "sessionId": "s1",
        "message": {"role": kind, "content": content},
    }
    r.update(extra)
    return r


def write_transcript(tmp_path: Path, records: list[dict], name="t.jsonl") -> Path:
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


def digest_of(tmp_path: Path, records: list[dict], budget=40000, sidechains=False) -> str:
    events, meta = digest.load_events(
        write_transcript(tmp_path, records), sidechains
    )
    return digest.render(events, meta, budget)


# --------------------------------------------------------------------------


class TestUserMessagesSurvive:
    """The user's own words are the one thing that must never be compressed."""

    def test_first_user_message_becomes_the_task(self, tmp_path):
        out = digest_of(tmp_path, [_rec("user", "Build a worker pool in Go.")])
        assert "## The task, as stated" in out
        assert "Build a worker pool in Go." in out

    def test_ask_user_question_result_is_promoted_to_human(self, tmp_path):
        """The regression that shipped. AskUserQuestion returns through the tool
        channel, but its content is the user speaking -- usually the binding
        constraint of the entire run."""
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [
                {"type": "tool_use", "id": "tu1", "name": "AskUserQuestion", "input": {}},
            ]),
            _rec("user", [
                {"type": "tool_result", "tool_use_id": "tu1",
                 "content": 'The user answered: "Scope?"="Only via slash command"'},
            ]),
        ]
        out = digest_of(tmp_path, records)
        assert "## Everything the user said afterwards" in out
        assert "Only via slash command" in out

    def test_ordinary_tool_results_are_not_treated_as_the_user(self, tmp_path):
        """Without this, every Bash result would be filed as user steering."""
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [
                {"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"command": "ls"}},
            ]),
            _rec("user", [
                {"type": "tool_result", "tool_use_id": "tu1", "content": "file-a\nfile-b"},
            ]),
        ]
        out = digest_of(tmp_path, records)
        assert "## Everything the user said afterwards" not in out
        assert "file-a" not in out

    def test_user_messages_survive_an_absurdly_small_budget(self, tmp_path):
        """Budget pressure must never cost a stated constraint."""
        records = [_rec("user", "TASK-SENTINEL do the thing.")]
        records += [
            _rec("assistant", [{"type": "text", "text": "filler " * 400}])
            for _ in range(12)
        ]
        records.append(_rec("user", "STEERING-SENTINEL never use threads."))
        out = digest_of(tmp_path, records, budget=500)
        assert "TASK-SENTINEL" in out
        assert "STEERING-SENTINEL" in out


class TestSidechains:
    """Subagent traffic is another agent's reasoning, not the executor's."""

    def test_excluded_by_default(self, tmp_path):
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [{"type": "text", "text": "SIDECHAIN-SENTINEL"}],
                 isSidechain=True),
        ]
        assert "SIDECHAIN-SENTINEL" not in digest_of(tmp_path, records)

    def test_included_on_request(self, tmp_path):
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [{"type": "text", "text": "SIDECHAIN-SENTINEL"}],
                 isSidechain=True),
        ]
        assert "SIDECHAIN-SENTINEL" in digest_of(tmp_path, records, sidechains=True)


class TestErrorsAndFiles:
    def test_failed_tool_calls_are_named_by_their_tool(self, tmp_path):
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [
                {"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"command": "false"}},
            ]),
            _rec("user", [
                {"type": "tool_result", "tool_use_id": "tu1",
                 "is_error": True, "content": "exit 1"},
            ]),
        ]
        out = digest_of(tmp_path, records)
        assert "## Failed tool calls" in out
        assert "Bash: exit 1" in out

    def test_written_files_are_listed_once_each(self, tmp_path):
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [
                {"type": "tool_use", "id": "a", "name": "Write",
                 "input": {"file_path": "/repo/x.py", "content": "..."}},
                {"type": "tool_use", "id": "b", "name": "Edit",
                 "input": {"file_path": "/repo/x.py", "new_string": "..."}},
                {"type": "tool_use", "id": "c", "name": "Write",
                 "input": {"file_path": "/repo/y.py", "content": "..."}},
            ]),
        ]
        out = digest_of(tmp_path, records)
        assert out.count("`/repo/x.py`") == 1
        assert "`/repo/y.py`" in out

    def test_file_contents_are_not_inlined(self, tmp_path):
        """A single Write carries a whole file; the advisor gets the path and
        has Read if it needs more."""
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [
                {"type": "tool_use", "id": "a", "name": "Write",
                 "input": {"file_path": "/repo/x.py", "content": "SECRET-BODY-SENTINEL"}},
            ]),
        ]
        assert "SECRET-BODY-SENTINEL" not in digest_of(tmp_path, records)


class TestRobustness:
    def test_a_malformed_line_is_skipped_not_fatal(self, tmp_path):
        """A partially flushed final line is normal -- the transcript is written
        asynchronously and may be mid-write when the digest runs."""
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps(_rec("user", "KEEP-SENTINEL")) + "\n"
            + '{"type": "assistant", "message": {"content": [{"type"\n',
            encoding="utf-8",
        )
        events, meta = digest.load_events(p, False)
        assert "KEEP-SENTINEL" in digest.render(events, meta, 40000)

    def test_harness_injected_blocks_are_stripped(self, tmp_path):
        records = [_rec("user", "REAL-SENTINEL\n<system-reminder>NOISE-SENTINEL</system-reminder>")]
        out = digest_of(tmp_path, records)
        assert "REAL-SENTINEL" in out
        assert "NOISE-SENTINEL" not in out

    def test_empty_transcript_exits_nonzero(self, tmp_path, monkeypatch):
        p = tmp_path / "empty.jsonl"
        p.write_text("", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["digest.py", str(p)])
        assert digest.main() == 1

    def test_missing_transcript_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["digest.py", str(tmp_path / "nope.jsonl")])
        assert digest.main() == 1

    def test_writes_to_output_path(self, tmp_path, monkeypatch):
        src = write_transcript(tmp_path, [_rec("user", "OUT-SENTINEL")])
        dest = tmp_path / "digest.md"
        monkeypatch.setattr(sys, "argv", ["digest.py", str(src), "-o", str(dest)])
        assert digest.main() == 0
        assert "OUT-SENTINEL" in dest.read_text(encoding="utf-8")


class TestSummarizeInput:
    """One line per tool call. Delegation deserves more detail than a path."""

    @pytest.mark.parametrize("name,inp,expected", [
        ("Write", {"file_path": "/repo/a.py"}, "/repo/a.py"),
        ("Bash", {"command": "ls -la"}, "ls -la"),
        ("Grep", {"pattern": "TODO"}, "TODO"),
    ])
    def test_common_shapes(self, name, inp, expected):
        assert digest.summarize_input(name, inp) == expected

    def test_agent_calls_name_the_subagent(self):
        out = digest.summarize_input(
            "Agent", {"subagent_type": "advisor", "description": "consult"}
        )
        assert "advisor" in out

    def test_non_dict_input_is_survivable(self):
        assert digest.summarize_input("Bash", None) == ""

    def test_long_values_are_clipped_with_a_marker(self):
        out = digest.summarize_input("Bash", {"command": "x" * 5000})
        assert len(out) < 5000
        assert "elided" in out


class TestMetadata:
    def test_reports_branch_and_turn_counts(self, tmp_path):
        records = [
            _rec("user", "Do the thing."),
            _rec("assistant", [{"type": "text", "text": "ok"}]),
            _rec("assistant", [{"type": "text", "text": "still ok"}]),
        ]
        out = digest_of(tmp_path, records)
        assert "`main`" in out
        assert "1 human, 2 assistant" in out

    def test_states_that_it_is_a_reconstruction(self, tmp_path):
        """The advisor must not read compression artifacts as absence of fact."""
        out = digest_of(tmp_path, [_rec("user", "Do the thing.")])
        assert "reconstruction" in out.lower()
