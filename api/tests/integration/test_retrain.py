"""Feedback retrain orchestration: parse base, augment, honest skip, lab→row bridge."""

from __future__ import annotations

import math

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from naturascreen import models  # noqa: F401
from naturascreen.config import Settings
from naturascreen.db import Base
from naturascreen.models import Compound, LabResult
from naturascreen.tasks import retrain


def test_read_base_and_write_augmented(tmp_path):
    base = tmp_path / "gdsc.csv"
    base.write_text("DRUG_NAME,SMILES,LN_IC50\nAspirin,CC(=O)Oc1ccccc1C(=O)O,2.3\nbad,,9\n")
    rows = retrain._read_base_rows(base)
    assert rows == [("CC(=O)Oc1ccccc1C(=O)O", 2.3)]  # empty-SMILES row dropped

    out = tmp_path / "aug.csv"
    retrain._write_augmented(out, rows, [("CCO", -1.0)])
    text = out.read_text().splitlines()
    assert text[0] == "SMILES,LN_IC50"
    assert "CCO,-1.0" in text
    assert len(text) == 3  # header + base + lab


async def test_retrain_skips_without_base_data(tmp_path, monkeypatch):
    monkeypatch.setattr(retrain, "get_settings", lambda: Settings(data_dir=str(tmp_path)))
    result = await retrain._retrain()
    assert result["status"] == "skipped"
    assert "not provisioned" in result["reason"]


async def test_gather_lab_rows_only_verified(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        s.add(Compound(id=1, name="A", smiles="CCO", source_db="COCONUT"))
        s.add(Compound(id=2, name="B", smiles="CCN", source_db="COCONUT"))
        s.add(LabResult(compound_id=1, measured_ic50=10.0, source="assay", verified=True))
        s.add(LabResult(compound_id=2, measured_ic50=5.0, source="assay", verified=False))
        await s.commit()

    monkeypatch.setattr(retrain, "get_sessionmaker", lambda: maker)
    rows = await retrain._gather_lab_rows()
    await engine.dispose()

    assert len(rows) == 1  # only the verified result
    smiles, ln = rows[0]
    assert smiles == "CCO"
    assert abs(ln - math.log(10.0)) < 1e-9
