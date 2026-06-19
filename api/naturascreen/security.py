"""API-key authentication for write/compute endpoints.

Reads (browsing compounds, viewing results) are public so the demo "just works". The
endpoints that mutate state or burn compute — creating/running experiments, neoantigen
prediction, lab-result submission — are gated by an API key when any key is configured.

When ``NATURASCREEN_API_KEYS`` is empty the API is in OPEN mode (local/dev) and the gate
is a no-op. In any public deployment, set keys; requests then need ``X-API-Key`` (or
``Authorization: Bearer <key>``). This is deliberately simple and stateless — appropriate
for a research tool, with no patient data and no accounts.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


def _matches(presented: str, configured: list[str]) -> bool:
    # constant-time compare against each configured key
    return any(hmac.compare_digest(presented, key) for key in configured)


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    """FastAPI dependency: enforce a valid API key when keys are configured."""
    keys = get_settings().api_key_list
    if not keys:
        return  # OPEN mode — no keys configured (local/dev)

    presented = x_api_key
    if presented is None and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()

    if not presented or not _matches(presented, keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
