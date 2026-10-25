"""Extinction analysis: reads recorded species state, does not infer causes
beyond what the data supports."""

from __future__ import annotations


def extinct_species_summary(simulation) -> list[dict]:
    out = []
    for sp in simulation.species_registry.species.values():
        if sp.extinct:
            out.append({
                "species_id": sp.id,
                "created_tick": sp.created_tick,
                "extinction_tick": sp.extinction_tick,
                "lifespan_ticks": (sp.extinction_tick or 0) - sp.created_tick,
                "peak_population": sp.peak_population,
                "parent_species_id": sp.parent_species_id,
            })
    return sorted(out, key=lambda d: d["extinction_tick"] or 0)


def living_species_summary(simulation) -> list[dict]:
    out = []
    for sp in simulation.species_registry.species.values():
        if not sp.extinct:
            out.append({
                "species_id": sp.id,
                "created_tick": sp.created_tick,
                "population": sp.population,
                "peak_population": sp.peak_population,
                "parent_species_id": sp.parent_species_id,
            })
    return sorted(out, key=lambda d: -d["population"])
