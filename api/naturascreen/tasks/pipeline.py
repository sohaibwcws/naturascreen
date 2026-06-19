"""Celery tasks that run the experiment pipeline off the request path."""

from __future__ import annotations

import asyncio

from ..db import get_sessionmaker
from ..services.pipeline import run_pipeline
from .celery_app import celery_app


@celery_app.task(name="run_experiment")
def run_experiment(experiment_id: int) -> dict:
    async def _run() -> None:
        async with get_sessionmaker()() as session:
            await run_pipeline(session, experiment_id)

    asyncio.run(_run())
    return {"experiment_id": experiment_id, "status": "done"}
