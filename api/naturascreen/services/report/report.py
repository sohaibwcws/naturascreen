"""Build the candidate hypothesis report (JSON) and render it to PDF.

The mechanism description and caveats are generated ONLY from the sub-scores actually
computed — the report never asserts a binding/response/neoantigen claim for a channel that
was not measured. Both safety notices are embedded in the JSON envelope and in the PDF body
(not just a header), per PRD §14.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...disclaimer import DISCLAIMER, RESPONSE_OOD_NOTICE, SIMULATION_NOTICE
from ...models import (
    Compound,
    EffectivenessScore,
    Experiment,
    ResponsePrediction,
    SimulationRun,
    Target,
)
from ...schemas import CandidateReport, SimulationSummary


async def build_report(session: AsyncSession, experiment_id: int) -> CandidateReport | None:
    """Assemble the report for the top-ranked compound, or None if not yet scored."""
    top = (
        await session.execute(
            select(EffectivenessScore)
            .where(EffectivenessScore.experiment_id == experiment_id)
            .order_by(EffectivenessScore.rank)
            .limit(1)
        )
    ).scalar_one_or_none()
    if top is None:
        return None

    experiment = (
        await session.execute(select(Experiment).where(Experiment.id == experiment_id))
    ).scalar_one()
    compound = (
        await session.execute(select(Compound).where(Compound.id == top.compound_id))
    ).scalar_one()
    target = (
        (await session.execute(select(Target).where(Target.id == experiment.target_id))).scalar_one_or_none()
        if experiment.target_id
        else None
    )
    sim_row = (
        await session.execute(
            select(SimulationRun).where(SimulationRun.experiment_id == experiment_id).limit(1)
        )
    ).scalar_one_or_none()
    response_row = (
        await session.execute(
            select(ResponsePrediction)
            .where(ResponsePrediction.experiment_id == experiment_id)
            .where(ResponsePrediction.compound_id == top.compound_id)
            .limit(1)
        )
    ).scalar_one_or_none()

    channels: dict = top.breakdown.get("channels", {})
    warnings: list[str] = list(top.breakdown.get("warnings", []))

    mechanism = _mechanism(channels, response_row)
    caveats = _caveats(channels, response_row, warnings)

    references: list = list(compound.references or [])
    if target and target.pdb_id:
        references.append({"pdb_id": target.pdb_id})
    if target and target.box_source:
        references.append({"docking_box": target.box_source})

    descriptors = {
        k: v
        for k, v in (compound.molecular_descriptors or {}).items()
        if not k.startswith("ecfp4")  # drop the fingerprint blob from the report
    }

    simulation = (
        SimulationSummary(
            compound_id=sim_row.compound_id,
            baseline_population=sim_row.baseline_population,
            final_population=sim_row.final_population,
            reduction_pct=sim_row.reduction_pct,
        )
        if sim_row
        else None
    )

    return CandidateReport(
        experiment_id=experiment_id,
        generated_at=datetime.now(timezone.utc),
        rank=top.rank,
        combined_score=top.combined_score,
        compound={
            "id": compound.id,
            "name": compound.name,
            "coconut_id": compound.coconut_id,
            "smiles": compound.smiles,
            "source_organism": compound.source_organism,
            "descriptors": descriptors,
        },
        target=(
            {"gene": target.gene, "pdb_id": target.pdb_id, "type": target.type.value}
            if target
            else None
        ),
        subscores=channels,
        simulation=simulation,
        predicted_mechanism=mechanism,
        caveats=caveats,
        references=references,
    )


def _mechanism(channels: dict, response_row: ResponsePrediction | None) -> str:
    parts: list[str] = []
    binding = channels.get("binding", {})
    if binding.get("available"):
        parts.append(
            f"Predicted to bind the target with a docking score of {binding['raw']} kcal/mol "
            f"(normalized {binding['normalized']})."
        )
    neo = channels.get("neoantigen", {})
    if neo.get("available"):
        parts.append(
            f"The target is a predicted tumor neoantigen (presentation %rank {neo['raw']})."
        )
    resp = channels.get("response", {})
    if resp.get("available"):
        ic50 = round(math.exp(resp["raw"]), 3)
        ood = response_row is not None and not response_row.applicability_in_domain
        parts.append(
            f"Predicted cell-line response IC50 ≈ {ic50} µM"
            + (" (out-of-distribution — low confidence)." if ood else ".")
        )
    if not parts:
        parts.append(
            "No docking, neoantigen, or response sub-scores were computed for this candidate; "
            "its ranking reflects only the signals that were available."
        )
    parts.append("The tumor simulation shown is illustrative, not a prediction of tumor response.")
    return " ".join(parts)


def _caveats(
    channels: dict, response_row: ResponsePrediction | None, warnings: list[str]
) -> list[str]:
    caveats = [
        "This is a research hypothesis, not validated for human use. It requires cell-culture, "
        "animal, and clinical work before it could be considered a treatment.",
        "The tumor simulation is a qualitative illustration of the effectiveness score, not a "
        "prediction of how this compound affects a real tumor.",
    ]
    if channels.get("binding", {}).get("available"):
        caveats.append(
            "Docking scores are noisy (±2-3 kcal/mol) and depend on the curated search box."
        )
    if channels.get("neoantigen", {}).get("available"):
        caveats.append("Neoantigen predictions have frequent false positives; treat as candidate targets.")
    if channels.get("response", {}).get("available"):
        caveats.append(RESPONSE_OOD_NOTICE)
    caveats.extend(warnings)
    return caveats


def render_pdf(report: CandidateReport) -> bytes:
    """Render the report to a PDF with both notices embedded in the body."""
    from io import BytesIO

    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    styles = getSampleStyleSheet()
    notice_style = ParagraphStyle(
        "notice", parent=styles["BodyText"], textColor="#8a5a00", backColor="#fff6e0",
        borderPadding=6, alignment=TA_LEFT, spaceAfter=10,
    )
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title=f"NaturaScreen candidate — exp {report.experiment_id}")
    flow = [
        Paragraph("NaturaScreen — Candidate Hypothesis", styles["Title"]),
        Paragraph(f"Experiment #{report.experiment_id} · generated {report.generated_at:%Y-%m-%d %H:%M UTC}", styles["Normal"]),
        Spacer(1, 6),
        Paragraph(f"<b>NOT A TREATMENT.</b> {report.disclaimer}", notice_style),
        Paragraph(f"<b>ILLUSTRATIVE SIMULATION.</b> {report.illustrative_notice}", notice_style),
        Spacer(1, 6),
        Paragraph(f"<b>Compound:</b> {report.compound['name']} ({report.compound.get('coconut_id') or '—'})", styles["BodyText"]),
        Paragraph(f"<b>SMILES:</b> {report.compound['smiles']}", styles["BodyText"]),
        Paragraph(f"<b>Rank:</b> {report.rank} &nbsp; <b>Combined score:</b> {report.combined_score}", styles["BodyText"]),
        Paragraph(f"<b>Predicted mechanism:</b> {report.predicted_mechanism}", styles["BodyText"]),
    ]
    if report.simulation:
        s = report.simulation
        flow.append(
            Paragraph(
                f"<b>Illustrative simulation:</b> untreated final {s.baseline_population}, "
                f"treated final {s.final_population}, reduction {s.reduction_pct}% (illustrative).",
                styles["BodyText"],
            )
        )
    flow.append(Spacer(1, 6))
    flow.append(Paragraph("<b>Caveats</b>", styles["Heading3"]))
    flow.append(
        ListFlowable(
            [ListItem(Paragraph(c, styles["BodyText"])) for c in report.caveats], bulletType="bullet"
        )
    )
    doc.build(flow)
    return buf.getvalue()
