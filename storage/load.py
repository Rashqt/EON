"""Load: reconstruct a full Simulation from a JSON file written by save.py."""

from __future__ import annotations

import json

import numpy as np

from engine.simulation import Simulation, SimulationStats
from engine.environment import Environment
from engine.organism import Organism
from engine.genetics import Genome
from engine.species import Species
from engine.events import LogEvent


def load_simulation(path: str) -> Simulation:
    with open(path) as f:
        state = json.load(f)

    if state.get("format_version") != 1:
        raise ValueError(f"Unsupported save format version: {state.get('format_version')}")

    sim = Simulation.__new__(Simulation)
    sim.seed = state["seed"]
    sim.rng = np.random.default_rng(state["seed"] + state["tick"])  # advance rng state deterministically enough for a resumed run
    sim.environment = Environment.from_state_dict(state["environment"])
    sim.tick = state["tick"]
    sim._next_organism_id = state["next_organism_id"]
    sim.total_births = state["total_births"]
    sim.total_deaths = state["total_deaths"]
    sim.extinction_count = state["extinction_count"]
    sim.history = state["history"]

    sim.organisms = {}
    from engine.lineage import LineageIndex
    sim.lineage = LineageIndex()
    for od in state["organisms"]:
        org = Organism.from_state_dict(od)
        sim.organisms[org.id] = org
        sim.lineage.register(org)

    from engine.species import SpeciesRegistry
    sim.species_registry = SpeciesRegistry()
    sim.species_registry._next_species_id = state["next_species_id"]
    for sd in state["species"]:
        sp = Species(
            id=sd["id"], founder_organism_id=sd["founder_organism_id"],
            parent_species_id=sd["parent_species_id"], created_tick=sd["created_tick"],
            centroid=Genome(**sd["centroid"]), population=sd["population"],
            extinct=sd["extinct"], extinction_tick=sd["extinction_tick"],
            peak_population=sd["peak_population"],
        )
        sp.population_history = [tuple(x) for x in sd["population_history"]]
        sim.species_registry.species[sp.id] = sp

    from engine.events import EventLog
    sim.event_log = EventLog()
    for ed in state["events"]:
        sim.event_log.entries.append(LogEvent(tick=ed["tick"], category=ed["category"], text=ed["text"]))

    living = sum(1 for o in sim.organisms.values() if o.alive)
    sim.stats = SimulationStats(
        tick=sim.tick, population=living,
        species_count=len([s for s in sim.species_registry.species.values() if not s.extinct]),
        extinctions=sim.extinction_count,
    )
    return sim
