"""Ingest natural compounds into the library.

Two real sources, both flowing through the same upsert:
- COCONUT public search API (``--query`` / ``--all``), the live CC0 source.
- A bulk CSV download from COCONUT (``--csv path``), for large offline loads.

Run inside the worker/api container (needs RDKit + the database), e.g.:
    python -m naturascreen.services.compounds.ingest --query curcumin --max 200
    python -m naturascreen.services.compounds.ingest --csv /data/coconut.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from collections.abc import Iterator
from pathlib import Path

from ...db import get_sessionmaker
from .coconut import CompoundRecord, iter_records, parse_record
from .service import upsert_compounds

log = logging.getLogger(__name__)

_CSV_ALIASES = {
    "identifier": "identifier",
    "coconut_id": "identifier",
    "id": "identifier",
    "canonical_smiles": "canonical_smiles",
    "smiles": "canonical_smiles",
    "name": "name",
    "iupac_name": "iupac_name",
    "iupac": "iupac_name",
}


def _rows_from_csv(path: Path) -> Iterator[CompoundRecord]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            mapped: dict = {}
            for key, value in row.items():
                if key is None:
                    continue
                canonical = _CSV_ALIASES.get(key.strip().lower())
                if canonical:
                    mapped[canonical] = value
            rec = parse_record(mapped)
            if rec is not None:
                yield rec


async def _ingest_api(query: str, search_type: str, max_records: int, page_size: int) -> int:
    batch: list[CompoundRecord] = []
    written = 0
    sessionmaker = get_sessionmaker()
    async for rec in iter_records(
        query, search_type=search_type, max_records=max_records, page_size=page_size
    ):
        batch.append(rec)
        if len(batch) >= 100:
            async with sessionmaker() as session:
                written += await upsert_compounds(session, batch)
            log.info("ingested %d compounds so far", written)
            batch = []
    if batch:
        async with sessionmaker() as session:
            written += await upsert_compounds(session, batch)
    return written


async def _ingest_csv(path: Path, batch_size: int = 500) -> int:
    written = 0
    batch: list[CompoundRecord] = []
    sessionmaker = get_sessionmaker()
    for rec in _rows_from_csv(path):
        batch.append(rec)
        if len(batch) >= batch_size:
            async with sessionmaker() as session:
                written += await upsert_compounds(session, batch)
            log.info("ingested %d compounds so far", written)
            batch = []
    if batch:
        async with sessionmaker() as session:
            written += await upsert_compounds(session, batch)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest natural compounds from COCONUT.")
    parser.add_argument("--query", default="", help="text search query (e.g. a scaffold or name)")
    parser.add_argument(
        "--all", action="store_true", help="ingest broadly (uses a wildcard-ish common query)"
    )
    parser.add_argument("--type", default="text", dest="search_type")
    parser.add_argument("--max", type=int, default=500, dest="max_records")
    parser.add_argument("--limit", type=int, default=50, dest="page_size", help="page size")
    parser.add_argument("--csv", type=Path, default=None, help="bulk COCONUT CSV path")
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()

    if args.csv is not None:
        written = asyncio.run(_ingest_csv(args.csv))
    else:
        query = args.query or ("C" if args.all else "")
        if not query:
            parser.error("provide --query TEXT, or --all, or --csv PATH")
        written = asyncio.run(
            _ingest_api(query, args.search_type, args.max_records, args.page_size)
        )
    log.info("done: %d compounds upserted", written)


if __name__ == "__main__":
    main()
