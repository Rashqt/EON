"""
Species: trait-similarity clusters, not random labels.

Each species records a centroid genome (the running average trait vector
of its living members) and a genetic-distance threshold. An organism
belongs to a species if its genome is within SPECIES_DISTANCE_THRESHOLD
of that species' centroid. When a newborn's genome is not close enough to
its parent's species (drift past the threshold), it founds a new species,
recorded with its parent species as ancestor -- this is how species
splitting happens, driven by accumulated mutation, not scripted events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .genetics import Genome, TRAIT_NAMES

SPECIES_DISTANCE_THRESHOLD = 0.35


@dataclass
class Species:
    id: int
    founder_organism_id: int
    parent_species_id: Optional[int]
    created_tick: int
    centroid: Genome
    # Fixed at founding: the founder's own genome. Classification of new
    # members compares against this fixed anchor rather than the
    # constantly-recomputed live centroid. A live centroid tracks whoever
    # is currently alive, so comparing each newborn to it would make
    # cumulative multi-generation drift invisible -- the reference point
    # would always relax to wherever the population already is. Comparing
    # to a fixed founding genome lets real, accumulated divergence surface.
    reference_genome: Genome = None
    population: int = 0
    extinct: bool = False
    extinction_tick: Optional[int] = None
    peak_population: int = 0
    population_history: list = field(default_factory=list)  # (tick, population)

    def record_population(self, tick: int, population: int) -> None:
        self.population = population
        self.peak_population = max(self.peak_population, population)
        self.population_history.append((tick, population))


class SpeciesRegistry:
    def __init__(self) -> None:
        self.species: dict[int, Species] = {}
        self._next_species_id = 1

    def create_species(self, founder_organism_id: int, parent_species_id: Optional[int],
                        centroid: Genome, tick: int) -> Species:
        sp = Species(
            id=self._next_species_id,
            founder_organism_id=founder_organism_id,
            parent_species_id=parent_species_id,
            created_tick=tick,
            centroid=centroid,
            reference_genome=centroid,
        )
        self.species[sp.id] = sp
        self._next_species_id += 1
        return sp

    def classify(self, organism, parent_species_id: Optional[int], tick: int) -> int:
        """
        Assign (or create) a species for a newborn organism. If it has a
        parent species and remains within the distance threshold of that
        species' centroid, it stays in that species. Otherwise a new
        species is founded with the parent species recorded as ancestor.
        """
        if parent_species_id is not None and parent_species_id in self.species:
            parent_sp = self.species[parent_species_id]
            if not parent_sp.extinct and organism.genome.distance(parent_sp.reference_genome) < SPECIES_DISTANCE_THRESHOLD:
                return parent_species_id
            new_sp = self.create_species(organism.id, parent_species_id, organism.genome, tick)
            return new_sp.id

        new_sp = self.create_species(organism.id, None, organism.genome, tick)
        return new_sp.id

    def update_centroids_and_extinctions(self, organisms: list, tick: int) -> list[Species]:
        """
        Recompute each species' centroid from its currently living members
        and mark newly-zero-population species as extinct. Returns species
        that went extinct this call.
        """
        by_species: dict[int, list] = {}
        for org in organisms:
            if org.alive and org.species_id is not None:
                by_species.setdefault(org.species_id, []).append(org)

        newly_extinct = []
        for sp_id, sp in self.species.items():
            members = by_species.get(sp_id, [])
            if members:
                vecs = np.array([m.genome.as_vector() for m in members])
                mean_vec = vecs.mean(axis=0)
                sp.centroid = Genome(*mean_vec)
                sp.record_population(tick, len(members))
            else:
                if not sp.extinct and sp.population_history:
                    sp.extinct = True
                    sp.extinction_tick = tick
                    sp.record_population(tick, 0)
                    newly_extinct.append(sp)
        return newly_extinct
