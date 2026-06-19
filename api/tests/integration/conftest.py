"""Shared async test fixtures: an in-memory SQLite session with the full schema."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from naturascreen import models  # noqa: F401  (register all tables on Base.metadata)
from naturascreen.config import get_settings
from naturascreen.db import Base


@pytest.fixture(autouse=True)
def _clean_adapter_env(monkeypatch):
    """Force adapters OFF by default so the suite is deterministic regardless of the host's
    ambient provisioning (env vars / trained model files). Tests that exercise a provisioned
    adapter override these within their own body."""
    settings = get_settings()
    monkeypatch.setattr(settings, "response_model_ready", False)
    monkeypatch.setattr(settings, "mhcflurry_ready", False)
    monkeypatch.setattr(settings, "vina_binary", "")


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()
