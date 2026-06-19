"""End-to-end HTTP + WebSocket tests against the real ASGI app (shared-memory SQLite).

Exercises the router wiring, the experiment pipeline over the API, and the live stream
protocol — without needing the Docker stack.
"""

from __future__ import annotations

import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from naturascreen import models  # noqa: F401
from naturascreen.db import Base, get_session
from naturascreen.disclaimer import DISCLAIMER, SIMULATION_NOTICE
from naturascreen.main import app
from naturascreen.services.compounds.coconut import CompoundRecord
from naturascreen.services.compounds.service import upsert_compounds


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    async with maker() as session:
        await upsert_compounds(
            session,
            [CompoundRecord("CNP1", "Alpha", "CCO", None, 1), CompoundRecord("CNP2", "Beta", "CCN", None, 1)],
            with_descriptors=False,
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_health_and_meta(client):
    assert (await client.get("/health")).json()["status"] == "ok"
    meta = (await client.get("/meta")).json()
    assert meta["disclaimer"] == DISCLAIMER
    assert meta["simulation_notice"] == SIMULATION_NOTICE
    assert set(meta["adapters"]) == {"docking", "neoantigen", "response"}


async def test_compounds_listed(client):
    body = (await client.get("/compounds")).json()
    assert body["total"] == 2
    assert {c["name"] for c in body["items"]} == {"Alpha", "Beta"}


async def test_experiment_flow_end_to_end(client):
    ids = [c["id"] for c in (await client.get("/compounds")).json()["items"]]
    created = await client.post("/experiments", json={"compound_set": ids, "seed": 1})
    assert created.status_code == 201
    exp_id = created.json()["id"]

    run = await client.post(f"/experiments/{exp_id}/run?sync=true")
    assert run.json()["status"] == "completed"

    results = (await client.get(f"/experiments/{exp_id}/results")).json()
    # Safety notices are present on the results envelope (type-enforced).
    assert results["disclaimer"] == DISCLAIMER
    assert results["illustrative_notice"] == SIMULATION_NOTICE
    assert len(results["ranked"]) == 2
    assert results["simulation"] is not None
    # No adapters -> combined scores are 0 and not fabricated.
    assert all(r["combined_score"] == 0.0 for r in results["ranked"])


async def test_create_rejects_empty_compound_set(client):
    resp = await client.post("/experiments", json={"compound_set": []})
    assert resp.status_code == 422


async def test_feedback_lab_result_roundtrip(client):
    cid = (await client.get("/compounds")).json()["items"][0]["id"]
    created = await client.post(
        "/feedback/lab-result",
        json={"compound_id": cid, "measured_ic50": 12.5, "source": "internal assay", "verified": True},
    )
    assert created.status_code == 201
    assert created.json()["measured_ic50"] == 12.5
    listed = (await client.get("/feedback/lab-results?verified_only=true")).json()
    assert any(r["compound_id"] == cid for r in listed)


async def test_feedback_rejects_unknown_compound(client):
    resp = await client.post(
        "/feedback/lab-result",
        json={"compound_id": 99999, "measured_ic50": 1.0, "source": "x"},
    )
    assert resp.status_code == 404


def test_sandbox_websocket_streams_meta_then_frames():
    # Sync TestClient for websockets; the sandbox stream does not touch the database.
    with TestClient(app) as c:
        with c.websocket_connect(
            "/simulate/stream?effectiveness=0.9&population=40&steps=12&fps=30"
        ) as ws:
            meta = ws.receive_json()
            assert meta["type"] == "meta"
            assert meta["disclaimer"] == DISCLAIMER
            assert meta["illustrative_notice"] == SIMULATION_NOTICE

            saw_frame = False
            while True:
                msg = ws.receive_json()
                if msg["type"] == "frame":
                    saw_frame = True
                    assert msg["illustrative_notice"] == SIMULATION_NOTICE
                    assert len(msg["positions"]) == 3 * len(msg["states"])
                elif msg["type"] == "end":
                    break
            assert saw_frame
