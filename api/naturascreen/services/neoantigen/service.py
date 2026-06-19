"""Persist and rank MHCflurry presentation predictions as ``Neoantigen`` rows.

This is the database-facing half of the neoantigen channel: it asks the predictor
for presentation scores, stores them, and returns them ranked by presentation
%rank (ascending = strongest presentation first). It never fabricates rows — when
MHCflurry is not provisioned the predictor raises ``AdapterUnavailable`` and that
propagates unchanged to the caller (the router turns it into a 503).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Neoantigen
from .predictor import predict_presentation

# MHCflurry presentation %rank thresholds (the field's conventional cutoffs):
# rank <= 0.5 is a strong binder/presented epitope, <= 2.0 a weak one. Anything
# above ~2 is unlikely to be presented.
STRONG_RANK: float = 0.5
WEAK_RANK: float = 2.0


def binder_class(presentation_rank: float | None) -> str:
    """Classify a presentation %rank as ``strong`` / ``weak`` / ``non-binder``.

    ``None`` (rank could not be computed) maps to ``unscored``.
    """
    if presentation_rank is None:
        return "unscored"
    if presentation_rank <= STRONG_RANK:
        return "strong"
    if presentation_rank <= WEAK_RANK:
        return "weak"
    return "non-binder"


def _rank_key(row: Neoantigen) -> tuple[bool, float]:
    """Sort key: real ranks ascending (strongest first), ``None`` ranks last."""
    rank = row.presentation_rank
    return (rank is None, rank if rank is not None else 0.0)


async def predict(
    session: AsyncSession,
    tumor_type: str,
    alleles: list[str],
    peptides: list[str],
) -> list[Neoantigen]:
    """Predict presentation for every peptide×allele pair, persist, return ranked.

    Persists one ``Neoantigen`` row per prediction (``binding_score`` = affinity in
    nM, ``presentation_rank`` = MHCflurry %rank) and returns them ranked by
    presentation %rank ascending — strongest presentation first, unscored rows
    last.

    Raises
    ------
    AdapterUnavailable
        Propagated from the predictor when MHCflurry is not provisioned. No rows
        are written in that case.
    """
    predictions = predict_presentation(peptides, alleles)

    rows: list[Neoantigen] = []
    for pred in predictions:
        row = Neoantigen(
            tumor_type=tumor_type,
            peptide=pred["peptide"],
            mhc_allele=pred["allele"],
            binding_score=pred["affinity_nM"],
            presentation_rank=pred["presentation_rank"],
        )
        session.add(row)
        rows.append(row)

    if rows:
        await session.commit()
        for row in rows:
            await session.refresh(row)

    rows.sort(key=_rank_key)
    return rows
