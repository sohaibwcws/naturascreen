"""The seam where real scientific adapters feed the scoring service.

Each adapter module (docking / neoantigen / response, landed in Phase 5) exposes:

    async def score(session, experiment, compound) -> float | None

returning its sub-score in the raw unit the scoring window expects (kcal/mol,
MHCflurry %rank, ln(IC50 µM)), persisting its own detail rows, and returning ``None`` or
raising ``AdapterUnavailable`` when the tool/data is not provisioned. Until an adapter
module exists or is provisioned, that channel is simply absent — the scoring service
excludes it and renormalizes. Nothing here fabricates a value.
"""

from __future__ import annotations

import importlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Compound, Experiment

log = logging.getLogger(__name__)


class AdapterUnavailable(Exception):
    """Raised by an adapter when its tool or data is not provisioned."""


_ADAPTERS = {
    "binding": "naturascreen.services.docking.adapter",
    "neoantigen": "naturascreen.services.neoantigen.adapter",
    "response": "naturascreen.services.response.adapter",
}


async def _channel_score(
    modpath: str, session: AsyncSession, experiment: Experiment, compound: Compound
) -> float | None:
    try:
        module = importlib.import_module(modpath)
    except ImportError:
        return None  # adapter not built yet
    scorer = getattr(module, "score", None)
    if scorer is None:
        return None
    try:
        return await scorer(session, experiment, compound)
    except AdapterUnavailable:
        return None
    except Exception:  # noqa: BLE001 — one adapter failing must not abort the pipeline
        log.exception("adapter %s failed for compound %s", modpath, compound.id)
        return None


async def gather_subscores(
    session: AsyncSession, experiment: Experiment, compound: Compound
) -> dict[str, float | None]:
    """Collect raw sub-scores for one compound. Missing channels are ``None``."""
    raw: dict[str, float | None] = {}
    for channel, modpath in _ADAPTERS.items():
        raw[channel] = await _channel_score(modpath, session, experiment, compound)
    # Simulation is downstream of scoring (it illustrates the score), never an input.
    raw["simulation"] = None
    return raw
