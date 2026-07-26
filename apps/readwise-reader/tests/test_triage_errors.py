"""Tests for batch_triage's per-item error collector.

`batch_triage` used to wrap each item in a bare `except Exception`, which meant
a bug in our own dispatch was silently recorded as a per-document failure and
returned to the caller as if the document were at fault. The catch is now
narrowed to what the body can actually raise: the API call (`httpx.HTTPError`,
covering both transport and status errors), request-model construction and
response decoding (`pydantic.ValidationError` and `JSONDecodeError`, both
`ValueError` subclasses), and the audit write (`duckdb.Error`).

These tests pin both halves of that contract -- expected failures are still
collected and the batch still completes, and an unexpected exception now
propagates instead of being disguised as a document-level error.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import duckdb
import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from readwise_reader.storage.database import Database
from readwise_reader.tools.triage import register_triage_tools


def _batch_triage_fn() -> Any:
    """Pull the registered closure out of the tool manager."""
    mcp = FastMCP("test")
    register_triage_tools(mcp)
    return mcp._tool_manager.get_tool("batch_triage").fn


def _ctx(client: Any, db: Any) -> Any:
    """Minimal stand-in for the FastMCP request context `_get_deps` reads."""
    lifespan = SimpleNamespace(client=client, db=db)
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=lifespan))


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "triage.duckdb")


class _Client:
    """Client stub whose `update_document` raises whatever it is given."""

    def __init__(self, exc: BaseException | None = None) -> None:
        self._exc = exc
        self.calls: list[str] = []

    async def update_document(self, doc_id: str, request: Any) -> dict[str, Any]:
        self.calls.append(doc_id)
        if self._exc is not None:
            raise self._exc
        return {"id": doc_id}

    async def delete_document(self, doc_id: str) -> bool:
        return True


@pytest.mark.parametrize(
    ("exc", "label"),
    [
        (httpx.ConnectError("connection refused"), "transport error"),
        (
            httpx.HTTPStatusError(
                "500 Server Error",
                request=httpx.Request("PATCH", "http://x/api/v3/update/d1/"),
                response=httpx.Response(500),
            ),
            "status error",
        ),
        (duckdb.Error("audit write failed"), "database error"),
        (ValueError("undecodable response"), "value error"),
    ],
)
async def test_expected_failures_are_collected_not_raised(
    db: Database, exc: BaseException, label: str
) -> None:
    """Each reachable failure is recorded on its own row; the call still returns."""
    fn = _batch_triage_fn()
    client = _Client(exc)
    results = await fn(
        _ctx(client, db),
        [{"doc_id": "d1", "action": "later"}],
    )
    assert len(results) == 1, label
    assert results[0]["success"] is False, label
    assert results[0]["doc_id"] == "d1"
    assert results[0]["error"]


async def test_one_failure_does_not_abort_the_batch(db: Database) -> None:
    """The whole point of the collector: later items still get processed."""
    fn = _batch_triage_fn()

    class FlakyClient(_Client):
        async def update_document(self, doc_id: str, request: Any) -> dict[str, Any]:
            self.calls.append(doc_id)
            if doc_id == "bad":
                raise httpx.ConnectError("connection refused")
            return {"id": doc_id}

    client = FlakyClient()
    results = await fn(
        _ctx(client, db),
        [
            {"doc_id": "good-1", "action": "later"},
            {"doc_id": "bad", "action": "later"},
            {"doc_id": "good-2", "action": "archive"},
        ],
    )

    assert [r["success"] for r in results] == [True, False, True]
    assert client.calls == ["good-1", "bad", "good-2"]


async def test_unexpected_exception_propagates(db: Database) -> None:
    """A bug in our own code must not be reported as a document-level failure.

    This is the behaviour the narrowing bought. Under the previous bare
    `except Exception` this test would fail: the TypeError would be swallowed
    and returned as `{"success": False, "error": "..."}` for document `d1`.
    """
    fn = _batch_triage_fn()
    client = _Client(TypeError("internal dispatch bug"))

    with pytest.raises(TypeError, match="internal dispatch bug"):
        await fn(_ctx(client, db), [{"doc_id": "d1", "action": "later"}])
