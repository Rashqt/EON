import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from api import server
from api.server import Runner, make_server


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.r = Runner(width=30, height=20, seed=3, population=40)

    def tearDown(self):
        self.r._stop.set()

    def test_frame_numbers_match_simulation_state(self):
        f = self.r.frame()
        alive = sum(1 for o in self.r.sim.organisms.values() if o.alive)
        self.assertEqual(f["stats"]["population"], alive)
        self.assertEqual(len(f["orgs"]), alive)
        self.assertEqual(f["stats"]["species"], 40)
        self.assertEqual(len(f["values"]), 30 * 20)

    def test_step_advances_tick(self):
        self.r.control({"action": "step"})
        self.assertEqual(self.r.frame()["tick"], 1)

    def test_play_then_pause_advances_time(self):
        self.r.control({"action": "speed", "tps": 0})
        self.r.control({"action": "play"})
        time.sleep(0.6)
        self.r.control({"action": "pause"})
        t = self.r.frame()["tick"]
        self.assertGreater(t, 0)
        time.sleep(0.2)
        self.assertEqual(self.r.frame()["tick"], t)

    def test_organism_info_has_calculated_fields(self):
        oid = self.r.frame()["orgs"][0][0]
        info = self.r.organism(oid)
        self.assertEqual(info["id"], oid)
        self.assertIn("temperature_gap", info["calculated"])
        self.assertEqual(len(info["genome"]), 9)
        self.assertIsNone(self.r.organism(99999999))

    def test_species_detail_and_list(self):
        for _ in range(30):
            self.r.step_once()
        sp = self.r.species_list()
        self.assertGreater(sp["living_total"], 0)
        sid = sp["living"][0]["id"]
        d = self.r.species_detail(sid)
        self.assertEqual(len(d["geo"]), 10)
        self.assertEqual(sum(map(sum, d["geo"])), d["population"])
        self.assertIsNone(self.r.species_detail(99999999))

    def test_history_columns_line_up(self):
        for _ in range(20):
            self.r.step_once()
        h = self.r.history()
        n = len(h["tick"])
        self.assertGreater(n, 0)
        for key in ("population", "species_count", "births_total", "deaths_total"):
            self.assertEqual(len(h[key]), n)
        self.assertEqual(len(h["traits"]["speed"]), n)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            self.r.control({"action": "explode"})

    def test_new_world_changes_version_and_clamps_size(self):
        v = self.r.world_version
        self.r.control({"action": "new", "seed": 5, "width": 5, "height": 5, "population": 99999})
        self.assertEqual(self.r.world_version, v + 1)
        self.assertEqual(self.r.config["width"], 20)
        self.assertEqual(self.r.config["population"], 3000)

    def test_save_rejects_unsafe_names(self):
        for bad in ("../x", "a/b", "", "x" * 60):
            with self.assertRaises(ValueError):
                self.r.save(bad)

    def test_save_and_load_roundtrip(self):
        old = server.SAVE_DIR
        with tempfile.TemporaryDirectory() as d:
            server.SAVE_DIR = d
            try:
                for _ in range(15):
                    self.r.step_once()
                tick = self.r.frame()["tick"]
                self.r.save("snap")
                self.r.control({"action": "new", "seed": 9, "width": 30, "height": 20, "population": 10})
                self.assertEqual(self.r.frame()["tick"], 0)
                self.r.load("snap")
                self.assertEqual(self.r.frame()["tick"], tick)
                self.assertEqual([s["name"] for s in self.r.saves()], ["snap"])
            finally:
                server.SAVE_DIR = old


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.runner = make_server(port=0, width=30, height=20, seed=1, population=30)
        cls.port = cls.srv.server_address[1]
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.runner._stop.set()
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}")

    def post(self, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/control", json.dumps(body).encode(),
            {"Content-Type": "application/json"})
        return urllib.request.urlopen(req)

    def test_index_and_docs_pages_served(self):
        for path in ("/", "/privacy", "/terms"):
            self.assertEqual(self.get(path).status, 200)

    def test_frame_endpoint_returns_json(self):
        data = json.load(self.get("/api/frame?layer=temperature"))
        self.assertEqual(data["layer"], "temperature")
        self.assertEqual(data["stats"]["population"], 30)

    def test_unknown_route_is_404_json(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.get("/api/nope")
        self.assertEqual(cm.exception.code, 404)

    def test_bad_action_is_400(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post({"action": "explode"})
        self.assertEqual(cm.exception.code, 400)

    def test_missing_organism_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.get("/api/organism/99999999")
        self.assertEqual(cm.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
