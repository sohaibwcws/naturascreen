"""Persistence for the XGBoost response regressor + its applicability-domain sidecar.

Two artifacts live side by side in this package's ``artifacts/`` directory:

- ``response_model.ubj`` — the trained XGBoost regressor, in UBJSON (XGBoost's portable,
  default binary format).
- ``response_meta.json`` — everything inference needs *besides* the model weights: the
  training set's ECFP4 on-bit lists (for the applicability-domain Tanimoto distance), the
  honestly-reported cross-validation metric, the feature-key order the model was trained
  on, and the data provenance.

Neither file is committed (see ``.gitignore``); both are produced by ``make data-response``
(``python -m naturascreen.services.response.train``). ``xgboost`` is imported lazily inside
the functions that touch a model object, so importing this module never requires the heavy
dependency — the pipeline imports the ``response`` package unconditionally.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ...config import get_settings

MODEL_FILENAME = "response_model.ubj"
META_FILENAME = "response_meta.json"


def artifacts_dir() -> Path:
    """Default on-disk location of the model + meta (co-located with this package)."""
    return Path(__file__).resolve().parent / "artifacts"


def model_path(artifacts: Path | None = None) -> Path:
    return (artifacts or artifacts_dir()) / MODEL_FILENAME


def meta_path(artifacts: Path | None = None) -> Path:
    return (artifacts or artifacts_dir()) / META_FILENAME


@dataclass
class ResponseMeta:
    """Sidecar contract persisted next to the model weights.

    ``training_onbits`` is the list of ECFP4 on-bit index lists, one per training compound,
    used to compute the applicability-domain nearest-neighbour Tanimoto at inference time.
    ``cv_metric`` records the honest cross-validated R²/RMSE (poor values included).
    ``feature_keys`` pins the feature order so an inference-time drift is detectable.
    ``natural_product_metric`` is the same metric on a natural-product-labelled subset when
    one is identifiable — a reminder that GDSC is synthetic-drug-biased.
    """

    feature_keys: list[str]
    training_onbits: list[list[int]]
    cv_metric: dict
    source: str
    natural_product_metric: dict | None = None
    tissue_vocab: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseMeta":
        return cls(
            feature_keys=list(data["feature_keys"]),
            training_onbits=[list(bits) for bits in data["training_onbits"]],
            cv_metric=dict(data.get("cv_metric") or {}),
            source=str(data.get("source", "")),
            natural_product_metric=data.get("natural_product_metric"),
            tissue_vocab=list(data.get("tissue_vocab") or []),
            extra=dict(data.get("extra") or {}),
        )


def save(model, meta: ResponseMeta, artifacts: Path | None = None) -> None:
    """Persist the fitted XGBoost regressor (UBJSON) and its meta sidecar (JSON)."""
    target = artifacts or artifacts_dir()
    target.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path(target)))
    meta_path(target).write_text(json.dumps(meta.to_dict(), indent=2))


def load(artifacts: Path | None = None) -> tuple["object", ResponseMeta]:
    """Load the regressor + meta. Lazily imports xgboost (raises if files are absent)."""
    import xgboost as xgb

    regressor = xgb.XGBRegressor()
    regressor.load_model(str(model_path(artifacts)))
    meta = ResponseMeta.from_dict(json.loads(meta_path(artifacts).read_text()))
    return regressor, meta


def is_ready(artifacts: Path | None = None) -> bool:
    """True only when BOTH artifacts exist AND settings declare the model provisioned.

    The settings flag is the explicit operator switch (``response_model_ready``); the file
    checks guard against a half-provisioned worker. Either being false => the adapter raises
    ``AdapterUnavailable`` and the channel is honestly absent.
    """
    return (
        model_path(artifacts).exists()
        and meta_path(artifacts).exists()
        and get_settings().response_model_ready
    )
