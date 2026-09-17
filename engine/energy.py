"""
Energy: the actual survival currency.

Every organism's energy is a real float that goes up (consuming resource,
converted at energy_efficiency) and down (metabolism upkeep + movement
cost + a temperature-mismatch penalty). If it drops to or below zero the
organism dies of starvation. Nothing about survival is decided outside
this arithmetic.
"""

from __future__ import annotations

from .environment import Environment
from .organism import Organism

MAX_ENERGY = 100.0
BASE_UPKEEP = 0.15
MOVE_COST_PER_STEP = 0.06


def apply_upkeep_and_feeding(org: Organism, env: Environment, moved_distance: float) -> None:
    upkeep = BASE_UPKEEP * (0.5 + org.genome.metabolism) * (0.6 + org.genome.size)
    move_cost = MOVE_COST_PER_STEP * moved_distance * (0.5 + org.genome.size)

    temp_gap = abs(env.temperature[org.y, org.x] - org.genome.temperature_tolerance)
    temp_penalty = 0.0
    if temp_gap > 0.35:
        temp_penalty = (temp_gap - 0.35) * 0.6

    org.energy -= upkeep + move_cost + temp_penalty

    desired_intake = 1.2 + org.genome.size * 1.5
    taken = env.consume(org.y, org.x, desired_intake)
    org.energy += taken * org.genome.energy_efficiency
    org.energy = min(org.energy, MAX_ENERGY)
