"""WebSocket streaming of live simulation frames.

- ``/simulate/stream`` — sandbox: stream the illustrative dynamics at an explicit
  effectiveness. This is an honest exploration of the HeuristicEffectTransfer, not tied to
  any compound's real score; the UI labels it as such.
- ``/experiments/{id}/stream`` — stream the top compound's run at its computed score
  (0.0 until the scientific adapters are provisioned).

Both send the StreamMeta envelope (both safety notices) before any frame; the viewer is
gated on it. Streaming is a deterministic re-run from the seed — race-free and replayable.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..db import get_sessionmaker
from ..models import Experiment
from ..services.pipeline import top_effectiveness
from ..services.simulation.engine import SimConfig
from ..services.simulation.stream import stream_to
from sqlalchemy import select

log = logging.getLogger(__name__)
router = APIRouter(tags=["stream"])


def _f(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _i(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


@router.websocket("/simulate/stream")
async def simulate_stream(ws: WebSocket) -> None:
    await ws.accept()
    q = ws.query_params
    effectiveness = min(1.0, max(0.0, _f(q.get("effectiveness"), 0.5)))
    config = SimConfig(
        seed=_i(q.get("seed"), 0),
        max_steps=min(300, max(10, _i(q.get("steps"), 120))),
        initial_population=min(1500, max(20, _i(q.get("population"), 400))),
    )
    fps = min(30.0, max(1.0, _f(q.get("fps"), 12.0)))
    try:
        await stream_to(
            ws.send_json, effectiveness=effectiveness, config=config, source="sandbox", fps=fps
        )
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001
        log.exception("sandbox stream failed")
    finally:
        await _safe_close(ws)


@router.websocket("/experiments/{experiment_id}/stream")
async def experiment_stream(ws: WebSocket, experiment_id: int) -> None:
    await ws.accept()
    q = ws.query_params
    fps = min(30.0, max(1.0, _f(q.get("fps"), 12.0)))
    async with get_sessionmaker()() as session:
        experiment = (
            await session.execute(select(Experiment).where(Experiment.id == experiment_id))
        ).scalar_one_or_none()
        if experiment is None:
            await ws.close(code=4404)
            return
        effectiveness = await top_effectiveness(session, experiment_id)
        config = SimConfig(seed=experiment.seed)
    try:
        await stream_to(
            ws.send_json,
            effectiveness=effectiveness,
            config=config,
            source=f"experiment:{experiment_id}",
            fps=fps,
        )
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001
        log.exception("experiment stream failed")
    finally:
        await _safe_close(ws)


async def _safe_close(ws: WebSocket) -> None:
    try:
        await ws.close()
    except RuntimeError:
        pass  # already closed
