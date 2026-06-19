"""Combine sub-scores into a single effectiveness score — exposed and auditable.

Rules (spec §4):
- Normalize each present sub-score via its reference window.
- Combine only the sub-scores that are present AND carry weight; renormalize those weights
  to sum to 1. Missing sub-scores are EXCLUDED, never imputed as 0 — "not measured" must
  not be punished as "no effect".
- ``simulation`` defaults to weight 0 (circularity guard): its reduction is derived from
  binding+response, so weighting it double-counts. If a caller weights it, a warning is
  emitted and surfaced in the report.
- The returned breakdown records raw · window · normalized · requested weight · effective
  weight · contribution per sub-score, so the ranking is never a black box.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .normalization import WINDOWS

CHANNELS = ("binding", "neoantigen", "response", "simulation")

# Default weights — note simulation = 0 (illustrative term excluded from the rank).
DEFAULT_WEIGHTS: dict[str, float] = {
    "binding": 0.40,
    "neoantigen": 0.25,
    "response": 0.35,
    "simulation": 0.0,
}


@dataclass
class ScoreResult:
    combined_score: float
    breakdown: dict[str, dict]
    normalized: dict[str, float | None]
    available: list[str]
    missing: list[str]
    warnings: list[str] = field(default_factory=list)


def score_compound(
    raw: dict[str, float | None], weights: dict[str, float] | None = None
) -> ScoreResult:
    """Score one compound from its raw sub-scores (any of which may be missing)."""
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    breakdown: dict[str, dict] = {}
    normalized: dict[str, float | None] = {}
    contributing: dict[str, tuple[float, float]] = {}  # channel -> (normalized, weight)
    missing: list[str] = []

    for channel in CHANNELS:
        window = WINDOWS[channel]
        value = raw.get(channel)
        weight = float(weights.get(channel, 0.0))
        if value is None:
            normalized[channel] = None
            missing.append(channel)
            breakdown[channel] = {
                "available": False,
                "raw": None,
                "normalized": None,
                "window": window.as_dict(),
                "weight_requested": weight,
                "weight_effective": 0.0,
                "contribution": 0.0,
            }
            continue
        norm = window.normalize(float(value))
        normalized[channel] = round(norm, 4)
        breakdown[channel] = {
            "available": True,
            "raw": round(float(value), 4),
            "normalized": round(norm, 4),
            "window": window.as_dict(),
            "weight_requested": weight,
            "weight_effective": 0.0,  # filled after renormalization
            "contribution": 0.0,
        }
        if weight > 0:
            contributing[channel] = (norm, weight)

    warnings: list[str] = []
    if weights.get("simulation", 0.0) > 0 and raw.get("simulation") is not None:
        warnings.append(
            "Simulation term has non-zero weight: its reduction is derived from binding + "
            "response and therefore double-counts them. It is illustrative, not an "
            "independent measurement."
        )

    weight_sum = sum(w for _, w in contributing.values())
    combined = 0.0
    if weight_sum > 0:
        for channel, (norm, weight) in contributing.items():
            eff = weight / weight_sum
            contribution = eff * norm
            combined += contribution
            breakdown[channel]["weight_effective"] = round(eff, 4)
            breakdown[channel]["contribution"] = round(contribution, 4)
    else:
        warnings.append("No weighted sub-scores were available; combined score is 0.")

    available = [c for c in CHANNELS if breakdown[c]["available"]]
    return ScoreResult(
        combined_score=round(combined, 4),
        breakdown=breakdown,
        normalized=normalized,
        available=available,
        missing=missing,
        warnings=warnings,
    )


def rank_results(results: dict[int, ScoreResult]) -> dict[int, int]:
    """Return compound_id -> 1-based rank, highest combined score first (ties by id)."""
    ordered = sorted(results.items(), key=lambda kv: (-kv[1].combined_score, kv[0]))
    return {compound_id: i + 1 for i, (compound_id, _) in enumerate(ordered)}
