"""Tests for the heylook capability probe.

`probe.py` answers one question: can this machine do the thing I am about to
build. The skill body tells you to gate on its exit code, so every failure
pinned here is a WRONG ANSWER rather than a crash -- the probe still exits,
it just exits 0 when the honest answer was "no".

Four of these went red against the 0.1.0 script:

  - an empty roster with `--need` exited 0 in text mode and 2 in `--json`.
    The documented invocation (SKILL.md) has no `--json`, so the reachable
    path was the wrong one, and a gate written from the skill body passed on
    a server serving nothing.
  - an HTTP error (401 from an authenticated off-machine server) was caught
    as a connection failure and answered "start the server", which is wrong
    advice for a server that is already running.
  - a non-JSON body -- the wrong service on :8000 -- raised JSONDecodeError
    as a traceback. It is a ValueError, so the OSError handler never saw it.
  - there was no way to send a bearer token at all, so the probe could not
    reach the authenticated remote server the skill tells you to expect.

The exit code is computed ONCE and both renderers return it; the
mode-agreement tests below are what keeps that true. The tests that pin
already-correct behaviour were each proved fallible at birth by mutating the
behaviour and confirming red (see the module comment on each).

Run: uv run pytest skills/heylook-provider/tests/ -q
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

_PROBE = Path(__file__).resolve().parents[1] / "skills" / "heylook-provider" / "scripts" / "probe.py"
_spec = importlib.util.spec_from_file_location("heylook_probe", _PROBE)
assert _spec and _spec.loader
probe = importlib.util.module_from_spec(_spec)
sys.modules["heylook_probe"] = probe
_spec.loader.exec_module(probe)


# --------------------------------------------------------------------------
# a real HTTP server, not a stubbed fetch
#
# Two of the bugs above originate INSIDE fetch() -- urllib's error taxonomy
# and the JSON decode. A monkeypatched fetch cannot reach either, so the
# fixture serves real responses over a real socket.
# --------------------------------------------------------------------------

MODELS = "/v1/models"
CAPS = "/v1/capabilities"

VISION_ROW = {"id": "qwen-vl", "provider": "mlx", "capabilities": ["chat", "vision"]}
TEXT_ROW = {"id": "qwen-text", "provider": "mlx", "capabilities": ["chat"]}
CAPS_BODY = {"server_version": "1.79.37", "samplers": {"available": ["balanced"]}}


def json_routes(rows, caps=None):
    """Standard heylook shapes: /v1/models is an OpenAI-style list envelope."""
    return {
        MODELS: (200, "application/json", json.dumps({"object": "list", "data": rows})),
        CAPS: (200, "application/json", json.dumps(CAPS_BODY if caps is None else caps)),
    }


@contextmanager
def serving(routes, *, record=None):
    """Serve `routes` on a loopback port. `record` collects request headers."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep pytest output clean
            pass

        def do_GET(self):
            if record is not None:
                record.append((self.path, dict(self.headers)))
            status, ctype, body = routes.get(
                self.path, (404, "application/json", '{"detail":"not found"}')
            )
            payload = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def run(base, *args):
    return probe.main(["--base", base, "--timeout", "5", *args])


# --------------------------------------------------------------------------
# the exit code is the product
# --------------------------------------------------------------------------


class TestExitCodeIsTheAnswer:
    """`--need` is a gate. An exit 0 it did not earn is the only failure that
    reaches production, because nothing downstream looks again."""

    @pytest.mark.parametrize("mode", [[], ["--json"]])
    def test_empty_roster_with_need_is_unmatched(self, mode, capsys):
        # RED at 0.1.0 in text mode (returned 0), green in --json. The two
        # renderers derived the code independently; now they share one.
        with serving(json_routes([])) as base:
            assert run(base, "--need", "vision", *mode) == 2

    @pytest.mark.parametrize("mode", [[], ["--json"]])
    def test_roster_without_the_capability_is_unmatched(self, mode, capsys):
        # Born green. Fallibility proved by making the gate match every
        # row (`matched = list(models)`): this went to 0. Reverted.
        with serving(json_routes([TEXT_ROW])) as base:
            assert run(base, "--need", "vision", *mode) == 2

    @pytest.mark.parametrize("mode", [[], ["--json"]])
    def test_served_capability_is_ok(self, mode, capsys):
        # Born green. Fallibility proved by inverting the subset test to
        # `caps <= need`: this went to 2. Reverted.
        with serving(json_routes([VISION_ROW, TEXT_ROW])) as base:
            assert run(base, "--need", "vision", *mode) == 0

    @pytest.mark.parametrize("mode", [[], ["--json"]])
    def test_no_need_is_ok_even_with_an_empty_roster(self, mode, capsys):
        # An empty roster is not itself a failure -- only an unmet `--need`
        # is. Born green; proved by returning 2 whenever `models` was empty,
        # which reddened this. Reverted.
        with serving(json_routes([])) as base:
            assert run(base, *mode) == 0

    @pytest.mark.parametrize("rows", [[], [TEXT_ROW], [VISION_ROW, TEXT_ROW]])
    def test_both_renderers_agree(self, rows, capsys):
        """The 0.1.0 bug was a divergence, not a wrong constant. This is the
        test that stays meaningful after the constant is fixed."""
        with serving(json_routes(rows)) as base:
            text = run(base, "--need", "vision")
            capsys.readouterr()
            as_json = run(base, "--need", "vision", "--json")
        assert text == as_json


# --------------------------------------------------------------------------
# a server we cannot read is not a server that is down
# --------------------------------------------------------------------------


class TestUnreadableServers:
    """Each of these answered "start the server with heylookllm" at 0.1.0 or
    raised a traceback. Both send the operator to the wrong place."""

    def test_unreachable_says_so(self, capsys):
        # Born green. Fallibility proved by returning 0 from the connection
        # handler: this reddened. Reverted.
        assert run("http://127.0.0.1:9", "--timeout", "1") == 1
        assert "cannot reach" in capsys.readouterr().err

    def test_401_is_an_auth_problem_not_a_dead_server(self, capsys):
        # RED at 0.1.0: HTTPError subclasses URLError, so this printed
        # "start the server with `heylookllm`" for a server already running.
        routes = {MODELS: (401, "application/json", '{"detail":"unauthorized"}')}
        with serving(routes) as base:
            assert run(base) == 1
        err = capsys.readouterr().err
        assert "HEYLOOK_API_KEY" in err or "--api-key" in err
        assert "start the server" not in err

    def test_non_json_body_is_diagnosed_not_raised(self, capsys):
        # RED at 0.1.0: JSONDecodeError is a ValueError, so the OSError
        # handler missed it and the user got a traceback. The realistic
        # trigger is another service already on :8000.
        routes = {MODELS: (200, "text/html", "<html>not heylook</html>")}
        with serving(routes) as base:
            assert run(base) == 1
        assert "JSON" in capsys.readouterr().err

    def test_row_without_an_id_is_diagnosed_not_raised(self, capsys):
        # RED at 0.1.0: `max(len(m["id"]) ...)` raised KeyError as a
        # traceback. Line 88 of that file used .get on the same rows, so the
        # defensiveness was already inconsistent.
        with serving(json_routes([{"provider": "mlx", "capabilities": ["chat"]}])) as base:
            assert run(base) == 1
        assert "id" in capsys.readouterr().err

    def test_capabilities_endpoint_is_optional(self, capsys):
        # Born green, and load-bearing: /v1/capabilities is best-effort, so
        # its absence must not fail a probe that got a roster. Proved by
        # letting the caps fetch propagate: this went to 1. Reverted.
        routes = {MODELS: (200, "application/json", json.dumps({"data": [VISION_ROW]}))}
        with serving(routes) as base:
            assert run(base, "--need", "vision") == 0


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------


class TestAuth:
    """The API-key gate is loopback-exempt, so it appears exactly when the
    app runs off-machine -- the case the skill tells you to plan for and the
    one 0.1.0 could not probe at all."""

    def test_api_key_flag_sends_a_bearer_header(self):
        # RED at 0.1.0: no such flag existed.
        seen = []
        with serving(json_routes([VISION_ROW]), record=seen) as base:
            assert run(base, "--api-key", "sk-test-value") == 0
        assert all(h.get("Authorization") == "Bearer sk-test-value" for _, h in seen)

    def test_env_var_is_the_default(self, monkeypatch):
        # RED at 0.1.0. HEYLOOK_API_KEY is what the server itself reads, so
        # a flag-only probe would force the secret into shell history.
        monkeypatch.setenv("HEYLOOK_API_KEY", "sk-from-env")
        seen = []
        with serving(json_routes([VISION_ROW]), record=seen) as base:
            assert run(base) == 0
        assert seen[0][1].get("Authorization") == "Bearer sk-from-env"

    def test_flag_beats_env(self, monkeypatch):
        monkeypatch.setenv("HEYLOOK_API_KEY", "sk-from-env")
        seen = []
        with serving(json_routes([VISION_ROW]), record=seen) as base:
            assert run(base, "--api-key", "sk-from-flag") == 0
        assert seen[0][1].get("Authorization") == "Bearer sk-from-flag"

    def test_no_auth_header_when_no_key(self, monkeypatch):
        monkeypatch.delenv("HEYLOOK_API_KEY", raising=False)
        seen = []
        with serving(json_routes([VISION_ROW]), record=seen) as base:
            assert run(base) == 0
        assert all("Authorization" not in h for _, h in seen)

    def test_the_key_is_never_printed(self, monkeypatch, capsys):
        """A probe is something you paste into an issue. The secret must not
        survive into stdout or stderr on any path, including the failing one."""
        monkeypatch.setenv("HEYLOOK_API_KEY", "sk-should-not-appear")
        routes = {MODELS: (401, "application/json", '{"detail":"unauthorized"}')}
        with serving(routes) as base:
            run(base)
        captured = capsys.readouterr()
        assert "sk-should-not-appear" not in captured.out + captured.err


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


class TestOutput:
    def test_matched_rows_are_marked(self, capsys):
        """The marker must be on the TABLE ROW. A first draft asserted
        `"*" in out`, which the trailing `* serves [...]` summary line
        satisfied on its own -- so dropping the row marker left it green.
        Proved by dropping the marker: this now reddens. Reverted."""
        with serving(json_routes([VISION_ROW, TEXT_ROW])) as base:
            run(base, "--need", "vision")
        rows = {ln.split()[0]: ln.rstrip()
                for ln in capsys.readouterr().out.splitlines()
                if ln.startswith(("qwen-vl", "qwen-text"))}
        assert set(rows) == {"qwen-vl", "qwen-text"}
        assert rows["qwen-vl"].endswith("*")
        assert not rows["qwen-text"].endswith("*")

    def test_json_mode_reports_matched_ids(self, capsys):
        with serving(json_routes([VISION_ROW, TEXT_ROW])) as base:
            run(base, "--need", "vision", "--json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["matched"] == ["qwen-vl"]
        assert payload["server_version"] == "1.79.37"
        assert payload["samplers"] == ["balanced"]
