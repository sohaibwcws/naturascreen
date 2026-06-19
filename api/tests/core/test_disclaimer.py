"""The safety notices must be impossible to omit from a payload that should carry them.

This is the structural half of the honesty guarantee: if these tests pass, no results or
report DTO can be serialized without its notice, regardless of how a caller constructs it.
"""

from __future__ import annotations

from pydantic import BaseModel

from naturascreen.disclaimer import DISCLAIMER, RESPONSE_OOD_NOTICE, SIMULATION_NOTICE
from naturascreen.schemas import Disclaimed, Illustrated, SafetyEnvelope


def test_notice_constants_are_meaningful():
    assert "not" in DISCLAIMER.lower() and "treatment" in DISCLAIMER.lower()
    assert "illustrat" in SIMULATION_NOTICE.lower()
    assert "not a prediction" in SIMULATION_NOTICE.lower()
    assert "out-of-distribution" in RESPONSE_OOD_NOTICE.lower()


def test_disclaimed_always_serializes_disclaimer():
    class Result(Disclaimed):
        rank: int

    payload = Result(rank=1).model_dump()
    assert payload["disclaimer"] == DISCLAIMER


def test_illustrated_always_serializes_notice():
    class Frame(Illustrated):
        t: int

    payload = Frame(t=0).model_dump()
    assert payload["illustrative_notice"] == SIMULATION_NOTICE


def test_safety_envelope_carries_both():
    class Report(SafetyEnvelope):
        compound: str

    payload = Report(compound="curcumin").model_dump()
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["illustrative_notice"] == SIMULATION_NOTICE


def test_subclass_cannot_drop_notice_by_construction():
    # A subclass that forgets the notice still gets it from the base — there is no
    # constructor path that yields a payload without the field.
    class Sloppy(SafetyEnvelope):
        value: float

    fields = Sloppy.model_fields
    assert "disclaimer" in fields
    assert "illustrative_notice" in fields
