"""
Behavior analysis.

The spec for EON lists many possible future emergent behaviors (hunting,
territoriality, communication, and so on). None of those are implemented
in this MVP, and this module does not claim they occur. The one thing it
does measure, from actual positions, is spatial clustering: whether
members of the same species tend to sit closer to each other than a
uniform random scattering would produce. That is a real, computable
signal from current organism positions, nothing more.
"""

from __future__ import annotations

import math
from collections import defaultdict


def species_clustering_score(simulation) -> dict[int, float]:
    """
    For each living species with at least 3 members, returns the average
    pairwise distance between its members divided by the average pairwise
    distance of the same number of randomly-placed points on the same
    world. A score below 1.0 means members of that species are, on
    average, positioned closer together than chance would predict
    (a measurable clustering signal). A score near 1.0 means no
    detectable clustering. This is computed directly from organism
    positions each time it is called; it is not cached or guessed.
    """
    by_species: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for org in simulation.organisms.values():
        if org.alive:
            by_species[org.species_id].append((org.y, org.x))

    width, height = simulation.environment.width, simulation.environment.height
    # Expected average pairwise distance for uniform random points on a
    # width x height rectangle, approximated analytically.
    expected_random_distance = 0.5214 * math.sqrt(width * width + height * height)

    scores = {}
    for species_id, positions in by_species.items():
        if len(positions) < 3:
            continue
        total = 0.0
        count = 0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dy = positions[i][0] - positions[j][0]
                dx = positions[i][1] - positions[j][1]
                total += math.hypot(dy, dx)
                count += 1
        if count == 0:
            continue
        avg_distance = total / count
        scores[species_id] = avg_distance / expected_random_distance if expected_random_distance > 0 else 1.0
    return scores
