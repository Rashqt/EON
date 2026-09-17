# DEMO WORLD

This folder contains the actual output of one real EON run, not sample
or placeholder data:

```
python3 cli.py run --ticks 2000 --width 70 --height 45 --population 220 --seed 42 \
    --save data/demo_world/DEMO_WORLD_seed42.json \
    --charts data/demo_world/DEMO_WORLD_seed42
```

- `DEMO_WORLD_seed42.json`: the full save file (environment, every
  organism alive or dead, species registry, event log, history). Load
  it with `python3 cli.py species --load data/demo_world/DEMO_WORLD_seed42.json`
  or `inspect`/`resume`.
- `DEMO_WORLD_seed42_population_species.png`: population and living
  species count over the 2000 ticks of this run.
- `DEMO_WORLD_seed42_traits.png`: average trait values over the same run.
- `DEMO_WORLD_seed42_worldmap.png`: a snapshot of the world and living
  organisms at tick 2000.

Because the world was created with seed 42, re-running the exact command
above reproduces the same initial world and organisms (see
"Reproducibility" in the main README).
