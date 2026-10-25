"""Evolution analysis: trait averages over time, read from recorded history."""

from __future__ import annotations

from engine.genetics import TRAIT_NAMES


def trait_series(simulation, trait_name: str) -> tuple[list[int], list[float]]:
    if trait_name not in TRAIT_NAMES:
        raise ValueError(f"Unknown trait: {trait_name}")
    ticks, values = [], []
    for h in simulation.history:
        key = f"avg_{trait_name}"
        if key in h:
            ticks.append(h["tick"])
            values.append(h[key])
    return ticks, values


def all_trait_series(simulation) -> dict[str, tuple[list[int], list[float]]]:
    return {name: trait_series(simulation, name) for name in TRAIT_NAMES}


def trait_shift_summary(simulation) -> dict[str, tuple[float, float]]:
    """For each trait, (value at first recorded tick, value at latest recorded tick)."""
    out = {}
    if not simulation.history:
        return out
    first, last = simulation.history[0], simulation.history[-1]
    for name in TRAIT_NAMES:
        key = f"avg_{name}"
        if key in first and key in last:
            out[name] = (first[key], last[key])
    return out
