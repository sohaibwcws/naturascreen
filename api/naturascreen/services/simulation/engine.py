"""Agent-based tumor-cell simulation engine.

WHAT IS REAL HERE: the mechanics. Each cell is an agent with a position, a state, and
stochastic division/death governed by logistic crowding. The integration, the random
walk, the carrying-capacity dynamics, and the streaming are genuine and deterministic
under a seed.

WHAT IS NOT A PREDICTION: the biological meaning. A compound's effect enters ONLY through
``heuristic_effect_transfer`` — an invented, non-validated mapping from an effectiveness
score in [0, 1] to division/death-rate multipliers. There is no validated function that
turns a binding score (kcal/mol) or a predicted IC50 into a tumor growth rate, so this
mapping is a qualitative illustration of the score, never a forecast of how a compound
affects a real tumor. The accompanying ``SIMULATION_NOTICE`` is carried on every payload
and the viewer refuses to render frames without displaying it.

The engine is pure NumPy (no DB, no Redis, no Pydantic) so it is unit-tested directly and
reused by the Celery task that streams frames.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

# Cell states (shared numeric contract with the WebGL viewer).
DIVIDING = 0
STRESSED = 1
DYING = 2

# --- HeuristicEffectTransfer (ILLUSTRATIVE; not validated) ---
# At effectiveness = 1.0 the division rate is suppressed by up to this fraction...
K_DIVISION_SUPPRESSION = 0.85
# ...and the death rate is multiplied by up to (1 + this).
K_DEATH_INDUCTION = 3.0


def heuristic_effect_transfer(effectiveness: float) -> tuple[float, float]:
    """Map an effectiveness score in [0, 1] to (division_multiplier, death_multiplier).

    ILLUSTRATIVE ONLY. This is the single, named place where a score becomes a visible
    tumor dynamic. It encodes no validated pharmacology — it exists so the animation
    *illustrates* the ranking, and its parameters are surfaced in the UI as such.
    """
    e = min(max(float(effectiveness), 0.0), 1.0)
    division_multiplier = max(0.0, 1.0 - K_DIVISION_SUPPRESSION * e)
    death_multiplier = 1.0 + K_DEATH_INDUCTION * e
    return division_multiplier, death_multiplier


@dataclass(frozen=True)
class SimConfig:
    initial_population: int = 400
    max_steps: int = 120
    dt: float = 1.0  # arbitrary simulated time units
    domain_radius: float = 42.0
    base_division_rate: float = 0.16
    base_death_rate: float = 0.02
    motility: float = 0.7
    carrying_capacity: int = 2600
    crowding_stress: float = 2.0
    max_cells: int = 6000
    seed: int = 0


@dataclass
class Frame:
    """One streamed timestep. Compact: positions are a flat xyz list for instanced rendering."""

    t: int
    time: float
    positions: list[float]
    states: list[int]
    population: int  # living cells (not counting those dying this step)
    baseline_population: int  # untreated population at the same t, for the overlay
    counts: dict[str, int] = field(default_factory=dict)


class _Population:
    """Mutable cell population backed by NumPy arrays."""

    def __init__(self, config: SimConfig, rng: np.random.Generator):
        self.config = config
        self.rng = rng
        n = config.initial_population
        # Seed a compact spheroid.
        r = config.domain_radius * 0.35 * np.cbrt(rng.random(n))
        theta = rng.uniform(0, np.pi, n)
        phi = rng.uniform(0, 2 * np.pi, n)
        self.pos = np.column_stack(
            [
                r * np.sin(theta) * np.cos(phi),
                r * np.sin(theta) * np.sin(phi),
                r * np.cos(theta),
            ]
        )
        self.state = np.full(n, DIVIDING, dtype=np.int8)

    @property
    def size(self) -> int:
        return self.pos.shape[0]

    def step(self, division_multiplier: float, death_multiplier: float) -> None:
        cfg = self.config
        # 1. Remove cells that were dying in the previous step (they are now dead/gone).
        if self.size:
            keep = self.state != DYING
            self.pos = self.pos[keep]
            self.state = self.state[keep]
        n = self.size
        if n == 0:
            return

        # 2. Random-walk motion, clamped into the spherical domain.
        self.pos = self.pos + self.rng.normal(0.0, cfg.motility, size=(n, 3))
        dist = np.linalg.norm(self.pos, axis=1)
        outside = dist > cfg.domain_radius
        if outside.any():
            self.pos[outside] *= (cfg.domain_radius / dist[outside])[:, None]

        # 3. Crowding-dependent effective rates.
        crowding = n / cfg.carrying_capacity
        div_rate = cfg.base_division_rate * division_multiplier * max(0.0, 1.0 - crowding)
        death_rate = cfg.base_death_rate * death_multiplier * (
            1.0 + cfg.crowding_stress * max(0.0, crowding - 0.6)
        )

        # 4. Deaths: flag as DYING (rendered one frame, removed next step).
        new_dying = self.rng.random(n) < min(1.0, death_rate * cfg.dt)
        self.state = np.where(new_dying, DYING, DIVIDING).astype(np.int8)

        # 5. Stress: living cells under crowding read as stressed.
        if crowding > 0.7:
            stressed = (~new_dying) & (self.rng.random(n) < (crowding - 0.7))
            self.state[stressed] = STRESSED

        # 6. Divisions among the living: spawn daughters near parents (capacity-capped).
        can_divide = (~new_dying) & (self.rng.random(n) < min(1.0, div_rate * cfg.dt))
        room = cfg.max_cells - n
        idx = np.flatnonzero(can_divide)
        if room > 0 and idx.size:
            if idx.size > room:
                idx = idx[:room]
            daughters = self.pos[idx] + self.rng.normal(0.0, 1.2, size=(idx.size, 3))
            self.pos = np.vstack([self.pos, daughters])
            self.state = np.concatenate(
                [self.state, np.full(idx.size, DIVIDING, dtype=np.int8)]
            )

    def living_count(self) -> int:
        return int(np.count_nonzero(self.state != DYING))

    def state_counts(self) -> dict[str, int]:
        return {
            "dividing": int(np.count_nonzero(self.state == DIVIDING)),
            "stressed": int(np.count_nonzero(self.state == STRESSED)),
            "dying": int(np.count_nonzero(self.state == DYING)),
        }


def _baseline_populations(config: SimConfig) -> list[int]:
    """Run an untreated (effectiveness=0) pass, returning living count per timestep."""
    rng = np.random.default_rng(config.seed)
    pop = _Population(config, rng)
    div_m, death_m = heuristic_effect_transfer(0.0)
    counts: list[int] = []
    for _ in range(config.max_steps):
        pop.step(div_m, death_m)
        counts.append(pop.living_count())
        if pop.size == 0:
            break
    # Pad to max_steps so treated frames always have a baseline value to pair with.
    while len(counts) < config.max_steps:
        counts.append(counts[-1] if counts else 0)
    return counts


def simulate(config: SimConfig, effectiveness: float) -> Iterator[Frame]:
    """Yield frames for the treated run, each carrying the untreated baseline population."""
    baseline = _baseline_populations(config)
    rng = np.random.default_rng(config.seed)
    pop = _Population(config, rng)
    div_m, death_m = heuristic_effect_transfer(effectiveness)
    for t in range(config.max_steps):
        pop.step(div_m, death_m)
        yield Frame(
            t=t,
            time=round(t * config.dt, 3),
            positions=pop.pos.astype(float).round(2).ravel().tolist(),
            states=pop.state.astype(int).tolist(),
            population=pop.living_count(),
            baseline_population=baseline[t],
            counts=pop.state_counts(),
        )
        if pop.size == 0:
            break
