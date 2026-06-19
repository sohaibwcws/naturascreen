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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

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

    # Rate limiting (per client IP). Default storage is in-process; use Redis in prod.
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit],
        storage_uri=settings.rate_limit_storage,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/meta", tags=["meta"])
    async def meta() -> dict:
        """Honest capability report: what is actually provisioned vs. `unavailable`."""
        import json
        import shutil

        from .services.response import model as response_model

        # Read the response model's honest dual-CV card if present (pure JSON, no xgboost).
        response_card: dict | None = None
        meta_file = response_model.meta_path()
        if meta_file.is_file():
            try:
                response_card = json.loads(meta_file.read_text()).get("cv_metric")
            except Exception:  # noqa: BLE001
                response_card = None

        return {
            "version": __version__,
            "disclaimer": DISCLAIMER,
            "simulation_notice": SIMULATION_NOTICE,
            "adapters": {
                # Reflect real provisioning, not mere configuration: the Vina binary must be
                # on PATH, MHCflurry models fetched, the response checkpoint trained.
                "docking": {
                    "available": bool(settings.vina_binary)
                    and shutil.which(settings.vina_binary) is not None,
                    "tool": "AutoDock Vina",
                },
                "neoantigen": {"available": settings.mhcflurry_ready, "tool": "MHCflurry"},
                "response": {
                    "available": response_model.is_ready(),
                    "tool": "XGBoost/GDSC",
                    "cv": response_card,
                },
            },
        }

    _mount_routers(app)
    return app


def _mount_routers(app: FastAPI) -> None:
    """Mount domain routers as each phase lands them (kept import-coherent)."""
    from .routers import compounds, experiments, feedback, neoantigens, stream, targets

    app.include_router(compounds.router)
    app.include_router(targets.router)
    app.include_router(neoantigens.router)
    app.include_router(experiments.router)
    app.include_router(feedback.router)
    app.include_router(stream.router)

app = create_app()
