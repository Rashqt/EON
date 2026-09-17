import unittest
import numpy as np

from engine.environment import Environment
from engine.genetics import Genome
from engine.organism import Organism
from engine import energy, reproduction, movement


def make_env(seed=1, width=20, height=20):
    return Environment(width=width, height=height, seed=seed)


def make_organism(env, rng, **overrides):
    land = np.argwhere(~env.is_water)
    y, x = land[0]
    genome = Genome.random(rng)
    defaults = dict(
        id=1, species_id=None, genome=genome, y=int(y), x=int(x), energy=50.0, health=100.0,
        age=25, generation=0, parent_id=None, birth_tick=0,
    )
    defaults.update(overrides)
    return Organism(**defaults)


class TestEnergy(unittest.TestCase):
    def test_upkeep_reduces_energy_when_no_resource(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=50.0)
        env.resource[org.y, org.x] = 0.0
        energy.apply_upkeep_and_feeding(org, env, moved_distance=0)
        self.assertLess(org.energy, 50.0)

    def test_feeding_increases_energy_when_resource_available(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=10.0)
        org.genome.energy_efficiency = 0.9
        org.genome.metabolism = 0.1
        org.genome.size = 0.1
        env.resource[org.y, org.x] = env.resource_cap[org.y, org.x] = 10.0
        energy.apply_upkeep_and_feeding(org, env, moved_distance=0)
        self.assertGreater(org.energy, 10.0)

    def test_energy_capped_at_max(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=99.9)
        env.resource[org.y, org.x] = env.resource_cap[org.y, org.x] = 100.0
        energy.apply_upkeep_and_feeding(org, env, moved_distance=0)
        self.assertLessEqual(org.energy, energy.MAX_ENERGY)


class TestReproduction(unittest.TestCase):
    def test_no_reproduction_below_maturity_age(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=100.0, age=1)
        for _ in range(50):
            child = reproduction.try_reproduce(org, rng, next_id=999, tick=1)
            self.assertIsNone(child)

    def test_no_reproduction_below_energy_threshold(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=1.0, age=100)
        child = reproduction.try_reproduce(org, rng, next_id=999, tick=1)
        self.assertIsNone(child)

    def test_reproduction_can_occur_with_high_energy_and_maturity(self):
        env = make_env()
        rng = np.random.default_rng(1)
        org = make_organism(env, rng, energy=100.0, age=100)
        org.genome.reproduction_rate = 0.9
        found_child = False
        for _ in range(500):
            org.energy = 100.0
            child = reproduction.try_reproduce(org, rng, next_id=999, tick=1)
            if child is not None:
                found_child = True
                self.assertEqual(child.parent_id, org.id)
                self.assertEqual(child.generation, org.generation + 1)
                break
        self.assertTrue(found_child, "reproduction should eventually occur given many high-energy attempts")

    def test_reproduction_costs_energy(self):
        env = make_env()
        rng = np.random.default_rng(2)
        org = make_organism(env, rng, energy=100.0, age=100)
        org.genome.reproduction_rate = 1.0
        for _ in range(500):
            before = org.energy
            org.energy = 100.0
            child = reproduction.try_reproduce(org, rng, next_id=999, tick=1)
            if child is not None:
                self.assertLess(org.energy, 100.0)
                return
        self.fail("expected a reproduction event within 500 attempts")

    def test_child_genome_may_differ_from_parent(self):
        env = make_env()
        rng = np.random.default_rng(3)
        org = make_organism(env, rng, energy=100.0, age=100)
        org.genome.reproduction_rate = 1.0
        for _ in range(500):
            org.energy = 100.0
            child = reproduction.try_reproduce(org, rng, next_id=999, tick=1)
            if child is not None:
                # Not asserting inequality strictly (mutation is probabilistic per trait),
                # just that the mechanism ran and produced a valid genome.
                self.assertIsNotNone(child.genome)
                return
        self.fail("expected a reproduction event within 500 attempts")


class TestMovement(unittest.TestCase):
    def test_move_stays_in_bounds(self):
        env = make_env(width=10, height=10)
        rng = np.random.default_rng(1)
        org = make_organism(env, rng)
        for _ in range(100):
            y, x = movement.choose_move(org, env, rng)
            self.assertTrue(env.in_bounds(y, x))
            org.y, org.x = y, x

    def test_move_never_lands_on_water(self):
        env = make_env(width=15, height=15)
        rng = np.random.default_rng(1)
        org = make_organism(env, rng)
        for _ in range(200):
            y, x = movement.choose_move(org, env, rng)
            self.assertFalse(env.is_water[y, x])
            org.y, org.x = y, x


if __name__ == "__main__":
    unittest.main()
