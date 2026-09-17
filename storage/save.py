"""
Save: serialize a full Simulation to a single JSON file.

Everything needed to resume is stored: environment grids, every organism
(alive and dead, so lineage stays intact), species registry, event log,
and the sampled history used for charts. This is not a partial snapshot.
"""

from __future__ import annotations

import json

from engine.simulation import Simulation


def simulation_to_state(sim: Simulation) -> dict:
    return {
        "format_version": 1,
        "seed": sim.seed,
        "tick": sim.tick,
        "next_organism_id": sim._next_organism_id,
        "total_births": sim.total_births,
        "total_deaths": sim.total_deaths,
        "extinction_count": sim.extinction_count,
        "environment": sim.environment.to_state_dict(),
        "organisms": [o.to_state_dict() for o in sim.organisms.values()],
        "species": [
            {
                "id": sp.id,
                "founder_organism_id": sp.founder_organism_id,
                "parent_species_id": sp.parent_species_id,
                "created_tick": sp.created_tick,
                "centroid": sp.centroid.__dict__,
                "population": sp.population,
                "extinct": sp.extinct,
                "extinction_tick": sp.extinction_tick,
                "peak_population": sp.peak_population,
                "population_history": sp.population_history,
            }
            for sp in sim.species_registry.species.values()
        ],
        "next_species_id": sim.species_registry._next_species_id,
        "events": [
            {"tick": e.tick, "category": e.category, "text": e.text}
            for e in sim.event_log.entries
        ],
        "history": sim.history,
    }


def save_simulation(sim: Simulation, path: str) -> None:
    state = simulation_to_state(sim)
    with open(path, "w") as f:
        json.dump(state, f)
