"""The websocket stream protocol: meta-first, notice on every frame, terminal reduction."""

from __future__ import annotations

from naturascreen.disclaimer import DISCLAIMER, SIMULATION_NOTICE
from naturascreen.services.simulation.engine import SimConfig
from naturascreen.services.simulation.stream import stream_to


async def test_stream_protocol_and_notice_on_every_frame():
    sent: list[dict] = []

    async def send(msg: dict) -> None:
        sent.append(msg)

    async def no_sleep(_: float) -> None:
        return None

    config = SimConfig(initial_population=60, max_steps=15, seed=2)
    treated, untreated, reduction = await stream_to(
        send, effectiveness=0.9, config=config, source="sandbox", fps=12, sleep=no_sleep
    )

    # 1. The mandatory envelope is first and carries BOTH notices.
    assert sent[0]["type"] == "meta"
    assert sent[0]["disclaimer"] == DISCLAIMER
    assert sent[0]["illustrative_notice"] == SIMULATION_NOTICE
    assert sent[0]["source"] == "sandbox"
    assert "k_division_suppression" in sent[0]["transfer"]

    # 2. Every frame carries the illustrative notice (cannot be inspected without it).
    frames = [m for m in sent if m["type"] == "frame"]
    assert frames
    assert all(f["illustrative_notice"] == SIMULATION_NOTICE for f in frames)
    assert all(len(f["positions"]) == 3 * len(f["states"]) for f in frames)

    # 3. Terminal message carries the treated-vs-untreated reduction.
    assert sent[-1]["type"] == "end"
    assert sent[-1]["reduction_pct"] == reduction
    # A strong illustrative effect reduces the treated population below untreated.
    assert treated < untreated
    assert reduction > 0
