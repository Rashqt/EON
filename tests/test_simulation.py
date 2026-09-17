import os
import tempfile
import unittest

from engine.simulation import Simulation
from storage.save import save_simulation
from storage.load import load_simulation


class TestWorldCreation(unittest.TestCase):
    def test_world_created_with_requested_population(self):
        sim = Simulation(width=30, height=20, seed=1, initial_population=50)
        self.assertEqual(sim.stats.population, 0)  # stats only updates after a step()
        self.assertEqual(len(sim.organisms), 50)

    def test_world_never_exceeds_available_land_when_seeding(self):
        # Tiny world: fewer land cells than requested population is plausible;
        # seeding should not crash, and should not exceed available land cells.
        sim = Simulation(width=5, height=5, seed=1, initial_population=10000)
        land_cells = (~sim.environment.is_water).sum()
        self.assertLessEqual(len(sim.organisms), land_cells)


class TestOrganismCreationAndMovement(unittest.TestCase):
    def test_organisms_move_over_time(self):
        sim = Simulation(width=40, height=30, seed=2, initial_population=100)
        positions_before = {oid: (o.y, o.x) for oid, o in sim.organisms.items()}
        for _ in range(10):
            sim.step()
        moved = 0
        for oid, org in sim.organisms.items():
            if oid in positions_before and org.alive:
                if (org.y, org.x) != positions_before[oid]:
                    moved += 1
        self.assertGreater(moved, 0, "at least some organisms should have moved after 10 ticks")


class TestEnergyConsumption(unittest.TestCase):
    def test_energy_changes_over_time(self):
        sim = Simulation(width=40, height=30, seed=3, initial_population=100)
        start_energy = {oid: o.energy for oid, o in sim.organisms.items()}
        for _ in range(5):
            sim.step()
        changed = 0
        for oid, org in sim.organisms.items():
            if oid in start_energy and org.alive and org.energy != start_energy[oid]:
                changed += 1
        self.assertGreater(changed, 0)


class TestReproductionAndMutation(unittest.TestCase):
    def test_births_occur_over_a_long_run(self):
        sim = Simulation(width=50, height=35, seed=4, initial_population=150)
        for _ in range(600):
            sim.step()
        self.assertGreater(sim.total_births, 0)

    def test_generations_advance(self):
        sim = Simulation(width=50, height=35, seed=4, initial_population=150)
        for _ in range(600):
            sim.step()
        max_generation = max((o.generation for o in sim.organisms.values()), default=0)
        self.assertGreater(max_generation, 0)


class TestDeath(unittest.TestCase):
    def test_deaths_occur_over_a_long_run(self):
        sim = Simulation(width=50, height=35, seed=5, initial_population=150)
        for _ in range(600):
            sim.step()
        self.assertGreater(sim.total_deaths, 0)

    def test_dead_organisms_have_death_metadata(self):
        sim = Simulation(width=50, height=35, seed=5, initial_population=150)
        for _ in range(600):
            sim.step()
        dead = [o for o in sim.organisms.values() if not o.alive]
        self.assertGreater(len(dead), 0)
        for o in dead[:20]:
            self.assertIsNotNone(o.death_tick)
            self.assertIsNotNone(o.death_cause)


class TestSpeciesTrackingAndExtinction(unittest.TestCase):
    def test_species_registered_for_every_founder(self):
        sim = Simulation(width=30, height=20, seed=6, initial_population=40)
        self.assertEqual(len(sim.species_registry.species), 40)

    def test_extinction_detected_when_population_reaches_zero(self):
        sim = Simulation(width=30, height=20, seed=6, initial_population=40)
        for _ in range(1500):
            sim.step()
        self.assertGreater(sim.extinction_count, 0)
        extinct = [s for s in sim.species_registry.species.values() if s.extinct]
        self.assertEqual(len(extinct), sim.extinction_count)
        for sp in extinct:
            self.assertEqual(sp.population, 0)
            self.assertIsNotNone(sp.extinction_tick)

    def test_species_splitting_can_occur(self):
        sim = Simulation(width=70, height=45, seed=42, initial_population=220)
        for _ in range(2500):
            sim.step()
        split_species = [s for s in sim.species_registry.species.values() if s.created_tick > 0]
        self.assertGreater(len(split_species), 0, "expected at least one species to emerge via divergence")
        for sp in split_species:
            self.assertIsNotNone(sp.parent_species_id)


class TestPopulationCalculations(unittest.TestCase):
    def test_population_matches_count_of_alive_organisms(self):
        sim = Simulation(width=40, height=30, seed=7, initial_population=100)
        for _ in range(200):
            sim.step()
        actual_alive = sum(1 for o in sim.organisms.values() if o.alive)
        self.assertEqual(sim.stats.population, actual_alive)

    def test_species_count_matches_non_extinct_species(self):
        sim = Simulation(width=40, height=30, seed=7, initial_population=100)
        for _ in range(200):
            sim.step()
        actual = len([s for s in sim.species_registry.species.values() if not s.extinct])
        self.assertEqual(sim.stats.species_count, actual)


class TestEnvironmentalChanges(unittest.TestCase):
    def test_environmental_events_can_mutate_grids(self):
        sim = Simulation(width=40, height=30, seed=8, initial_population=50)
        before = sim.environment.resource_cap.copy()
        changed = False
        for _ in range(3000):
            sim.step()
            if not (sim.environment.resource_cap == before).all():
                changed = True
                break
        self.assertTrue(changed, "expected at least one environmental event to alter the grid within 3000 ticks")


class TestSaveLoad(unittest.TestCase):
    def test_save_and_load_round_trip_preserves_state(self):
        sim = Simulation(width=30, height=20, seed=9, initial_population=60)
        for _ in range(100):
            sim.step()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "world.json")
            save_simulation(sim, path)
            loaded = load_simulation(path)
        self.assertEqual(loaded.tick, sim.tick)
        self.assertEqual(loaded.stats.population, sim.stats.population)
        self.assertEqual(len(loaded.organisms), len(sim.organisms))
        self.assertEqual(len(loaded.species_registry.species), len(sim.species_registry.species))

    def test_loaded_simulation_can_continue_running(self):
        sim = Simulation(width=30, height=20, seed=9, initial_population=60)
        for _ in range(50):
            sim.step()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "world.json")
            save_simulation(sim, path)
            loaded = load_simulation(path)
        loaded.step()
        self.assertEqual(loaded.tick, sim.tick + 1)

    def test_load_rejects_unsupported_format_version(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            import json
            with open(path, "w") as f:
                json.dump({"format_version": 999}, f)
            with self.assertRaises(ValueError):
                load_simulation(path)


class TestDeterminism(unittest.TestCase):
    def test_same_seed_produces_same_initial_world(self):
        sim1 = Simulation(width=40, height=30, seed=123, initial_population=80)
        sim2 = Simulation(width=40, height=30, seed=123, initial_population=80)
        self.assertEqual(
            [o.genome.as_vector().tolist() for o in sim1.organisms.values()],
            [o.genome.as_vector().tolist() for o in sim2.organisms.values()],
        )

    def test_different_seeds_produce_different_worlds(self):
        sim1 = Simulation(width=40, height=30, seed=1, initial_population=80)
        sim2 = Simulation(width=40, height=30, seed=2, initial_population=80)
        self.assertFalse(
            (sim1.environment.elevation == sim2.environment.elevation).all()
        )


class TestInvalidStates(unittest.TestCase):
    def test_inspecting_nonexistent_organism_returns_none(self):
        sim = Simulation(width=20, height=20, seed=1, initial_population=10)
        self.assertIsNone(sim.get_organism(999999))

    def test_simulation_survives_total_extinction_without_crashing(self):
        # Extreme, tiny, resource-starved world to force extinction quickly,
        # then confirm stepping an empty world doesn't raise.
        sim = Simulation(width=6, height=6, seed=1, initial_population=5)
        for _ in range(3000):
            sim.step()
        # Whatever the population is, stepping further must not crash.
        for _ in range(20):
            sim.step()
        self.assertGreaterEqual(sim.stats.population, 0)

    def test_zero_initial_population_does_not_crash(self):
        sim = Simulation(width=20, height=20, seed=1, initial_population=0)
        for _ in range(10):
            sim.step()
        self.assertEqual(sim.stats.population, 0)


if __name__ == "__main__":
    unittest.main()
