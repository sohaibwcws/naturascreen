"""Neoantigen presentation prediction endpoints (MHCflurry-backed).

Request/response models live inline here (not in the shared ``schemas``) because
this is a self-contained adapter surface. When MHCflurry is not provisioned the
predict endpoint returns 503 with an actionable message rather than fabricating
predictions — a fake neoepitope is exactly the kind of false positive this tool
must never emit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Neoantigen
from ..services.neoantigen.service import STRONG_RANK, WEAK_RANK, binder_class, predict
from ..services.subscores import AdapterUnavailable
from ..security import require_api_key

router = APIRouter(prefix="/neoantigens", tags=["neoantigens"])

# Load-bearing honesty note carried on every response from this surface.
NEOANTIGEN_NOTE = (
    "Neoantigen presentation predictions have frequent false positives. A low "
    "presentation %rank flags a candidate epitope for laboratory validation "
    "(immunopeptidomics, T-cell assays), not a confirmed presented neoantigen. "
    "These are research candidates only, never a treatment claim."
)

# Surfaced verbatim as the 503 detail when MHCflurry is absent.
NOT_PROVISIONED_DETAIL = "MHCflurry not provisioned — run make data-mhcflurry"


class PredictRequest(BaseModel):
    """Body for ``POST /neoantigens/predict``."""

    tumor_type: str = Field(
        ..., min_length=1, description="Tumor / cohort label stored with each prediction"
    )
    hla_alleles: list[str] = Field(
        ..., min_length=1, description="MHC class I alleles, e.g. HLA-A*02:01"
    )
    peptides: list[str] = Field(
        ..., min_length=1, description="Candidate peptide sequences (8-11mers)"
    )


class PredictionOut(BaseModel):
    """One persisted (peptide, allele) presentation prediction."""

    id: int
    tumor_type: str
    peptide: str
    mhc_allele: str
    affinity_nM: float | None = Field(
        default=None, description="Predicted binding affinity KD in nM (lower = stronger)"
    )
    presentation_rank: float | None = Field(
        default=None, description="MHCflurry presentation %rank (lower = stronger)"
    )
    binder_class: str = Field(description="strong / weak / non-binder / unscored")

    @classmethod
    def from_row(cls, row: Neoantigen) -> "PredictionOut":
        return cls(
            id=row.id,
            tumor_type=row.tumor_type,
            peptide=row.peptide,
            mhc_allele=row.mhc_allele,
            affinity_nM=row.binding_score,
            presentation_rank=row.presentation_rank,
            binder_class=binder_class(row.presentation_rank),
        )


class PredictResponse(BaseModel):
    """Ranked predictions plus the honesty note and the binder-class thresholds."""

    note: str = NEOANTIGEN_NOTE
    strong_rank_threshold: float = STRONG_RANK
    weak_rank_threshold: float = WEAK_RANK
    count: int
    predictions: list[PredictionOut]


@router.post("/predict", response_model=PredictResponse, dependencies=[Depends(require_api_key)])
async def predict_neoantigens(
    body: PredictRequest, session: AsyncSession = Depends(get_session)
) -> PredictResponse:
    """Predict presentation for peptides×alleles, persist, and return ranked rows.

    Returns 503 (never fabricated predictions) when MHCflurry is not provisioned.
    """
    try:
        rows = await predict(session, body.tumor_type, body.hla_alleles, body.peptides)
    except AdapterUnavailable as exc:
        raise HTTPException(status_code=503, detail=NOT_PROVISIONED_DETAIL) from exc

    predictions = [PredictionOut.from_row(r) for r in rows]
    return PredictResponse(count=len(predictions), predictions=predictions)


@router.get("", response_model=PredictResponse)
async def list_neoantigens(
    tumor_type: str | None = Query(default=None, description="Filter by tumor type"),
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> PredictResponse:
    """List stored ``Neoantigen`` rows, strongest presentation first."""
    stmt = select(Neoantigen)
    if tumor_type:
        stmt = stmt.where(Neoantigen.tumor_type == tumor_type)
    stmt = stmt.order_by(
        Neoantigen.presentation_rank.is_(None),  # real ranks first, NULLs last
        Neoantigen.presentation_rank.asc(),
    ).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()
    predictions = [PredictionOut.from_row(r) for r in rows]
    return PredictResponse(count=len(predictions), predictions=predictions)
