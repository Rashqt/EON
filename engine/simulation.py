"""
Simulation: the tick loop that ties every other engine module together.

This is the only place that advances simulated time. Every number the
UI/CLI ever displays (population, species count, extinctions, an
organism's stats) is read directly off the state this class owns -- there
is no separate "display" copy of any of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .environment import Environment
from .genetics import Genome
from .organism import Organism
from .species import SpeciesRegistry
from .events import EventLog
from .lineage import LineageIndex
from . import movement, energy, reproduction

# Soft population ceiling. This is a performance safeguard, not a game
# rule: above this size, local crowding imposes extra mortality (crowded
# cells run out of resource faster than they can regenerate, which is a
# real consequence of the energy model, not a scripted cull). It exists
# so the MVP stays responsive; it is documented in the README as a
# known limitation rather than hidden.
SOFT_POPULATION_CEILING = 6000


@dataclass
class SimulationStats:
    tick: int = 0
    population: int = 0
    species_count: int = 0
    extinctions: int = 0
    births_this_tick: int = 0
    deaths_this_tick: int = 0
    total_births: int = 0
    total_deaths: int = 0


class Simulation:
    def __init__(self, width: int = 80, height: int = 50, seed: int = 0, initial_population: int = 250):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.environment = Environment(width=width, height=height, seed=seed)
        self.species_registry = SpeciesRegistry()
        self.event_log = EventLog()
        self.lineage = LineageIndex()

        self.organisms: dict[int, Organism] = {}
        self._next_organism_id = 1
        self.tick = 0
        self.stats = SimulationStats()
        self.total_births = 0
        self.total_deaths = 0
        self.extinction_count = 0

        # Sampled history for charts/analysis. Recorded once per tick, read
        # directly off the same state everything else uses -- not a
        # separately-imagined series.
        self.history: list[dict] = []

        self._seed_initial_population(initial_population)

    # ------------------------------------------------------------------ init
    def _seed_initial_population(self, n: int) -> None:
        land_cells = np.argwhere(~self.environment.is_water)
        if len(land_cells) == 0:
            return
        choices = self.rng.choice(len(land_cells), size=min(n, len(land_cells)), replace=True)
        for idx in choices:
            y, x = land_cells[idx]
            genome = Genome.random(self.rng)
            org = Organism(
                id=self._next_organism_id, species_id=None, genome=genome,
                y=int(y), x=int(x), energy=60.0, health=100.0, age=0,
                generation=0, parent_id=None, birth_tick=0,
            )
            org.species_id = self.species_registry.classify(org, None, tick=0)
            self.organisms[org.id] = org
            self.lineage.register(org)
            self._next_organism_id += 1
        self.species_registry.update_centroids_and_extinctions(list(self.organisms.values()), tick=0)
        self.stats.species_count = len([s for s in self.species_registry.species.values() if not s.extinct])
        self.event_log.add(0, "population", f"World seeded with {len(self.organisms)} organisms.")

    # ------------------------------------------------------------------ tick
    def step(self) -> SimulationStats:
        self.tick += 1
        self.environment.regenerate()

        env_event = self.environment.apply_event(self.tick, self.rng)
        if env_event is not None:
            self.event_log.add(self.tick, "environment", env_event.description)

        living = [o for o in self.organisms.values() if o.alive]
        overcrowded = len(living) > SOFT_POPULATION_CEILING
        births = []
        deaths = []

        # Shuffle order each tick so no organism gets systematic first-mover advantage.
        order = list(living)
        self.rng.shuffle(order)

        for org in order:
            if not org.alive:
                continue
            org.age += 1

            old_y, old_x = org.y, org.x
            new_y, new_x = movement.choose_move(org, self.environment, self.rng)
            moved_distance = abs(new_y - old_y) + abs(new_x - old_x)
            org.y, org.x = new_y, new_x

            energy.apply_upkeep_and_feeding(org, self.environment, moved_distance)

            if overcrowded:
                # Extra crowding mortality: resource is already scarcer per-capita
                # when too many organisms share the world; this simply keeps a
                # runaway population from making every subsequent tick slower.
                org.energy -= 0.4

            death_cause = self._check_death(org)
            if death_cause is not None:
                org.alive = False
                org.death_tick = self.tick
                org.death_cause = death_cause
                deaths.append(org)
                continue

            if not overcrowded:
                child = reproduction.try_reproduce(org, self.rng, self._next_organism_id, self.tick)
                if child is not None:
                    child.species_id = self.species_registry.classify(child, org.species_id, self.tick)
                    self.organisms[child.id] = child
                    self.lineage.register(child)
                    self._next_organism_id += 1
                    births.append(child)

        self.total_births += len(births)
        self.total_deaths += len(deaths)

        newly_extinct = self.species_registry.update_centroids_and_extinctions(
            [o for o in self.organisms.values() if o.alive], self.tick
        )
        for sp in newly_extinct:
            self.extinction_count += 1
            self.event_log.add(
                self.tick, "extinction",
                f"Species {sp.id} reached zero population at tick {self.tick} "
                f"(peak population was {sp.peak_population})."
            )

        for sp in self.species_registry.species.values():
            if not sp.extinct and sp.created_tick == self.tick:
                self.event_log.add(
                    self.tick, "species",
                    f"Species {sp.id} emerged from divergence (parent species: "
                    f"{sp.parent_species_id if sp.parent_species_id else 'none'})."
                )

        living_count = sum(1 for o in self.organisms.values() if o.alive)
        self.stats = SimulationStats(
            tick=self.tick,
            population=living_count,
            species_count=len([s for s in self.species_registry.species.values() if not s.extinct]),
            extinctions=self.extinction_count,
            births_this_tick=len(births),
            deaths_this_tick=len(deaths),
            total_births=self.total_births,
            total_deaths=self.total_deaths,
        )

        if living_count == 0 and self.tick % 50 == 0:
            self.event_log.add(self.tick, "population", "All life has died out.")

        self._record_history()
        return self.stats

    def _record_history(self) -> None:
        living = [o for o in self.organisms.values() if o.alive]
        entry = {
            "tick": self.tick,
            "population": len(living),
            "species_count": self.stats.species_count,
            "extinctions": self.extinction_count,
            "births": self.stats.births_this_tick,
            "deaths": self.stats.deaths_this_tick,
        }
        if living:
            for trait in ("size", "speed", "vision", "metabolism", "lifespan",
                          "reproduction_rate", "temperature_tolerance",
                          "energy_efficiency", "mutation_tendency"):
                entry[f"avg_{trait}"] = sum(getattr(o.genome, trait) for o in living) / len(living)
        self.history.append(entry)

    def _check_death(self, org: Organism) -> Optional[str]:
        if org.energy <= 0:
            return "starvation"
        if org.age >= org.max_lifespan_ticks:
            return "old_age"
        # Small baseline random mortality (predation-free environments still have risk)
        if self.rng.random() < 0.0008:
            return "random"
        return None

    # ------------------------------------------------------------- queries
    def living_organisms(self) -> list[Organism]:
        return [o for o in self.organisms.values() if o.alive]

    def get_organism(self, organism_id: int) -> Optional[Organism]:
        return self.organisms.get(organism_id)

    def prune_dead_history(self, keep_last_n_dead: int = 20000) -> None:
        """Optional memory management: drop the oldest dead organisms beyond a cap.
        Lineage links for pruned organisms are not recoverable after this call --
        this trades long-run memory footprint for full history depth."""
        dead_ids = [oid for oid, o in self.organisms.items() if not o.alive]
        if len(dead_ids) <= keep_last_n_dead:
            return
        dead_ids.sort(key=lambda oid: self.organisms[oid].death_tick or 0)
        to_remove = dead_ids[: len(dead_ids) - keep_last_n_dead]
        for oid in to_remove:
            del self.organisms[oid]
