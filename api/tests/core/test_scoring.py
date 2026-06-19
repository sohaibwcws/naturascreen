"""Scoring + normalization invariants (spec §4) — the core scientific decision."""

from __future__ import annotations

import math

from naturascreen.services.scoring.normalization import WINDOWS
from naturascreen.services.scoring.scoring import rank_results, score_compound


def test_window_direction_and_clamp():
    binding = WINDOWS["binding"]
    assert binding.normalize(-6.0) == 0.0
    assert binding.normalize(-12.0) == 1.0
    assert binding.normalize(-9.0) == 0.5  # midpoint
    assert binding.normalize(-3.0) == 0.0  # clamped, not extrapolated
    assert binding.normalize(-20.0) == 1.0  # clamped

    response = WINDOWS["response"]
    assert response.normalize(math.log(100.0)) == 0.0
    assert response.normalize(math.log(0.01)) == 1.0
    assert response.normalize(math.log(1.0)) > 0  # 1 µM is decently potent


def test_contributions_sum_to_combined_and_weights_renormalize():
    res = score_compound(
        {"binding": -12.0, "neoantigen": 0.0, "response": math.log(0.01), "simulation": 0.5}
    )
    # simulation default weight 0 -> excluded from the combined score
    assert "simulation" not in [c for c in res.available if res.breakdown[c]["contribution"] > 0]
    eff_weights = sum(res.breakdown[c]["weight_effective"] for c in res.available)
    assert round(eff_weights, 4) == 1.0  # renormalized over contributing channels
    contrib = sum(res.breakdown[c]["contribution"] for c in res.breakdown)
    assert round(contrib, 4) == res.combined_score
    # all three contributing sub-scores at their max -> combined 1.0
    assert res.combined_score == 1.0


def test_missing_subscore_excluded_not_imputed_zero():
    # Only binding available, and it is strong. Missing response must not drag it down.
    only_binding = score_compound({"binding": -12.0, "neoantigen": None, "response": None})
    assert "response" in only_binding.missing
    assert only_binding.combined_score == 1.0  # full weight redistributed to binding


def test_circularity_guard_warns_when_simulation_weighted():
    weighted = score_compound(
        {"binding": -9.0, "response": math.log(1.0), "simulation": 0.8},
        weights={"binding": 0.3, "response": 0.3, "simulation": 0.4},
    )
    assert any("double-count" in w for w in weighted.warnings)

    default = score_compound({"binding": -9.0, "response": math.log(1.0), "simulation": 0.8})
    assert default.warnings == [] or all("double-count" not in w for w in default.warnings)


def test_binding_monotonicity():
    weak = score_compound({"binding": -7.0, "neoantigen": None, "response": None})
    strong = score_compound({"binding": -11.0, "neoantigen": None, "response": None})
    assert strong.combined_score > weak.combined_score


def test_rank_orders_by_combined_desc():
    a = score_compound({"binding": -11.0})
    b = score_compound({"binding": -7.0})
    c = score_compound({"binding": -9.0})
    ranks = rank_results({1: a, 2: b, 3: c})
    assert ranks == {1: 1, 3: 2, 2: 3}
