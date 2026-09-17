"""
Genetics: trait vectors and mutation.

Traits are plain floats in [0, 1] (a few have different natural ranges,
noted below). There is no hidden "fitness" field. Whether a trait helps
an organism is entirely a consequence of what happens to it in
environment.py, energy.py and movement.py. Nothing here privileges any
trait value over another.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, fields

TRAIT_NAMES = [
    "size",                # 0..1, affects energy upkeep and reproduction cost
    "speed",                # 0..1, movement distance per tick, costs energy
    "vision",               # 0..1, radius (in cells) an organism can sense
    "metabolism",           # 0..1, baseline energy burn rate
    "lifespan",             # 0..1, scaled to a max-age-in-ticks elsewhere
    "reproduction_rate",    # 0..1, energy threshold fraction needed to reproduce
    "temperature_tolerance",# 0..1, preferred temperature (center of comfort band)
    "energy_efficiency",    # 0..1, fraction of consumed resource converted to energy
    "mutation_tendency",    # 0..1, how much a parent's mutation step size scales
]


@dataclass
class Genome:
    size: float
    speed: float
    vision: float
    metabolism: float
    lifespan: float
    reproduction_rate: float
    temperature_tolerance: float
    energy_efficiency: float
    mutation_tendency: float

    def as_vector(self) -> np.ndarray:
        return np.array([getattr(self, name) for name in TRAIT_NAMES], dtype=np.float64)

    @classmethod
    def random(cls, rng: np.random.Generator) -> "Genome":
        values = rng.uniform(0.15, 0.85, size=len(TRAIT_NAMES))
        return cls(*values)

    def mutated(self, rng: np.random.Generator, base_mutation_std: float = 0.04) -> "Genome":
        """
        Produce a child genome. Each trait independently has a chance to
        mutate; mutation step size scales with the parent's own
        mutation_tendency trait, so mutation rate is itself heritable and
        can drift over generations rather than being a fixed constant.
        """
        vec = self.as_vector()
        step = base_mutation_std * (0.3 + 1.4 * self.mutation_tendency)
        mutate_mask = rng.random(len(vec)) < 0.5  # about half of traits drift each generation
        noise = rng.normal(0.0, step, size=len(vec))
        new_vec = vec + np.where(mutate_mask, noise, 0.0)
        new_vec = np.clip(new_vec, 0.01, 0.99)
        return Genome(*new_vec)

    def distance(self, other: "Genome") -> float:
        return float(np.linalg.norm(self.as_vector() - other.as_vector()))
