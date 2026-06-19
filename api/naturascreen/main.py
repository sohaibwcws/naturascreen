"""FastAPI application factory and process-wide wiring.

Routers are mounted per domain (compounds, targets, neoantigens, experiments,
feedback) and a WebSocket streamer relays live simulation frames. The ``/meta``
endpoint reports which scientific adapters are actually provisioned, so the frontend
can show capabilities honestly instead of implying functionality that is unavailable.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .disclaimer import DISCLAIMER, SIMULATION_NOTICE

settings = get_settings()
logging.basicConfig(level=settings.log_level)


def create_app() -> FastAPI:
    app = FastAPI(
        title="NaturaScreen",
        version=__version__,
        summary="Screen natural compounds against cancer targets as research hypotheses.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/meta", tags=["meta"])
    async def meta() -> dict:
        """Honest capability report: what is wired vs. what is `unavailable`."""
        return {
            "version": __version__,
            "disclaimer": DISCLAIMER,
            "simulation_notice": SIMULATION_NOTICE,
            "adapters": {
                "docking": {"available": bool(settings.vina_binary), "tool": "AutoDock Vina"},
                "neoantigen": {"available": settings.mhcflurry_ready, "tool": "MHCflurry"},
                "response": {"available": settings.response_model_ready, "tool": "XGBoost/GDSC"},
            },
        }

    _mount_routers(app)
    return app


def _mount_routers(app: FastAPI) -> None:
    """Mount domain routers as each phase lands them (kept import-coherent)."""
    from .routers import compounds

    app.include_router(compounds.router)

app = create_app()
