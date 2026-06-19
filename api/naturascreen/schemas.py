"""Pydantic DTOs and the type-enforced safety-notice bases.

The two safety notices (spec §3, §7) are enforced structurally rather than by
convention: any response that must carry a notice inherits a base model whose notice
field defaults to the canonical constant. Because the field exists on the base and is
non-optional, it is always serialized — a developer cannot ship a results or report
payload that omits it. This is the schema half of "the type system enforces it".
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .disclaimer import DISCLAIMER, SIMULATION_NOTICE


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Disclaimed(BaseModel):
    """Base for every results/report response — carries the cure-boundary disclaimer."""

    disclaimer: str = Field(default=DISCLAIMER)


class Illustrated(BaseModel):
    """Base for every simulation / frame / results / report payload — illustrative notice."""

    illustrative_notice: str = Field(default=SIMULATION_NOTICE)


class SafetyEnvelope(Disclaimed, Illustrated):
    """Carries both notices, for results and report payloads."""


# --- Compounds (Compounds phase) ---


class CompoundOut(ORMModel):
    id: int
    name: str
    smiles: str
    inchikey: str | None = None
    source_organism: str | None = None
    source_db: str
    coconut_id: str | None = None
    molecular_descriptors: dict = Field(default_factory=dict)
    references: list = Field(default_factory=list)
    created_at: datetime


class CompoundPage(BaseModel):
    items: list[CompoundOut]
    total: int
    limit: int
    offset: int
