"""Parsing the COCONUT search payload — recorded real rows (captured 2026-06-19).

The mapping is the boundary between a third-party API shape we don't control and our
domain model. It must drop rows that can't be docked/simulated (no SMILES, no id) rather
than store junk, and it must pull the COCONUT id + name + canonical SMILES from the real
field names.
"""

from __future__ import annotations

from naturascreen.services.compounds.coconut import parse_record

# Verbatim rows from POST https://coconut.naturalproducts.net/api/search
VALID_ROW = {
    "identifier": "CNP0288229.0",
    "canonical_smiles": "COC1=CC(CCC(=O)CC(=O)CCC2=CC=C(O)C(OC)=C2)=CC=C1O",
    "annotation_level": 4,
    "name": "Tetrahydrocurcumin",
    "iupac_name": "1,7-bis(4-hydroxy-3-methoxy-phenyl)heptane-3,5-dione",
    "organism_count": 2,
    "active": True,
}


def test_parses_real_row():
    rec = parse_record(VALID_ROW)
    assert rec is not None
    assert rec.coconut_id == "CNP0288229.0"
    assert rec.name == "Tetrahydrocurcumin"
    assert rec.smiles.startswith("COC1=CC")
    assert rec.iupac_name and "heptane" in rec.iupac_name
    assert rec.annotation_level == 4


def test_drops_row_without_smiles():
    assert parse_record({"identifier": "CNP0000000.0", "name": "x"}) is None


def test_drops_row_without_identifier():
    assert parse_record({"canonical_smiles": "CCO", "name": "ethanol"}) is None


def test_falls_back_to_identifier_when_name_missing():
    rec = parse_record({"identifier": "CNP0000001.0", "canonical_smiles": "CCO"})
    assert rec is not None
    assert rec.name == "CNP0000001.0"
