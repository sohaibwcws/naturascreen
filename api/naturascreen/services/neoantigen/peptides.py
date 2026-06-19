"""Candidate MHC class I neoepitope generation from a mutated protein context.

Pure string code (no heavy dependencies, so this is exercised in the
dependency-light core test path): tile k-mers across a mutated protein sequence
and keep only the windows that span the mutated residue. A neoepitope is only
worth predicting if the mutation falls *inside* the presented peptide — a window
that does not cover the mutated position is identical to wild-type and tells us
nothing about a tumor-specific target.
"""

from __future__ import annotations

# Canonical MHC class I peptide lengths. 8-11mers cover the overwhelming majority
# of peptides presented by HLA-A/B/C (9mers dominate); longer/shorter peptides are
# rare enough to ignore for candidate generation.
MHC_I_LENGTHS: tuple[int, ...] = (8, 9, 10, 11)


def windows(
    sequence: str,
    mutation_pos: int,
    lengths: tuple[int, ...] = MHC_I_LENGTHS,
) -> list[str]:
    """Unique k-mer peptides tiling ``sequence`` that include the mutated residue.

    Parameters
    ----------
    sequence:
        The mutated protein context. The residue at ``mutation_pos`` is the
        substituted (neo) residue. Embedded whitespace is stripped and the
        sequence is upper-cased so peptides are directly comparable across alleles.
    mutation_pos:
        0-based index of the mutated residue within the cleaned ``sequence``.
    lengths:
        Peptide lengths to generate (default 8-11). Non-positive lengths are
        ignored defensively.

    Returns
    -------
    list[str]
        Unique peptides, each containing the mutated residue, in deterministic
        order (ascending start position, then ascending length). The first
        occurrence of a duplicate peptide wins, so the output is stable.

    Raises
    ------
    ValueError
        If ``mutation_pos`` is outside the cleaned sequence.
    """
    seq = "".join(sequence.split()).upper()
    n = len(seq)
    if n == 0:
        return []
    if not 0 <= mutation_pos < n:
        raise ValueError(
            f"mutation_pos {mutation_pos} out of range for sequence of length {n}"
        )

    seen: set[str] = set()
    out: list[str] = []
    for start in range(n):
        for length in lengths:
            if length <= 0:
                continue
            end = start + length
            if end > n:
                continue
            # The window [start, end) covers the mutation iff start <= pos < end.
            if not start <= mutation_pos < end:
                continue
            peptide = seq[start:end]
            if peptide not in seen:
                seen.add(peptide)
                out.append(peptide)
    return out
