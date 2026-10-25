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

    def test_loaded_species_preserve_reference_genome(self):
        """
        Regression test: storage/save.py originally omitted
        Species.reference_genome entirely (it was added to the Species
        dataclass after save.py was written), so every loaded world
        crashed the moment it tried to classify a new organism against a
        species' reference_genome, since it was silently None. A longer
        run is used here specifically so at least one reproduction event
        happens after loading, which is what actually exercises the
        classify() codepath that reads reference_genome.
        """
        sim = Simulation(width=50, height=35, seed=4, initial_population=150)
        for _ in range(300):
            sim.step()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "world.json")
            save_simulation(sim, path)
            loaded = load_simulation(path)
        for sp in loaded.species_registry.species.values():
            self.assertIsNotNone(sp.reference_genome)
        for _ in range(300):
            loaded.step()  # must not raise

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


class TestMortalityCalibration(unittest.TestCase):
    """
    Regression test for the Phase 1 fix to RANDOM_DEATH_HAZARD: a flat,
    trait-independent per-tick death chance should stay a real but minor
    background risk, not a de facto cap on how much the lifespan trait
    can matter. Encodes the actual design intent (documented next to
    RANDOM_DEATH_HAZARD in simulation.py) directly, so a future change to
    the constant that quietly reintroduces the old problem gets caught
    here rather than only being visible as a subtler flattening of the
    lifespan trend in a chart.
    """

    def test_random_mortality_does_not_dominate_max_lifespan(self):
        from engine.simulation import RANDOM_DEATH_HAZARD
        from engine.organism import MAX_LIFESPAN_TICKS

        survival_probability = (1 - RANDOM_DEATH_HAZARD) ** MAX_LIFESPAN_TICKS
        self.assertGreater(
            survival_probability, 0.85,
            "an organism with the maximum lifespan trait should have a high chance "
            "of surviving to that age via background hazard alone, or the lifespan "
            "trait's top end is effectively being capped by an unrelated mechanic"
        )

    def test_random_mortality_still_a_real_nonzero_risk(self):
        from engine.simulation import RANDOM_DEATH_HAZARD
        self.assertGreater(RANDOM_DEATH_HAZARD, 0.0, "background risk should not be silently disabled")


class TestLineagePruning(unittest.TestCase):
    """
    Regression tests for the Phase 1 fix to prune_dead_history()/LineageIndex:
    ancestry must remain traceable after pruning (it always did, even before
    the fix), AND pruned Organism objects must actually become eligible for
    garbage collection (they did NOT before the fix, because LineageIndex
    held direct references to them independent of Simulation.organisms).
    """

    def test_ancestors_still_traceable_after_pruning(self):
        sim = Simulation(width=40, height=30, seed=5, initial_population=100)
        for _ in range(400):
            sim.step()
        dead_with_parent = [o for o in sim.organisms.values() if not o.alive and o.parent_id is not None]
        self.assertGreater(len(dead_with_parent), 0)
        target_id = dead_with_parent[0].id
        target_parent = dead_with_parent[0].parent_id

        before = sim.lineage.ancestors(target_id)
        sim.prune_dead_history(keep_last_n_dead=1)
        after = sim.lineage.ancestors(target_id)

        self.assertEqual(before, after)
        self.assertIn(target_parent, after)

    def test_pruning_actually_removes_organisms_from_simulation(self):
        sim = Simulation(width=40, height=30, seed=5, initial_population=100)
        for _ in range(400):
            sim.step()
        dead_count_before = sum(1 for o in sim.organisms.values() if not o.alive)
        self.assertGreater(dead_count_before, 1)

        sim.prune_dead_history(keep_last_n_dead=1)
        dead_count_after = sum(1 for o in sim.organisms.values() if not o.alive)
        self.assertLessEqual(dead_count_after, 1)

    def test_lineage_index_does_not_hold_organism_object_references(self):
        """
        The actual root-cause check: LineageIndex must store lightweight
        records, not the Organism objects themselves, or pruning is a
        no-op for memory (the bug this fix addresses).
        """
        from engine.lineage import LineageRecord
        sim = Simulation(width=20, height=20, seed=1, initial_population=20)
        for _ in range(30):
            sim.step()
        self.assertGreater(len(sim.lineage.records), 0)
        for record in sim.lineage.records.values():
            self.assertIsInstance(record, LineageRecord)


if __name__ == "__main__":
    unittest.main()
