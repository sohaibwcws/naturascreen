"""Cell-line response sub-score: predicted ln(IC50 µM) from an XGBoost regressor.

This package is the ``response`` channel of the scoring seam (see
``services/subscores.py``). Its public entry point is ``adapter.score``; the supporting
modules are split by concern so the dependency-light parts stay importable without the
heavy ML stack:

- ``features``      — pure projection of RDKit descriptors onto the model's feature order.
- ``applicability`` — pure ECFP Tanimoto applicability-domain math (spec §5).
- ``model``         — load/save the XGBoost regressor + its AD/metric meta sidecar.
- ``train``         — CLI that fits the model on REAL public GDSC1 data (never fabricated).
- ``adapter``       — the ``score`` coroutine wired into the pipeline.

Scientific honesty: the model is trained on GDSC, a screen of *synthetic* drugs, so it is
out-of-distribution for most natural products. The applicability domain makes that visible
rather than hiding it; nothing here invents a number when the model is not provisioned.
"""
