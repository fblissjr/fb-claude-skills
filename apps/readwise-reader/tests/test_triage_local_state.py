"""Tests that triage moves are mirrored into the local DuckDB copy.

`get_inbox` reads the local copy, not Reader. `batch_triage` used to move
`later`/`archive` items in Reader and write only the audit log, so each moved
item still read as `new` locally and the next `get_inbox` returned it again;
the skills worked around it by telling Claude to sync after every batch.

The local write must not cost a Reader read per item: reads are budgeted at 20
per minute (`ReadwiseClient._read_limiter`) and a default triage batch is 10
items. So a move without tags is written locally, and only a move that also
sets tags re-reads the document, because Reader replaces the whole tag set and
its tag JSON cannot be reconstructed from a list of names.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from readwise_reader.api.models import Document
from readwise_reader.storage.database import Database
from readwise_reader.tools.triage import register_triage_tools


def _tool(name: str) -> Any:
    mcp = FastMCP("test")
    register_triage_tools(mcp)
    return mcp._tool_manager.get_tool(name).fn


def _ctx(client: Any, db: Any) -> Any:
    lifespan = SimpleNamespace(client=client, db=db)
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=lifespan))


class _Client:
    """Reader stub: updates succeed, and every read is recorded."""

    def __init__(self, served: dict[str, Document] | None = None) -> None:
        self.served = served or {}
        self.reads: list[str] = []

    async def update_document(self, doc_id: str, request: Any) -> dict[str, Any]:
        return {"id": doc_id}

    async def get_document(self, doc_id: str, include_content: bool = False) -> Document | None:
        self.reads.append(doc_id)
        return self.served.get(doc_id)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(db_path=tmp_path / "triage.duckdb")
    for doc_id in ("d1", "d2", "d3"):
        database.upsert_document({"id": doc_id, "title": doc_id, "location": "new"})
    return database


def _row(db: Database, doc_id: str) -> dict[str, Any]:
    row = db.get_document(doc_id)
    assert row is not None, f"{doc_id} missing from the local copy"
    return row


def _inbox_ids(db: Database) -> list[str]:
    return sorted(d["doc_id"] for d in db.query_documents(location="new"))


async def test_batch_moves_leave_the_local_inbox(db: Database) -> None:
    # The reported bug: without this, d1 and d2 come back from the next get_inbox.
    client = _Client()
    await _tool("batch_triage")(
        _ctx(client, db),
        [{"doc_id": "d1", "action": "later"}, {"doc_id": "d2", "action": "archive"}],
    )

    assert _inbox_ids(db) == ["d3"]
    assert _row(db, "d1")["location"] == "later"
    assert _row(db, "d2")["location"] == "archive"


async def test_batch_moves_without_tags_spend_no_reads(db: Database) -> None:
    # Pins the rate-budget choice: a re-read per item would let a 10-item batch
    # consume half the per-minute read budget.
    client = _Client()
    await _tool("batch_triage")(
        _ctx(client, db),
        [{"doc_id": "d1", "action": "later"}, {"doc_id": "d2", "action": "archive"}],
    )

    assert client.reads == []


async def test_batch_move_with_tags_refreshes_the_row_from_reader(db: Database) -> None:
    # Reader replaced the tag set; the local row must carry Reader's version.
    served = Document(id="d1", title="d1", location="later", tags={"ml": {"name": "ml"}})
    client = _Client({"d1": served})
    await _tool("batch_triage")(
        _ctx(client, db),
        [{"doc_id": "d1", "action": "later", "tags": ["ml"]}],
    )

    assert client.reads == ["d1"]
    row = _row(db, "d1")
    assert row["location"] == "later"
    assert "ml" in row["tags"]


async def test_single_triage_uses_the_same_local_write(db: Database) -> None:
    # triage_document and batch_triage share one rule; this keeps them from drifting.
    client = _Client()
    await _tool("triage_document")(_ctx(client, db), doc_id="d3", action="archive")

    assert _row(db, "d3")["location"] == "archive"
    assert client.reads == []
