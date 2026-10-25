# Changelog

## Phase 2 - live web interface

- New local web UI (`python3 serve.py`): live map with layers, zoom, pan,
  hover readouts, click-to-inspect, follow mode with trail, species
  browser and detail (population history, average traits, where they
  live, lineage), charts (population, species and extinctions, traits,
  births and deaths, environment), event log, new world, save and load.
  Light palette: ice silver, deep aubergine, marigold.
- `api/server.py`: stdlib JSON server running the simulation in a
  background thread, bound to 127.0.0.1.
- History now also records average land food and temperature per tick.
- Saves now store lineage records separately, so ancestry survives when
  old dead creatures were pruned before saving (the UI prunes to stay fast).
- Tests: `tests/test_api.py`, `tests/test_lineage_persistence.py`.

## Phase 1 (verify & harden) - this session

Following a review pass (see `eon_roadmap.md` if kept alongside this
project), the existing test suite was confirmed green, then these real
issues were found and fixed:

1. **`Species.reference_genome` typed as `Genome` but defaulted to
   `None`.** Not a runtime bug on its own, but a foot-gun for type
   checkers and future refactors. Fixed to `Optional[Genome] = None`
   (`engine/species.py`).

2. **Flat random-mortality hazard was undercutting the lifespan trait's
   top end.** At the old hazard (0.0008/tick), an organism with the
   maximum possible lifespan trait had only about a 49% chance of
   surviving to that age via background risk alone, before its trait
   ever got to matter. Recalibrated to 0.0001/tick, which gives about a
   91% chance at the same age, keeping background risk real without
   quietly capping the trait. See the comment above
   `RANDOM_DEATH_HAZARD` in `engine/simulation.py` and
   `tests/test_simulation.py::TestMortalityCalibration`.

3. **`prune_dead_history()` did not actually free memory, and its own
   docstring was wrong about why.** `LineageIndex` (`engine/lineage.py`)
   held direct references to full `Organism` objects, independent of
   `Simulation.organisms`, so removing an organism from
   `Simulation.organisms` never made it eligible for garbage collection;
   the docstring's claim that pruning made lineage "not recoverable" was
   also false; lineage tracing kept working fine, just for the wrong
   reason (nothing was ever actually released). Fixed by having
   `LineageIndex` store a small `LineageRecord` (parent_id, species_id,
   generation, birth_tick) instead of the object itself, decoupling
   ancestry tracking from full organism state. See
   `tests/test_simulation.py::TestLineagePruning`.

4. **`storage/save.py` never persisted `Species.reference_genome`,
   because it was written before that field existed on `Species`.**
   A loaded world crashed the moment it tried to classify a newly born
   organism into an existing species, since `reference_genome` silently
   deserialized as `None`. This was the most serious of the four: any
   saved-and-reloaded world with reproduction still enabled would have
   crashed on its next birth. Fixed in `storage/save.py` and
   `storage/load.py` (with a backward-compatible, explicitly-noted
   fallback to `centroid` for save files written before this fix).
   See `tests/test_simulation.py::test_loaded_species_preserve_reference_genome`.

Test suite: 56 tests (73 after Phase 2), all passing (`tests/`).

The `data/demo_world/` save file was regenerated after these fixes;
the earlier version was written by the pre-fix `save.py` and would not
have reloaded correctly under this code.
