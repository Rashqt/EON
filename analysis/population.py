"""Population analysis: reads directly from a Simulation's recorded history."""

from __future__ import annotations


def population_series(simulation) -> tuple[list[int], list[int]]:
    """Returns (ticks, population) straight from the recorded per-tick history."""
    ticks = [h["tick"] for h in simulation.history]
    pop = [h["population"] for h in simulation.history]
    return ticks, pop


def species_series(simulation) -> tuple[list[int], list[int]]:
    ticks = [h["tick"] for h in simulation.history]
    species = [h["species_count"] for h in simulation.history]
    return ticks, species


def births_deaths_summary(simulation) -> dict:
    return {
        "total_births": simulation.total_births,
        "total_deaths": simulation.total_deaths,
        "current_population": simulation.stats.population,
        "tick": simulation.tick,
    }
