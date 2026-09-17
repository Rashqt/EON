import unittest
import numpy as np

from engine.genetics import Genome, TRAIT_NAMES


class TestGenetics(unittest.TestCase):
    def test_random_genome_in_bounds(self):
        rng = np.random.default_rng(1)
        g = Genome.random(rng)
        for name in TRAIT_NAMES:
            v = getattr(g, name)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_mutation_stays_in_bounds(self):
        rng = np.random.default_rng(2)
        g = Genome.random(rng)
        for _ in range(200):
            g = g.mutated(rng, base_mutation_std=0.5)
            for name in TRAIT_NAMES:
                v = getattr(g, name)
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_mutation_changes_genome_probabilistically(self):
        rng = np.random.default_rng(3)
        g = Genome.random(rng)
        children = [g.mutated(rng) for _ in range(20)]
        distances = [g.distance(c) for c in children]
        self.assertTrue(any(d > 0 for d in distances), "at least some mutations should change the genome")

    def test_distance_zero_for_identical_genome(self):
        rng = np.random.default_rng(4)
        g = Genome.random(rng)
        self.assertEqual(g.distance(g), 0.0)

    def test_distance_symmetric(self):
        rng = np.random.default_rng(5)
        g1 = Genome.random(rng)
        g2 = Genome.random(rng)
        self.assertAlmostEqual(g1.distance(g2), g2.distance(g1), places=9)

    def test_deterministic_mutation_with_same_rng_state(self):
        g = Genome.random(np.random.default_rng(10))
        rng_a = np.random.default_rng(50)
        rng_b = np.random.default_rng(50)
        child_a = g.mutated(rng_a)
        child_b = g.mutated(rng_b)
        self.assertEqual(child_a.as_vector().tolist(), child_b.as_vector().tolist())


if __name__ == "__main__":
    unittest.main()
