import os
import tempfile
import unittest

from engine.simulation import Simulation
from storage.load import load_simulation
from storage.save import save_simulation


class TestLineagePersistence(unittest.TestCase):
    def test_ancestry_survives_pruning_then_save_and_load(self):
        sim = Simulation(width=40, height=30, seed=5, initial_population=100)
        for _ in range(400):
            sim.step()
        dead = [o for o in sim.organisms.values() if not o.alive and o.parent_id is not None]
        self.assertGreater(len(dead), 0)
        target = dead[0].id
        before = sim.lineage.ancestors(target)
        desc_before = len(sim.lineage.descendants(dead[0].parent_id))
        sim.prune_dead_history(keep_last_n_dead=1)
        self.assertNotIn(target, sim.organisms)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.json")
            save_simulation(sim, path)
            loaded = load_simulation(path)
        self.assertEqual(loaded.lineage.ancestors(target), before)
        self.assertEqual(len(loaded.lineage.descendants(dead[0].parent_id)), desc_before)

    def test_history_records_environment_series(self):
        sim = Simulation(width=30, height=20, seed=2, initial_population=30)
        for _ in range(5):
            sim.step()
        self.assertIn("avg_resource", sim.history[-1])
        self.assertIn("avg_temperature", sim.history[-1])


if __name__ == "__main__":
    unittest.main()
