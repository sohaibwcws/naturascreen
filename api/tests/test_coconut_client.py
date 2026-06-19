"""COCONUT client paging + de-duplication, against a mocked search endpoint."""

from __future__ import annotations

import httpx
import respx

from naturascreen.services.compounds.coconut import iter_records


def _page(page: int, last_page: int, rows: list[dict]) -> dict:
    return {"data": {"current_page": page, "last_page": last_page, "data": rows}}


@respx.mock
async def test_iter_records_pages_and_dedups():
    route = respx.post("https://x/api/search")
    route.side_effect = [
        httpx.Response(
            200,
            json=_page(
                1,
                2,
                [
                    {"identifier": "A", "canonical_smiles": "CCO", "name": "a"},
                    {"identifier": "B", "canonical_smiles": "CCN", "name": "b"},
                ],
            ),
        ),
        httpx.Response(
            200,
            json=_page(
                2,
                2,
                [
                    {"identifier": "B", "canonical_smiles": "CCN", "name": "b"},  # dup
                    {"identifier": "C", "canonical_smiles": "CCC", "name": "c"},
                    {"identifier": "D", "name": "no-smiles"},  # dropped
                ],
            ),
        ),
    ]

    got = [
        rec.coconut_id
        async for rec in iter_records("q", base="https://x/api", page_size=2, max_records=100)
    ]
    assert got == ["A", "B", "C"]  # B de-duplicated, D dropped (no SMILES)


@respx.mock
async def test_iter_records_respects_max():
    respx.post("https://x/api/search").mock(
        return_value=httpx.Response(
            200,
            json=_page(
                1,
                99,
                [{"identifier": f"X{i}", "canonical_smiles": "C", "name": f"x{i}"} for i in range(50)],
            ),
        )
    )
    got = [
        rec.coconut_id
        async for rec in iter_records("q", base="https://x/api", page_size=50, max_records=5)
    ]
    assert len(got) == 5
