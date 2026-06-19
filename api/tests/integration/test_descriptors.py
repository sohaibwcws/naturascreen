"""RDKit descriptor + structure-depiction path. Skips where RDKit is unavailable."""

from __future__ import annotations

import pytest

pytest.importorskip("rdkit")

from naturascreen.services.compounds.descriptors import FEATURE_KEYS, compute  # noqa: E402
from naturascreen.services.compounds.draw import draw_svg  # noqa: E402

CURCUMIN = "COc1cc(/C=C/C(=O)CC(=O)/C=C/c2ccc(O)c(OC)c2)ccc1O"


def test_compute_real_descriptors():
    result = compute(CURCUMIN)
    assert result is not None
    inchikey, descriptors = result
    assert inchikey and len(inchikey) == 27  # standard InChIKey length
    # curcumin's molecular weight is ~368.4
    assert 360 < descriptors["molecular_weight"] < 375
    assert all(k in descriptors for k in FEATURE_KEYS)
    assert descriptors["ecfp4_nbits"] == 2048
    assert len(descriptors["ecfp4_onbits"]) > 0


def test_compute_rejects_invalid_smiles():
    assert compute("this is not a molecule") is None


def test_draw_svg_renders():
    svg = draw_svg(CURCUMIN)
    assert svg is not None and "<svg" in svg
    assert draw_svg("nonsense!!!") is None
