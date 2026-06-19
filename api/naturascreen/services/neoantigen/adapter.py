"""Scoring adapter for the ``neoantigen`` channel — "neoantigen target match".

The neoantigen sub-score only means something when the experiment is actually
aimed at a predicted neoepitope: a presentation %rank scores *the target*, not the
small molecule. So this adapter contributes a value only when

  (a) the experiment's ``Target`` is of type ``neoantigen``, and
  (b) a stored ``Neoantigen`` row with a presentation rank matches that target
      (by peptide or tumor type against the target's identifiers).

Its raw unit is the MHCflurry presentation %rank (lower = stronger), which is what
the neoantigen scoring window expects. When there is no neoantigen target match it
raises ``AdapterUnavailable`` — the channel is simply absent for that experiment,
never fabricated.

No heavy dependencies are imported here, so the pipeline can import this module
unconditionally.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Compound, Experiment, Neoantigen, Target, TargetType
from ..subscores import AdapterUnavailable


async def score(
    session: AsyncSession, experiment: Experiment, compound: Compound
) -> float | None:
    """Presentation %rank of the experiment's matched neoantigen target.

    The value is a property of the target, so it is identical for every compound
    screened against that neoantigen (the channel reflects how presentable the
    neoepitope is, which the compound does not change).
    """
    if experiment.target_id is None:
        raise AdapterUnavailable("experiment has no target")
    # ``session.get`` returns the instance from the identity map when the pipeline
    # already eager-loaded it (selectin), so this adds no SQL in the hot path while
    # avoiding an async lazy-load on ``experiment.target``.
    target = await session.get(Target, experiment.target_id)

    if target is None or target.type != TargetType.neoantigen:
        raise AdapterUnavailable("experiment target is not a neoantigen")

    # Identifiers we can use to tie a stored prediction to this target. There is no
    # foreign key from Target to Neoantigen, so we match on the human-curated
    # strings the target carries (gene / pdb id / description) against the
    # epitope's peptide or tumor type.
    identifiers = [v for v in (target.gene, target.pdb_id, target.description) if v]
    if not identifiers:
        raise AdapterUnavailable("neoantigen target has no identifier to match")

    matched = (
        (
            await session.execute(
                select(Neoantigen)
                .where(
                    Neoantigen.presentation_rank.is_not(None),
                    or_(
                        Neoantigen.peptide.in_(identifiers),
                        Neoantigen.tumor_type.in_(identifiers),
                    ),
                )
                .order_by(Neoantigen.presentation_rank.asc())
            )
        )
        .scalars()
        .first()
    )

    if matched is None or matched.presentation_rank is None:
        raise AdapterUnavailable("no neoantigen target match for this experiment")

    return float(matched.presentation_rank)
