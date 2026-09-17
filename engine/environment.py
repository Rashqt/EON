"""
Environment: the physical world organisms live in.

The world is a 2D grid. Each cell has real numeric properties (not cosmetic
labels): elevation, temperature, moisture, and a resource level that
organisms actually consume. Habitats (wet, dry, cold, warm, coastal...)
are not hand-placed. They fall out of the combination of these numbers.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


def _generate_noise_field(rng: np.random.Generator, width: int, height: int, octaves: int = 4) -> np.ndarray:
    """
    Value-noise field built by summing progressively finer random grids,
    each upsampled with bilinear interpolation, then smoothed. This is a
    small, dependency-free stand-in for Perlin/Simplex noise. It gives
    continuous, patchy variation instead of pure per-cell randomness, which
    is what makes coherent regions (a dry patch, a cold patch) possible.
    """
    field_ = np.zeros((height, width), dtype=np.float64)
    amplitude = 1.0
    total_amplitude = 0.0
    for octave in range(octaves):
        scale = 2 ** octave
        gh = max(2, height // (2 ** (octaves - octave)) + 1)
        gw = max(2, width // (2 ** (octaves - octave)) + 1)
        coarse = rng.random((gh, gw))
        # Upsample via simple repeat + averaging (cheap bilinear approximation)
        ys = np.linspace(0, gh - 1, height)
        xs = np.linspace(0, gw - 1, width)
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        y1 = np.clip(y0 + 1, 0, gh - 1)
        x1 = np.clip(x0 + 1, 0, gw - 1)
        fy = (ys - y0).reshape(-1, 1)
        fx = (xs - x0).reshape(1, -1)
        top = coarse[y0][:, x0] * (1 - fx) + coarse[y0][:, x1] * fx
        bot = coarse[y1][:, x0] * (1 - fx) + coarse[y1][:, x1] * fx
        layer = top * (1 - fy) + bot * fy
        field_ += layer * amplitude
        total_amplitude += amplitude
        amplitude *= 0.5
    field_ /= total_amplitude
    lo, hi = field_.min(), field_.max()
    if hi - lo > 1e-9:
        field_ = (field_ - lo) / (hi - lo)
    return field_


@dataclass
class EnvironmentEvent:
    tick: int
    kind: str
    description: str
    magnitude: float


@dataclass
class Environment:
    """
    Holds all per-cell grids. All arrays are shape (height, width).

    elevation      : 0 (deep water) .. 1 (mountain)
    is_water       : boolean mask derived from elevation
    temperature    : 0 (freezing) .. 1 (hot), latitude + elevation driven
    moisture       : 0 (arid) .. 1 (saturated)
    resource       : 0 .. resource_cap, actual consumable food/energy density
    resource_cap   : per-cell carrying capacity for resource regeneration
    """

    width: int
    height: int
    seed: int
    water_level: float = 0.35
    elevation: np.ndarray = field(init=False)
    temperature: np.ndarray = field(init=False)
    moisture: np.ndarray = field(init=False)
    resource: np.ndarray = field(init=False)
    resource_cap: np.ndarray = field(init=False)
    is_water: np.ndarray = field(init=False)
    events: list = field(default_factory=list)
    _rng: np.random.Generator = field(init=False, repr=False)
    _base_temperature: np.ndarray = field(init=False, repr=False)
    _base_resource_cap: np.ndarray = field(init=False, repr=False)
    global_temperature_shift: float = 0.0
    global_resource_shift: float = 0.0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self.elevation = _generate_noise_field(self._rng, self.width, self.height, octaves=5)
        self.is_water = self.elevation < self.water_level

        # Latitude gradient (equator warm at center row, poles cold at edges)
        rows = np.linspace(-1, 1, self.height).reshape(-1, 1)
        latitude_component = 1.0 - np.abs(rows)
        temp_noise = _generate_noise_field(self._rng, self.width, self.height, octaves=4)
        self.temperature = np.clip(0.6 * latitude_component + 0.4 * temp_noise - 0.15 * self.elevation, 0.0, 1.0)
        self._base_temperature = self.temperature.copy()

        moisture_noise = _generate_noise_field(self._rng, self.width, self.height, octaves=4)
        # Cells near water are more moist (cheap distance-to-water proxy via blur of water mask)
        water_influence = self._blur(self.is_water.astype(np.float64), passes=3)
        self.moisture = np.clip(0.5 * moisture_noise + 0.5 * water_influence, 0.0, 1.0)
        self.moisture[self.is_water] = 1.0

        fertility = self.moisture * (1.0 - np.abs(self.temperature - 0.55)) 
        fertility = np.clip(fertility, 0.05, 1.0)
        self.resource_cap = np.where(self.is_water, 0.0, fertility) * 10.0
        self._base_resource_cap = self.resource_cap.copy()
        self.resource = self.resource_cap * self._rng.uniform(0.3, 0.8, size=self.resource_cap.shape)

    @staticmethod
    def _blur(arr: np.ndarray, passes: int = 1) -> np.ndarray:
        out = arr.copy()
        for _ in range(passes):
            padded = np.pad(out, 1, mode="edge")
            out = (
                padded[0:-2, 1:-1] + padded[2:, 1:-1] +
                padded[1:-1, 0:-2] + padded[1:-1, 2:] +
                4 * padded[1:-1, 1:-1]
            ) / 8.0
        return out

    def regenerate(self, regrowth_rate: float = 0.06) -> None:
        """
        Resources regrow toward capacity each tick, approaching it
        exponentially: growth = rate * (cap - current). A pure logistic
        term (rate * R * (1 - R/K)) has R=0 as a fixed point -- a fully
        depleted cell would never recover on its own, which does not
        reflect real regrowth (seed banks, root systems, immigration from
        neighboring cells). This formula regrows even from zero.
        """
        growth = regrowth_rate * (self.resource_cap - self.resource)
        self.resource = np.clip(self.resource + growth, 0.0, self.resource_cap)

    def consume(self, y: int, x: int, amount: float) -> float:
        """Attempt to consume `amount` resource from a cell; returns actual amount taken."""
        available = self.resource[y, x]
        taken = min(available, amount)
        self.resource[y, x] -= taken
        return taken

    def apply_event(self, tick: int, rng: np.random.Generator) -> Optional[EnvironmentEvent]:
        """
        With small per-tick probability, trigger one environmental event that
        actually mutates the underlying grids (not a cosmetic log entry).
        Returns the event if one occurred, else None.
        """
        if rng.random() > 0.0015:
            return None

        kind = rng.choice([
            "warming", "cooling", "drought", "flood", "resource_collapse", "resource_boom",
        ])
        if kind == "warming":
            delta = rng.uniform(0.03, 0.10)
            self.temperature = np.clip(self.temperature + delta, 0.0, 1.0)
            desc = f"Average temperature increased by {delta * 100:.1f}%."
        elif kind == "cooling":
            delta = rng.uniform(0.03, 0.10)
            self.temperature = np.clip(self.temperature - delta, 0.0, 1.0)
            desc = f"Average temperature decreased by {delta * 100:.1f}%."
        elif kind == "drought":
            delta = rng.uniform(0.10, 0.25)
            self.resource_cap = np.clip(self.resource_cap * (1 - delta), 0.0, None)
            desc = f"Water and resource availability decreased by {delta * 100:.1f}%."
        elif kind == "flood":
            delta = rng.uniform(0.10, 0.25)
            self.moisture = np.clip(self.moisture + delta, 0.0, 1.0)
            self.resource_cap = np.clip(self.resource_cap * (1 + delta * 0.5), 0.0, self._base_resource_cap * 1.5)
            desc = f"Moisture increased by {delta * 100:.1f}% after flooding."
        elif kind == "resource_collapse":
            delta = rng.uniform(0.15, 0.35)
            self.resource_cap = np.clip(self.resource_cap * (1 - delta), 0.0, None)
            desc = f"Resource carrying capacity collapsed by {delta * 100:.1f}%."
        else:  # resource_boom
            delta = rng.uniform(0.15, 0.35)
            self.resource_cap = np.clip(self.resource_cap * (1 + delta), 0.0, self._base_resource_cap * 2.0)
            desc = f"Resource carrying capacity increased by {delta * 100:.1f}%."

        event = EnvironmentEvent(tick=tick, kind=kind, description=desc, magnitude=float(delta))
        self.events.append(event)
        return event

    def in_bounds(self, y: int, x: int) -> bool:
        return 0 <= y < self.height and 0 <= x < self.width

    def to_state_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "water_level": self.water_level,
            "elevation": self.elevation.tolist(),
            "temperature": self.temperature.tolist(),
            "moisture": self.moisture.tolist(),
            "resource": self.resource.tolist(),
            "resource_cap": self.resource_cap.tolist(),
        }

    @classmethod
    def from_state_dict(cls, state: dict) -> "Environment":
        env = cls(width=state["width"], height=state["height"], seed=state["seed"], water_level=state["water_level"])
        env.elevation = np.array(state["elevation"])
        env.temperature = np.array(state["temperature"])
        env.moisture = np.array(state["moisture"])
        env.resource = np.array(state["resource"])
        env.resource_cap = np.array(state["resource_cap"])
        env.is_water = env.elevation < env.water_level
        return env
