import unittest
import numpy as np

from engine.genetics import Genome
from engine.organism import Organism, MIN_LIFESPAN_TICKS, MAX_LIFESPAN_TICKS


class TestOrganism(unittest.TestCase):
    def _make(self, **overrides):
        rng = np.random.default_rng(1)
        genome = Genome.random(rng)
        defaults = dict(
            id=1, species_id=None, genome=genome, y=0, x=0, energy=50.0, health=100.0,
            age=0, generation=0, parent_id=None, birth_tick=0,
        )
        defaults.update(overrides)
        return Organism(**defaults)

    def test_max_lifespan_in_expected_range(self):
        org = self._make()
        self.assertGreaterEqual(org.max_lifespan_ticks, MIN_LIFESPAN_TICKS)
        self.assertLessEqual(org.max_lifespan_ticks, MAX_LIFESPAN_TICKS)

    def test_vision_radius_at_least_one(self):
        org = self._make()
        org.genome.vision = 0.0
        self.assertGreaterEqual(org.vision_radius, 1)

    def test_round_trip_state_dict(self):
        org = self._make(id=42, generation=3, parent_id=7)
        state = org.to_state_dict()
        restored = Organism.from_state_dict(state)
        self.assertEqual(restored.id, 42)
        self.assertEqual(restored.generation, 3)
        self.assertEqual(restored.parent_id, 7)
        self.assertEqual(restored.genome.as_vector().tolist(), org.genome.as_vector().tolist())


if __name__ == "__main__":
    unittest.main()
