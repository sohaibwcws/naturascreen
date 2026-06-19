"""Transport-agnostic simulation streaming.

``stream_to`` drives the engine and pushes JSON-able payloads to a ``send`` callable: the
mandatory StreamMeta envelope first (both safety notices), then one Frame per timestep
(each also carrying the illustrative notice), then a StreamEnd with the treated-vs-
untreated reduction. The websocket router supplies ``send``; tests supply a fake send and
a no-op sleep, so the protocol (meta-first, notice-on-every-frame, terminal reduction) is
verified without a socket.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from ...schemas import FrameOut, StreamEnd, StreamMeta
from .engine import (
    K_DEATH_INDUCTION,
    K_DIVISION_SUPPRESSION,
    SimConfig,
    Frame,
    simulate,
)

SendFn = Callable[[dict], Awaitable[None]]


def transfer_params() -> dict:
    return {
        "k_division_suppression": K_DIVISION_SUPPRESSION,
        "k_death_induction": K_DEATH_INDUCTION,
        "formula": "division_multiplier = 1 - k_div·e ; death_multiplier = 1 + k_death·e",
        "note": "Illustrative mapping from effectiveness e∈[0,1] to rate multipliers; "
        "not validated pharmacology.",
    }


def build_meta(effectiveness: float, config: SimConfig, source: str) -> dict:
    return StreamMeta(
        effectiveness=round(float(effectiveness), 4),
        seed=config.seed,
        steps=config.max_steps,
        transfer=transfer_params(),
        source=source,
    ).model_dump()


def frame_payload(frame: Frame) -> dict:
    return FrameOut(
        t=frame.t,
        time=frame.time,
        positions=frame.positions,
        states=frame.states,
        population=frame.population,
        baseline_population=frame.baseline_population,
        counts=frame.counts,
    ).model_dump()


def reduction_pct(treated_final: int, untreated_final: int) -> float:
    """Percent reduction of the treated tumor vs. the untreated baseline at end time."""
    if untreated_final <= 0:
        return 0.0
    return round(100.0 * max(0.0, (untreated_final - treated_final) / untreated_final), 2)


async def stream_to(
    send: SendFn,
    *,
    effectiveness: float,
    config: SimConfig,
    source: str,
    fps: float = 12.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[int, int, float]:
    """Stream a full run; return (treated_final, untreated_final, reduction_pct)."""
    await send(build_meta(effectiveness, config, source))
    delay = 1.0 / fps if fps > 0 else 0.0
    treated_final = 0
    untreated_final = 0
    for frame in simulate(config, effectiveness):
        await send(frame_payload(frame))
        treated_final = frame.population
        untreated_final = frame.baseline_population
        if delay:
            await sleep(delay)
    reduction = reduction_pct(treated_final, untreated_final)
    await send(
        StreamEnd(
            final_population=treated_final,
            baseline_population=untreated_final,
            reduction_pct=reduction,
        ).model_dump()
    )
    return treated_final, untreated_final, reduction
