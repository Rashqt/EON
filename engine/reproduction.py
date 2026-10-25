"""
Reproduction: asexual, energy-gated, with heritable mutation.

An organism can reproduce once it has accumulated enough energy (its own
reproduction_rate trait sets the threshold, as a fraction of max energy)
and has passed a minimum maturity age. Reproduction costs energy, so it
is a real trade-off against survival, not a free action.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .energy import MAX_ENERGY
from .organism import Organism

MATURITY_AGE_TICKS = 20
REPRODUCTION_ENERGY_COST_FRACTION = 0.45


def try_reproduce(org: Organism, rng: np.random.Generator, next_id: int, tick: int) -> Optional[Organism]:
    if org.age < MATURITY_AGE_TICKS:
        return None

    threshold = MAX_ENERGY * (0.45 + org.genome.reproduction_rate * 0.4)
    if org.energy < threshold:
        return None

    # Probabilistic: even above threshold, reproduction isn't guaranteed every tick.
    if rng.random() > (0.05 + org.genome.reproduction_rate * 0.10):
        return None

    cost = MAX_ENERGY * REPRODUCTION_ENERGY_COST_FRACTION
    if org.energy - cost < 5.0:
        return None

    org.energy -= cost
    child_genome = org.genome.mutated(rng)
    child = Organism(
        id=next_id,
        species_id=org.species_id,  # species is (re)classified by the simulation after birth
        genome=child_genome,
        y=org.y,
        x=org.x,
        energy=cost * 0.6,
        health=100.0,
        age=0,
        generation=org.generation + 1,
        parent_id=org.id,
        birth_tick=tick,
    )
    org.children_count += 1
    return child
