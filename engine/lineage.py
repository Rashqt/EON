"""
Lineage: ancestry bookkeeping, built directly from parent_id / species
parent_species_id links recorded elsewhere. This module only provides
traversal helpers over that recorded data -- it invents nothing.
"""

from __future__ import annotations

from typing import Optional


class LineageIndex:
    """A lightweight index over all organisms (living and dead) for ancestry queries."""

    def __init__(self) -> None:
        self.organisms_by_id: dict[int, object] = {}
        self.children_by_parent: dict[int, list[int]] = {}

    def register(self, organism) -> None:
        self.organisms_by_id[organism.id] = organism
        if organism.parent_id is not None:
            self.children_by_parent.setdefault(organism.parent_id, []).append(organism.id)

    def ancestors(self, organism_id: int, max_depth: int = 50) -> list[int]:
        chain = []
        current = self.organisms_by_id.get(organism_id)
        depth = 0
        while current is not None and current.parent_id is not None and depth < max_depth:
            chain.append(current.parent_id)
            current = self.organisms_by_id.get(current.parent_id)
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
