"""Reference-window normalization (spec §4.1).

Every sub-score has different units, directions, and noise. We map each to [0, 1] via a
FIXED, documented reference window rather than batch min-max (so a compound's score does
not change based on what else was screened) or rank (which discards magnitude). A window
is ``(raw_at_zero, raw_at_one)``: the raw value that maps to 0 and the raw value that maps
to 1. Direction is encoded by which endpoint is which (e.g. binding's window runs from
-6 → 0 to -12 → 1, so more-negative binding scores higher). Values are clamped, never
extrapolated. The windows are surfaced per-compound in the report so the ranking is
auditable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    raw_at_zero: float
    raw_at_one: float
    unit: str
    note: str

    def normalize(self, raw: float) -> float:
        span = self.raw_at_one - self.raw_at_zero
        if span == 0:
            return 0.0
        t = (raw - self.raw_at_zero) / span
        return min(1.0, max(0.0, t))

    def as_dict(self) -> dict:
        return {
            "raw_at_zero": self.raw_at_zero,
            "raw_at_one": self.raw_at_one,
            "unit": self.unit,
            "note": self.note,
        }


# The single source of truth for how each sub-score becomes comparable. Configurable
# constants; their rationale is stated so the domain assumptions are in the open.
WINDOWS: dict[str, Window] = {
    "binding": Window(
        raw_at_zero=-6.0,
        raw_at_one=-12.0,
        unit="kcal/mol",
        note="Vina affinity; weaker than -6 is a non-specific floor, -12 saturates. "
        "Box-dependent and noisy (±2-3 kcal/mol).",
    ),
    "neoantigen": Window(
        raw_at_zero=2.0,
        raw_at_one=0.0,
        unit="MHCflurry presentation %rank",
        note="Allele-normalized presentation rank (lower = stronger). Gated by whether "
        "the target is a predicted neoantigen.",
    ),
    "response": Window(
        raw_at_zero=math.log(100.0),
        raw_at_one=math.log(0.01),
        unit="ln(IC50 µM)",
        note="Predicted potency; 100 µM (ineffective) → 0, 0.01 µM (very potent) → 1. "
        "Down-weighted/flagged when the compound is out-of-distribution.",
    ),
    "simulation": Window(
        raw_at_zero=0.0,
        raw_at_one=1.0,
        unit="population reduction fraction",
        note="Illustrative only and derived from the other sub-scores; default weight 0 "
        "to avoid double-counting (spec §4.3).",
    ),
}
