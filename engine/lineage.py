"""
Lineage: ancestry bookkeeping, built directly from parent_id / species
parent_species_id links recorded elsewhere. This module only provides
traversal helpers over that recorded data -- it invents nothing.

Deliberately decoupled from full Organism objects: register() stores a
small LineageRecord (parent_id, species_id, generation, birth_tick), not
a reference to the Organism itself. If it held the live object, every
organism ever created would stay reachable forever through this index
even after Simulation.prune_dead_history() removes it from
Simulation.organisms, which would make pruning a no-op for memory
purposes while quietly making the "irrecoverable" docstring on
prune_dead_history wrong in the other direction (nothing would actually
be lost). With only lightweight records here, pruning genuinely frees
the full per-tick organism state (traits, energy, position) while the
ancestry chain itself (who was whose parent, generation, species,
when they were born) stays queryable indefinitely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LineageRecord:
    parent_id: Optional[int]
    species_id: Optional[int]
    generation: int
    birth_tick: int


class LineageIndex:
    """A lightweight index over all organisms (living and dead) for ancestry queries."""

    def __init__(self) -> None:
        self.records: dict[int, LineageRecord] = {}
        self.children_by_parent: dict[int, list[int]] = {}

    def register(self, organism) -> None:
        self.records[organism.id] = LineageRecord(
            parent_id=organism.parent_id,
            species_id=organism.species_id,
            generation=organism.generation,
            birth_tick=organism.birth_tick,
        )
        if organism.parent_id is not None:
            self.children_by_parent.setdefault(organism.parent_id, []).append(organism.id)

    def ancestors(self, organism_id: int, max_depth: int = 50) -> list[int]:
        chain = []
        current = self.records.get(organism_id)
        depth = 0
        while current is not None and current.parent_id is not None and depth < max_depth:
            chain.append(current.parent_id)
            current = self.records.get(current.parent_id)
            depth += 1
        return chain

    def descendants(self, organism_id: int, max_count: int = 500) -> list[int]:
        result = []
        stack = list(self.children_by_parent.get(organism_id, []))
        while stack and len(result) < max_count:
            child_id = stack.pop()
            result.append(child_id)
            stack.extend(self.children_by_parent.get(child_id, []))
        return result

    def species_lineage(self, species_registry, species_id: int) -> list[int]:
        """Chain of ancestor species IDs (species-level, not organism-level)."""
        chain = []
        sp = species_registry.species.get(species_id)
        depth = 0
        while sp is not None and sp.parent_species_id is not None and depth < 100:
            chain.append(sp.parent_species_id)
            sp = species_registry.species.get(sp.parent_species_id)
            depth += 1
        return chain
