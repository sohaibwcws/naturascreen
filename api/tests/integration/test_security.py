"""API-key auth gate: open in dev (no keys), enforced when keys are configured."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from naturascreen import security
from naturascreen.config import Settings


def _with_keys(monkeypatch, keys: str) -> None:
    monkeypatch.setattr(security, "get_settings", lambda: Settings(api_keys=keys))


async def test_open_mode_allows_when_no_keys(monkeypatch):
    _with_keys(monkeypatch, "")
    assert await security.require_api_key(None, None) is None  # no raise


async def test_enforced_mode_rejects_missing_key(monkeypatch):
    _with_keys(monkeypatch, "secret-a,secret-b")
    with pytest.raises(HTTPException) as exc:
        await security.require_api_key(None, None)
    assert exc.value.status_code == 401


async def test_enforced_mode_accepts_header_and_bearer(monkeypatch):
    _with_keys(monkeypatch, "secret-a,secret-b")
    assert await security.require_api_key("secret-b", None) is None
    assert await security.require_api_key(None, "Bearer secret-a") is None


async def test_enforced_mode_rejects_wrong_key(monkeypatch):
    _with_keys(monkeypatch, "secret-a")
    with pytest.raises(HTTPException):
        await security.require_api_key("nope", None)
