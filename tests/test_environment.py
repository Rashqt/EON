import unittest
import numpy as np

from engine.environment import Environment


class TestEnvironment(unittest.TestCase):
    def test_world_has_land_and_water(self):
        env = Environment(width=60, height=40, seed=1)
        self.assertTrue(env.is_water.any(), "world should contain some water")
        self.assertTrue((~env.is_water).any(), "world should contain some land")

    def test_deterministic_with_same_seed(self):
        env1 = Environment(width=40, height=30, seed=99)
        env2 = Environment(width=40, height=30, seed=99)
        self.assertTrue(np.array_equal(env1.elevation, env2.elevation))
        self.assertTrue(np.array_equal(env1.resource, env2.resource))

    def test_different_seeds_differ(self):
        env1 = Environment(width=40, height=30, seed=1)
        env2 = Environment(width=40, height=30, seed=2)
        self.assertFalse(np.array_equal(env1.elevation, env2.elevation))

    def test_resource_never_exceeds_capacity(self):
        env = Environment(width=40, height=30, seed=3)
        self.assertTrue((env.resource <= env.resource_cap + 1e-9).all())

    def test_water_cells_have_zero_resource_capacity(self):
        env = Environment(width=40, height=30, seed=3)
        self.assertTrue((env.resource_cap[env.is_water] == 0).all())

    def test_regenerate_recovers_from_full_depletion(self):
        """Regression test for the fixed regrowth bug: a fully depleted cell
        (resource == 0) must still be able to regrow. A pure logistic
        R*(1-R/K) term has R=0 as a fixed point and would never recover."""
        env = Environment(width=10, height=10, seed=5)
        land = np.argwhere(~env.is_water)
        self.assertTrue(len(land) > 0)
        y, x = land[0]
        env.resource[y, x] = 0.0
        for _ in range(50):
            env.regenerate()
        self.assertGreater(env.resource[y, x], 0.0)

    def test_consume_does_not_go_negative(self):
        env = Environment(width=20, height=20, seed=6)
        land = np.argwhere(~env.is_water)
        y, x = land[0]
        env.resource[y, x] = 1.0
        taken = env.consume(int(y), int(x), 5.0)
        self.assertLessEqual(taken, 1.0)
        self.assertGreaterEqual(env.resource[y, x], 0.0)

    def test_in_bounds(self):
        env = Environment(width=10, height=10, seed=1)
        self.assertTrue(env.in_bounds(0, 0))
        self.assertTrue(env.in_bounds(9, 9))
        self.assertFalse(env.in_bounds(-1, 0))
        self.assertFalse(env.in_bounds(0, 10))

    def test_save_and_restore_state_dict(self):
        env = Environment(width=15, height=12, seed=7)
        state = env.to_state_dict()
        env2 = Environment.from_state_dict(state)
        self.assertTrue(np.array_equal(env.elevation, env2.elevation))
        self.assertTrue(np.array_equal(env.resource, env2.resource))


if __name__ == "__main__":
    unittest.main()
