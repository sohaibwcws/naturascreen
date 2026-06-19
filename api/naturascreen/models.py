"""ORM models — PRD §10 data model plus scientific-honesty / curation additions.

Additions beyond the PRD table list, each tied to a spec decision:
- ``Target`` carries an explicit docking box + ``dockable`` flag (spec §6): a target is
  not dockable until a human curates its pocket box, so docking can never emit a score
  against an undefined search space.
- ``ResponsePrediction`` carries an applicability-domain flag (spec §5): the response
  model is OOD for most natural products, surfaced per prediction.
- ``SimulationRun`` persists ``illustrative_notice`` (spec §3).
- ``EffectivenessScore`` persists a full per-sub-score ``breakdown`` (spec §4.4) so the
  ranking is auditable, not a black box.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TargetType(str, enum.Enum):
    protein = "protein"
    neoantigen = "neoantigen"


class ExperimentStatus(str, enum.Enum):
    created = "created"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Compound(Base):
    __tablename__ = "compounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    smiles: Mapped[str] = mapped_column(Text)
    inchikey: Mapped[str | None] = mapped_column(String(27), index=True, default=None)
    source_organism: Mapped[str | None] = mapped_column(String(512), default=None)
    source_db: Mapped[str] = mapped_column(String(64))
    coconut_id: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    # RDKit descriptors used as response-model features and applicability-domain checks.
    molecular_descriptors: Mapped[dict] = mapped_column(JSON, default=dict)
    references: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[TargetType] = mapped_column(Enum(TargetType), default=TargetType.protein)
    pdb_id: Mapped[str | None] = mapped_column(String(16), default=None)
    gene: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Docking search box (spec §6) — curated, not baked. dockable stays False until set.
    dockable: Mapped[bool] = mapped_column(Boolean, default=False)
    box_center_x: Mapped[float | None] = mapped_column(Float, default=None)
    box_center_y: Mapped[float | None] = mapped_column(Float, default=None)
    box_center_z: Mapped[float | None] = mapped_column(Float, default=None)
    box_size_x: Mapped[float | None] = mapped_column(Float, default=None)
    box_size_y: Mapped[float | None] = mapped_column(Float, default=None)
    box_size_z: Mapped[float | None] = mapped_column(Float, default=None)
    box_source: Mapped[str | None] = mapped_column(Text, default=None)  # provenance citation

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Neoantigen(Base):
    __tablename__ = "neoantigens"

    id: Mapped[int] = mapped_column(primary_key=True)
    tumor_type: Mapped[str] = mapped_column(String(128), index=True)
    peptide: Mapped[str] = mapped_column(String(64))
    mhc_allele: Mapped[str] = mapped_column(String(64))
    binding_score: Mapped[float | None] = mapped_column(Float, default=None)  # affinity nM
    presentation_rank: Mapped[float | None] = mapped_column(Float, default=None)  # MHCflurry %rank
    structure_uri: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(128), default=None)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), default=None)
    compound_set: Mapped[list] = mapped_column(JSON, default=list)  # list[int] compound ids
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus), default=ExperimentStatus.created
    )
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    target: Mapped["Target | None"] = relationship(lazy="selectin")


class DockingResult(Base):
    __tablename__ = "docking_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"))
    binding_affinity: Mapped[float] = mapped_column(Float)  # kcal/mol
    pose_uri: Mapped[str | None] = mapped_column(Text, default=None)
    box_used: Mapped[dict] = mapped_column(JSON, default=dict)  # the search box that produced it
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResponsePrediction(Base):
    __tablename__ = "response_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), index=True)
    cell_line: Mapped[str] = mapped_column(String(128))
    predicted_ic50: Mapped[float] = mapped_column(Float)  # micromolar
    # Applicability domain (spec §5): is this compound near the model's training set?
    applicability_in_domain: Mapped[bool] = mapped_column(Boolean, default=True)
    nn_tanimoto: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), index=True)
    baseline_population: Mapped[int] = mapped_column(Integer)
    final_population: Mapped[int] = mapped_column(Integer)
    reduction_pct: Mapped[float] = mapped_column(Float)
    frames_uri: Mapped[str | None] = mapped_column(Text, default=None)
    illustrative_notice: Mapped[str] = mapped_column(Text)  # spec §3, persisted with the run
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EffectivenessScore(Base):
    __tablename__ = "effectiveness_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), index=True)
    binding_score: Mapped[float | None] = mapped_column(Float, default=None)
    neoantigen_score: Mapped[float | None] = mapped_column(Float, default=None)
    response_score: Mapped[float | None] = mapped_column(Float, default=None)
    simulation_score: Mapped[float | None] = mapped_column(Float, default=None)
    combined_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    # Per-sub-score audit trail: raw, window, normalized, weight, contribution (spec §4.4).
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    compound_id: Mapped[int] = mapped_column(ForeignKey("compounds.id"), index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), default=None)
    measured_ic50: Mapped[float] = mapped_column(Float)  # micromolar
    source: Mapped[str] = mapped_column(String(256))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
