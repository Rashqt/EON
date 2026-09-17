# EON

Build a world. Start life. See what happens.

EON is an artificial-life simulation where organisms survive, reproduce,
mutate, and evolve inside a world governed by rules you define. You are
primarily an observer: you create a world, run it, and watch what
happens to it over simulated time.

This is not a scientifically accurate recreation of Earth's evolutionary
history, and its organisms are not alive or conscious. They are
computational agents inside a small, honest artificial ecosystem. See
"What is real, what is simplified" below before reading too much into
any single run.

## The idea

Give life simple rules, an environment, and time, and watch what
happens. EON does not script outcomes ("after N ticks, predators
appear"). It implements mechanics (movement, energy, reproduction,
mutation, environmental change) and lets whatever happens, happen. A run
can consolidate into a few dominant lineages, stay diverse, or die out
completely, depending on the seed and the rules, not on a prewritten
story.

## How it works

```
World (terrain, temperature, moisture, resources)
    -> Organisms (traits, energy, limited perception)
    -> Movement and feeding
    -> Survival or death
    -> Reproduction with mutation
    -> Natural selection (whichever traits survive and reproduce, do)
    -> Species classification by genetic distance
    -> Evolution, visible as trait averages drifting over generations
```

Every number EON reports (population, species count, extinction count,
an organism's traits) is read directly from the live simulation state.
Nothing in the CLI output or the exported charts is invented or
hardcoded.

## Features (implemented)

- Procedurally generated world: elevation, water, temperature, moisture,
  and per-cell renewable resources, generated from a random seed. Wet,
  dry, warm, cold, and coastal regions emerge from the combination of
  these values, they are not hand-placed.
- Organisms with nine heritable traits (size, speed, vision, metabolism,
  lifespan, reproduction rate, temperature tolerance, energy efficiency,
  mutation tendency), individually varied from birth.
- A real energy economy: organisms gain energy by consuming resource in
  their cell (scaled by their energy_efficiency trait) and spend it on
  metabolism, movement, and temperature mismatch. Energy at or below
  zero means death by starvation.
- Movement driven by limited local perception (a vision-trait-scaled
  radius), not global knowledge of the world.
- Asexual reproduction gated by energy and maturity, with heritable,
  probabilistic mutation (see `engine/genetics.py`). Mutations are not
  automatically beneficial.
- Species classification by genetic distance from a fixed founding
  reference genome, not by name or by random assignment. When a
  lineage's accumulated drift exceeds the distance threshold, it forms a
  new species with the parent species recorded as its ancestor. This
  means species splitting is a real, observed consequence of mutation
  and selection, not a scripted event, see
  `TestSpeciesTrackingAndExtinction.test_species_splitting_can_occur` in
  `tests/test_simulation.py` for a run where this is verified to happen.
- Extinction detection and recording (species ID, extinction tick, peak
  population, lineage) the moment a species' living population reaches
  zero.
- Environmental events (warming, cooling, drought, flood, resource
  collapse, resource boom) that actually mutate the environment grids,
  with small per-tick probability, and are logged when they occur.
- Lineage tracking: every organism records its parent, and species
  record their parent species. `LineageIndex` (`engine/lineage.py`) can
  trace ancestors and descendants from these real links.
- A chronological event log built only from things the engine actually
  detected (species emergence, extinctions, population fully dying out).
- Save and load: full simulation state (environment, every organism
  alive or dead, species registry, event log, and sampled history) to a
  single JSON file, and resuming a loaded world continues advancing it
  correctly.
- Deterministic worlds from a given random seed: the same seed and
  settings reproduce the same initial world and the same organism
  genomes.
- A CLI (`cli.py`) to run, resume, inspect an organism, and list species.
- Chart export: population-over-time, species-count-over-time, and
  average-trait-over-time, drawn from the actual recorded history, plus
  a world map snapshot (terrain, water, and live organism positions).
- A minimal, honestly-scoped behavior measurement: spatial clustering
  per species (`analysis/behavior.py`), computed from real organism
  positions each time it's called. This is the only "emergent behavior"
  metric implemented; see Limitations for what is not.
- 50 automated tests (`tests/`) covering world creation, organism
  creation, movement, energy, reproduction, mutation, death, species
  tracking, population calculations, extinction detection, environmental
  changes, save/load, deterministic seeds, and invalid/edge states.

## What is real, what is simplified

- Real: the energy economy, mutation, trait-distance species
  classification and splitting, extinction detection, environmental
  events, and every chart, all computed from live simulation state.
- Simplified, and worth knowing before you read too much into a chart:
  organisms don't perceive or react to each other directly (no
  predation, no flocking, no signaling), reproduction is asexual, and
  the world is a single flat grid with no seasons or day/night cycle.
  These are documented gaps, not claims of something more.

## Architecture

```
eon/
  engine/         world generation, organisms, genetics, movement, energy,
                  reproduction, species classification, events, lineage,
                  and the main simulation tick loop
  analysis/       reads simulation state/history and produces summaries
                  and chart-ready series; performs no simulation itself
  storage/        JSON save/load of full simulation state
  tests/          unittest-based test suite (50 tests)
  docs/           PRIVACY.md, TERMS.md
  cli.py          command-line entry point
```

The simulation engine (`engine/`) has no dependency on the CLI or on
matplotlib. Analysis and visualization only read state the engine
already produced.

## Technology

- Python 3.10+, NumPy for the world grid and vectorized environment
  math, Matplotlib for chart/world-map export.
- No web framework, database, or API in this version: EON is a local,
  offline batch/CLI tool. A live interactive graphical Observer Mode
  (the Play/Pause/Follow/Inspect UI described in the original design
  brief) is a natural next step but is not implemented here, see
  Limitations.
- Plain JSON for save files rather than SQLite: simulation state at MVP
  scale (thousands of organisms) serializes to a few megabytes and JSON
  keeps the format easy to inspect; SQLite would be a reasonable next
  step if very large or many concurrent worlds are needed.

## Installation

Requires Python 3.10 or later.

```bash
cd eon
pip install numpy matplotlib
```

(There is no `requirements.txt`-only path needed beyond these two
packages; `pyproject.toml` lists them if you prefer
`pip install -e .`.)

## Running EON

Create and run a new world for 2000 ticks, printing a report and periodic
progress:

```bash
python3 cli.py run --ticks 2000 --width 80 --height 50 --population 250 --seed 42
```

Run a world and also save it and export charts:

```bash
python3 cli.py run --ticks 2000 --seed 42 --save world.json --charts out/eon
```

This writes `world.json` and three PNGs:
`out/eon_population_species.png`, `out/eon_traits.png`,
`out/eon_worldmap.png`.

Resume a saved world and keep running it:

```bash
python3 cli.py resume --load world.json --ticks 1000 --charts out/eon_resumed
```

Inspect a specific organism from a saved world (get an ID from the
`species` command or from your own JSON inspection):

```bash
python3 cli.py inspect --load world.json --organism 4821
```

List living and extinct species from a saved world, including a spatial
clustering score:

```bash
python3 cli.py species --load world.json
```

## Controls (CLI flags)

| Flag | Applies to | Meaning |
|---|---|---|
| `--ticks` | run, resume | how many simulation ticks to advance |
| `--width`, `--height` | run | world grid size |
| `--population` | run | initial organism count |
| `--seed` | run | random seed; same seed + settings reproduce the same initial world |
| `--report-every` | run, resume | print a one-line progress update every N ticks (0 to disable) |
| `--save` | run, resume | path to write the save file to |
| `--load` | resume, inspect, species | path to an existing save file |
| `--charts` | run, resume | path prefix to export PNG charts to |
| `--organism` | inspect | organism ID to inspect |

There is no live pause/play/speed-multiplier control in this version:
you choose a tick count up front and EON runs it as a batch. See
Limitations.

## Data

Simulated (real, computed): world grids, organism traits and state,
species assignments and centroids, event log, sampled per-tick history
used for charts.

Not simulated (labelled where shown): none of the CLI/chart output is
sample or placeholder data. If you see a chart or report from EON, it
reflects an actual run.

## Reproducibility

Every world is created from an integer seed (`--seed`). The same seed,
width, height, and initial population reproduce the same initial
organisms and the same environment grids (`tests/test_simulation.py::TestDeterminism`
and `tests/test_environment.py::test_deterministic_with_same_seed`
verify this directly). Because the tick loop shuffles organism
processing order and draws further random numbers as it runs, a full
multi-thousand-tick run is not guaranteed bit-for-bit reproducible
across different NumPy versions, but is reproducible within a fixed
environment. Save your seed if you want to revisit a specific world.

## Limitations

Being direct about what this version does not do:

- No live interactive graphical Observer Mode. Play/Pause/Step/Speed/
  Follow/Inspect/Reset exist conceptually in the design but the actual
  interface here is the CLI plus static chart/image export. Building a
  live UI (web or desktop) on top of the existing engine is a
  reasonable next step; the engine was kept UI-independent for exactly
  that reason.
- No predation, flocking, territoriality, communication, or any other
  organism-to-organism interaction. Movement only reacts to the
  environment (resource, temperature), not to other organisms. The
  `analysis/behavior.py` clustering score is the only behavior metric
  that is actually measured; no other emergent behavior is claimed.
- No sexual reproduction; reproduction is asexual with mutation only, no
  trait recombination between two parents.
- No true spatial partitioning or neighbor-lookup data structure for
  organism-to-organism queries, since the current mechanics don't need
  one. Movement and energy calculations are per-organism against the
  environment grid, which is why performance holds up to roughly a few
  thousand simultaneous organisms in pure Python but slows down
  further beyond that. Very large simulations (tens of thousands of
  organisms) would need this or a NumPy-vectorized organism update.
- No experiment-mode (paired control/modified world comparison) tooling
  is implemented, despite being part of the original design brief.
  The engine's determinism and save/load make it straightforward to
  build as a script (run the same seed twice, mutate the environment
  differently between runs, diff the resulting histories), but that
  script does not exist yet.
- Performance: pure-Python per-organism ticking runs at roughly
  50-100 ticks/second at a few hundred organisms on typical hardware,
  slowing as population grows, on the machine this was built on. There
  is a soft population ceiling (`SOFT_POPULATION_CEILING` in
  `engine/simulation.py`) that adds crowding mortality above 6000
  simultaneous organisms, purely to keep runs responsive; it is not a
  narrative rule.
- No day/night cycle, seasons, or multi-layer ecology (no plants versus
  herbivores versus predators); "resource" is a single abstract food/
  energy quantity per cell.

## Testing

```bash
cd eon
python3 -m unittest discover -s tests -p "test_*.py" -v
```

50 tests, all passing at the time of writing. `pytest` was not available
in the environment this was built in (no network access to install it),
so the suite uses Python's built-in `unittest`; it will also run under
`pytest tests/` if you have it installed, since `unittest.TestCase`
classes are pytest-compatible.

## Future ideas

Listed as ideas, not implemented features: a live web or desktop
Observer Mode UI reading the same engine state; organism-to-organism
interaction (predation, flocking, signaling); sexual reproduction and
trait recombination; a proper spatial index for large populations;
paired experiment-mode comparisons; a graphical family-tree explorer
built on the existing `LineageIndex`; seasons and a day/night cycle.

## License

MIT License, see `LICENSE`.

## About Rashqt

I'm Rashqt, a young developer and creator who enjoys building unusual
projects and figuring out how things work. EON started as a simple
question: what happens if I stop telling every creature what to do and
just give them a world to survive in?

---

© 2025 Rashqt. Made with care in the late hours.
