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


# --- Targets (used by the experiment builder; full curation in the docking phase) ---


class TargetOut(ORMModel):
    id: int
    type: str
    pdb_id: str | None = None
    gene: str | None = None
    description: str | None = None
    dockable: bool
    box_source: str | None = None


# --- Experiments ---


class ExperimentCreate(BaseModel):
    target_id: int | None = None
    compound_set: list[int] = Field(default_factory=list)
    weights: dict[str, float] | None = None
    seed: int = 0


class ExperimentOut(ORMModel):
    id: int
    status: str
    target_id: int | None
    compound_set: list
    weights: dict
    error: str | None
    created_at: datetime


# --- Live simulation stream (spec §3) ---
#
# Two message types flow over the websocket. StreamMeta is sent first and carries BOTH
# safety notices; the viewer is hard-gated on it (it refuses to render cells without an
# active notice overlay). Every Frame ALSO carries the illustrative notice — the per-run
# total is ~120 frames, so the overhead is trivial and any frame inspected in isolation
# still carries the boundary.


class StreamMeta(SafetyEnvelope):
    type: str = "meta"
    effectiveness: float
    seed: int
    steps: int
    transfer: dict  # the HeuristicEffectTransfer parameters, surfaced as illustrative
    source: str  # "experiment:{id}" or "sandbox"


class FrameOut(Illustrated):
    type: str = "frame"
    t: int
    time: float
    positions: list[float]
    states: list[int]
    population: int
    baseline_population: int
    counts: dict[str, int] = Field(default_factory=dict)


class StreamEnd(Illustrated):
    type: str = "end"
    final_population: int
    baseline_population: int
    reduction_pct: float


# --- Experiment results / ranking ---


class ScoredCompoundOut(BaseModel):
    compound_id: int
    name: str
    coconut_id: str | None
    smiles: str
    rank: int
    combined_score: float
    normalized: dict[str, float | None]
    breakdown: dict
    warnings: list[str] = Field(default_factory=list)


class SimulationSummary(BaseModel):
    compound_id: int
    baseline_population: int
    final_population: int
    reduction_pct: float


class ExperimentResults(SafetyEnvelope):
    experiment: ExperimentOut
    ranked: list[ScoredCompoundOut]
    simulation: SimulationSummary | None = None


# --- Candidate hypothesis report (PRD §8 candidate report; carries both notices) ---


class CandidateReport(SafetyEnvelope):
    experiment_id: int
    generated_at: datetime
    rank: int
    combined_score: float
    compound: dict
    target: dict | None = None
    subscores: dict
    simulation: SimulationSummary | None = None
    predicted_mechanism: str
    caveats: list[str] = Field(default_factory=list)
    references: list = Field(default_factory=list)


# --- Feedback loop (real lab results -> retraining labels) ---


class LabResultIn(BaseModel):
    compound_id: int
    target_id: int | None = None
    measured_ic50: float = Field(gt=0, description="measured IC50 in micromolar")
    source: str = Field(min_length=1, max_length=256)
    verified: bool = False


class LabResultOut(ORMModel):
    id: int
    compound_id: int
    target_id: int | None
    measured_ic50: float
    source: str
    verified: bool
    created_at: datetime
