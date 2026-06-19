"""Client for COCONUT's public, unauthenticated search endpoint (CC0 data).

COCONUT 2.0 exposes ``POST /api/search`` (the "Advanced Molecule Search") without
authentication. It returns a Laravel paginator:

    {"data": {"current_page": 1, "last_page": 865, "total": 2594,
              "data": [{"identifier": "CNP0288229.0",
                        "canonical_smiles": "...", "name": "Tetrahydrocurcumin",
                        "iupac_name": "...", "annotation_level": 4, ...}, ...]}}

``parse_record`` is intentionally pure (no RDKit, no I/O) so the mapping is unit-tested
against a recorded fixture. Descriptor computation is a separate step (see descriptors).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from ...config import get_settings


@dataclass(frozen=True)
class CompoundRecord:
    coconut_id: str
    name: str
    smiles: str
    iupac_name: str | None
    annotation_level: int | None


def parse_record(raw: dict) -> CompoundRecord | None:
    """Map one COCONUT search row to a CompoundRecord, or None if unusable.

    A row without a SMILES string cannot be docked or simulated, so it is dropped.
    """
    smiles = (raw.get("canonical_smiles") or raw.get("smiles") or "").strip()
    identifier = (raw.get("identifier") or "").strip()
    if not smiles or not identifier:
        return None
    name = (raw.get("name") or "").strip() or identifier
    return CompoundRecord(
        coconut_id=identifier,
        name=name,
        smiles=smiles,
        iupac_name=(raw.get("iupac_name") or None),
        annotation_level=raw.get("annotation_level"),
    )


def _search_url(base: str | None = None) -> str:
    base = (base or get_settings().coconut_api_base).rstrip("/")
    return f"{base}/search"


async def search_page(
    client: httpx.AsyncClient,
    query: str,
    *,
    search_type: str = "text",
    limit: int = 50,
    page: int = 1,
    base: str | None = None,
) -> tuple[list[CompoundRecord], dict]:
    """Fetch one page; return (parsed records, paginator metadata without the rows)."""
    resp = await client.post(
        _search_url(base),
        json={"query": query, "type": search_type, "limit": limit, "page": page},
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    page_obj = resp.json().get("data", {})
    rows = page_obj.get("data", []) or []
    records = [r for r in (parse_record(row) for row in rows) if r is not None]
    meta = {k: v for k, v in page_obj.items() if k != "data"}
    return records, meta


async def iter_records(
    query: str,
    *,
    search_type: str = "text",
    max_records: int = 500,
    page_size: int = 50,
    base: str | None = None,
    timeout: float = 30.0,
) -> AsyncIterator[CompoundRecord]:
    """Page through COCONUT search results, de-duplicating by COCONUT id, up to max."""
    seen: set[str] = set()
    yielded = 0
    async with httpx.AsyncClient(timeout=timeout) as client:
        page = 1
        while yielded < max_records:
            records, meta = await search_page(
                client, query, search_type=search_type, limit=page_size, page=page, base=base
            )
            if not records:
                break
            for rec in records:
                if rec.coconut_id in seen:
                    continue
                seen.add(rec.coconut_id)
                yield rec
                yielded += 1
                if yielded >= max_records:
                    return
            last_page = meta.get("last_page")
            if last_page is not None and page >= last_page:
                break
            page += 1
