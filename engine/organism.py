"""
Organism: a single simulated agent.

Everything on this class is either set at birth or updated by the engine
each tick (movement.py, energy.py, reproduction.py). Nothing here is
narrated or invented after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .genetics import Genome

# Ticks-per-year-equivalent scaling for lifespan (trait 0..1 -> ticks)
MIN_LIFESPAN_TICKS = 80
MAX_LIFESPAN_TICKS = 900


@dataclass
class Organism:
    id: int
    species_id: Optional[int]
    genome: Genome
    y: int
    x: int
    energy: float
    health: float
    age: int
    generation: int
    parent_id: Optional[int]
    birth_tick: int
    death_tick: Optional[int] = None
    alive: bool = True
    children_count: int = 0
    death_cause: Optional[str] = None

    @property
    def max_lifespan_ticks(self) -> int:
        return int(MIN_LIFESPAN_TICKS + self.genome.lifespan * (MAX_LIFESPAN_TICKS - MIN_LIFESPAN_TICKS))

    @property
    def vision_radius(self) -> int:
        return max(1, int(round(1 + self.genome.vision * 4)))

    def to_state_dict(self) -> dict:
        d = {
            "id": self.id,
            "species_id": self.species_id,
            "genome": self.genome.__dict__,
            "y": self.y,
            "x": self.x,
            "energy": self.energy,
            "health": self.health,
            "age": self.age,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "birth_tick": self.birth_tick,
            "death_tick": self.death_tick,
            "alive": self.alive,
            "children_count": self.children_count,
            "death_cause": self.death_cause,
        }
        return d

    @classmethod
    def from_state_dict(cls, d: dict) -> "Organism":
        genome = Genome(**d["genome"])
        return cls(
            id=d["id"], species_id=d["species_id"], genome=genome, y=d["y"], x=d["x"],
            energy=d["energy"], health=d["health"], age=d["age"], generation=d["generation"],
            parent_id=d["parent_id"], birth_tick=d["birth_tick"], death_tick=d.get("death_tick"),
            alive=d.get("alive", True), children_count=d.get("children_count", 0),
            death_cause=d.get("death_cause"),
        )
