"""
Movement: organisms choose where to move based on limited local perception.

An organism does not know the whole world. It only samples cells within
its own vision_radius (derived from its vision trait) and picks among
those, weighted toward resource-rich, temperature-comfortable, non-water
cells. If nothing attractive is visible, it takes a step biased by its
speed trait with some randomness. This keeps decisions local and
trait-driven rather than omniscient.
"""

from __future__ import annotations

import numpy as np

from .environment import Environment
from .organism import Organism


def choose_move(org: Organism, env: Environment, rng: np.random.Generator) -> tuple[int, int]:
    r = org.vision_radius
    y, x = org.y, org.x
    best_score = -1e9
    best_cell = (y, x)
    candidates = []

    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            ny, nx = y + dy, x + dx
            if not env.in_bounds(ny, nx):
                continue
            if (dy * dy + dx * dx) > r * r:
                continue  # circular vision, not square
            candidates.append((ny, nx))

    if not candidates:
        return y, x

    for (ny, nx) in candidates:
        if env.is_water[ny, nx]:
            continue
        resource_score = env.resource[ny, nx]
        temp_gap = abs(env.temperature[ny, nx] - org.genome.temperature_tolerance)
        temp_score = max(0.0, 1.0 - temp_gap) * 2.0
        score = resource_score + temp_score
        if score > best_score:
            best_score = score
            best_cell = (ny, nx)

    current_cell_score = env.resource[y, x] + max(0.0, 1.0 - abs(env.temperature[y, x] - org.genome.temperature_tolerance)) * 2.0

    step_len = max(1, int(round(org.genome.speed * 2)))

    if best_score > current_cell_score + 0.05:
        # Move a bounded step toward the attractive cell rather than teleporting there.
        ny, nx = best_cell
        dy = int(np.sign(ny - y)) * min(step_len, abs(ny - y))
        dx = int(np.sign(nx - x)) * min(step_len, abs(nx - x))
        target_y, target_x = y + dy, x + dx
    else:
        # Nothing notably better visible: wander, biased by speed.
        dy = rng.integers(-step_len, step_len + 1)
        dx = rng.integers(-step_len, step_len + 1)
        target_y, target_x = y + dy, x + dx

    target_y = int(np.clip(target_y, 0, env.height - 1))
    target_x = int(np.clip(target_x, 0, env.width - 1))
    if env.is_water[target_y, target_x]:
        return y, x  # organisms in this MVP do not enter water
    return target_y, target_x
