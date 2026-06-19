"""Applicability-domain math (spec §5) — pure, exact, no heavy deps.

These are load-bearing: the whole honesty story for the response channel rests on the
Tanimoto distance being correct, so the values are asserted exactly, not approximately.
"""

from __future__ import annotations

from naturascreen.services.response.applicability import (
    DEFAULT_AD_THRESHOLD,
    in_domain,
    nearest_neighbor_tanimoto,
    tanimoto,
)


def test_tanimoto_identical_sets_is_one():
    assert tanimoto([1, 5, 9, 42], [42, 9, 5, 1]) == 1.0  # order-independent


def test_tanimoto_disjoint_sets_is_zero():
    assert tanimoto([1, 2, 3], [4, 5, 6]) == 0.0


def test_tanimoto_partial_overlap_exact_value():
    # A = {1,2,3,4}, B = {3,4,5,6}; intersection {3,4}=2, union {1..6}=6 -> 2/6.
    assert tanimoto([1, 2, 3, 4], [3, 4, 5, 6]) == 2 / 6


def test_tanimoto_handles_duplicate_bits_as_sets():
    # Duplicates collapse: {1,2} vs {2,2} -> intersection {2}=1, union {1,2}=2 -> 0.5.
    assert tanimoto([1, 2, 2], [2, 2]) == 0.5


def test_tanimoto_two_empty_fingerprints_is_zero_not_one():
    # A molecule with no on-bits carries no evidence of similarity: flagged OOD, never trusted.
    assert tanimoto([], []) == 0.0
    assert tanimoto([1, 2, 3], []) == 0.0


def test_nearest_neighbor_takes_the_max():
    query = [1, 2, 3, 4]
    training = [
        [4, 5, 6, 7],        # overlap {4} -> 1/7
        [1, 2, 3, 4],        # identical -> 1.0
        [1, 2, 9, 10],       # overlap {1,2} -> 2/6
    ]
    assert nearest_neighbor_tanimoto(query, training) == 1.0


def test_nearest_neighbor_empty_training_is_zero():
    assert nearest_neighbor_tanimoto([1, 2, 3], []) == 0.0


def test_in_domain_threshold_behavior():
    assert in_domain(0.5) is True
    assert in_domain(0.1) is False
    # Boundary is inclusive: exactly at the threshold is in-domain.
    assert in_domain(DEFAULT_AD_THRESHOLD) is True
    assert in_domain(DEFAULT_AD_THRESHOLD - 1e-9) is False


def test_in_domain_custom_threshold():
    assert in_domain(0.4, threshold=0.5) is False
    assert in_domain(0.6, threshold=0.5) is True
