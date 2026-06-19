"""Neoepitope k-mer windowing (pure, dependency-light core path).

These exercise ``windows`` without any heavy dependency, so they run under the
``make test-core`` environment (numpy/pydantic only) as well as the full suite.
"""

from __future__ import annotations

import pytest

from naturascreen.services.neoantigen.peptides import MHC_I_LENGTHS, windows

# 20 distinct standard residues: distinctness lets us locate each window uniquely
# via ``str.index`` and assert it actually spans the mutated position.
AA20 = "ACDEFGHIKLMNPQRSTVWY"


def test_every_window_spans_the_mutation_index():
    pos = 9
    peptides = windows(AA20, pos)
    assert peptides
    for pep in peptides:
        start = AA20.index(pep)  # unique residues -> exactly one location
        assert start <= pos < start + len(pep), f"{pep} does not span index {pos}"
        assert AA20[pos] in pep
        assert len(pep) in MHC_I_LENGTHS


def test_all_lengths_within_canonical_range():
    pos = 12
    for pep in windows(AA20, pos):
        assert 8 <= len(pep) <= 11


def test_dedups_identical_peptides():
    # A homopolymer collapses every same-length window to one peptide.
    peptides = windows("A" * 12, 5)
    assert len(peptides) == len(set(peptides))
    assert set(peptides) == {"A" * n for n in MHC_I_LENGTHS}


def test_window_must_cover_position_not_just_residue_value():
    # The unique 'X' sits at index 0; the mutation is the trailing 'Z'. No 8-11mer
    # that includes the last residue can also reach index 0, so 'X' must never
    # appear in any returned peptide even though both are single occurrences.
    seq = "X" + "A" * 12 + "Z"  # length 14, mutation at index 13
    peptides = windows(seq, 13)
    assert peptides
    for pep in peptides:
        assert pep.endswith("Z")
        assert "X" not in pep


def test_custom_lengths_only_generates_those_lengths():
    peptides = windows(AA20, 4, lengths=(9,))
    assert peptides
    assert all(len(p) == 9 for p in peptides)


def test_whitespace_stripped_and_uppercased():
    peptides = windows("ab cde fgh", 0)
    assert peptides == ["ABCDEFGH"]  # cleaned to 8 residues; only window covers pos 0


def test_out_of_range_mutation_raises():
    with pytest.raises(ValueError):
        windows("ACDEFGHIK", 99)
    with pytest.raises(ValueError):
        windows("ACDEFGHIK", -1)


def test_empty_sequence_returns_empty():
    assert windows("", 0) == []
    assert windows("   ", 0) == []
