"""Simulation engine invariants — the mechanics that must hold regardless of biology."""

from __future__ import annotations

from naturascreen.services.simulation.engine import (
    K_DEATH_INDUCTION,
    K_DIVISION_SUPPRESSION,
    SimConfig,
    heuristic_effect_transfer,
    simulate,
)

SMALL = SimConfig(initial_population=200, max_steps=40, max_cells=1500, seed=7)


def _final(config: SimConfig, effectiveness: float) -> int:
    last = 0
    for frame in simulate(config, effectiveness):
        last = frame.population
    return last


def test_transfer_endpoints_and_clamp():
    assert heuristic_effect_transfer(0.0) == (1.0, 1.0)
    div, death = heuristic_effect_transfer(1.0)
    assert div == 1.0 - K_DIVISION_SUPPRESSION
    assert death == 1.0 + K_DEATH_INDUCTION
    # Out-of-range inputs are clamped, never extrapolated.
    assert heuristic_effect_transfer(-5.0) == (1.0, 1.0)
    assert heuristic_effect_transfer(9.0) == heuristic_effect_transfer(1.0)


def test_deterministic_under_seed():
    assert _final(SMALL, 0.5) == _final(SMALL, 0.5)


def test_high_effectiveness_shrinks_relative_to_untreated():
    untreated = _final(SMALL, 0.0)
    treated = _final(SMALL, 1.0)
    assert treated < untreated
    # A strong effect should leave far fewer cells than no treatment.
    assert treated < untreated * 0.5


def test_frames_carry_aligned_baseline_and_notice_shape():
    frames = list(simulate(SMALL, 0.3))
    assert frames, "expected at least one frame"
    for f in frames:
        # positions are flat xyz triples matching the state count
        assert len(f.positions) == 3 * len(f.states)
        assert f.baseline_population >= 0
        assert f.population <= SMALL.max_cells
    # t increases monotonically from 0
    assert [f.t for f in frames][:3] == [0, 1, 2]


def test_population_never_exceeds_capacity():
    grow = SimConfig(initial_population=100, max_steps=60, max_cells=900, seed=3)
    peak = max(f.population for f in simulate(grow, 0.0))
    assert peak <= grow.max_cells
