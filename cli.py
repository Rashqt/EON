#!/usr/bin/env python3
"""
EON command-line interface.

This is the actual way to run EON in this version. There is no live
interactive graphical Play/Pause/Follow interface in the MVP (see
README "Limitations"). This CLI runs a simulation for a chosen number of
ticks, prints a report built entirely from simulation state, and can
export real charts (population, species count, trait averages) and a
snapshot image of the world map.

Usage:
    python3 cli.py run --ticks 2000 --width 80 --height 50 --population 250 --seed 42
    python3 cli.py run --ticks 2000 --seed 42 --save world.json
    python3 cli.py resume --load world.json --ticks 1000
    python3 cli.py inspect --load world.json --organism 4821
    python3 cli.py species --load world.json
"""

from __future__ import annotations

import argparse
import sys
import time

from engine.simulation import Simulation
from storage.save import save_simulation
from storage.load import load_simulation
from analysis import population as pop_analysis
from analysis import evolution as evo_analysis
from analysis import extinction as ext_analysis
from analysis import behavior as behavior_analysis


def print_report(sim: Simulation) -> None:
    print()
    print(f"WORLD  seed={sim.seed}")
    print(f"Age (ticks): {sim.tick}")
    print(f"Population: {sim.stats.population}")
    print(f"Species (living): {sim.stats.species_count}")
    print(f"Extinctions (total): {sim.extinction_count}")
    print(f"Total births: {sim.total_births}")
    print(f"Total deaths: {sim.total_deaths}")
    print()
    shifts = evo_analysis.trait_shift_summary(sim)
    if shifts:
        print("Trait averages, first recorded tick to latest:")
        for name, (start, end) in shifts.items():
            direction = "up" if end > start else ("down" if end < start else "flat")
            print(f"  {name:24s} {start:.3f} -> {end:.3f}  ({direction})")
    print()
    print("Recent events:")
    for e in sim.event_log.recent(15):
        print(f"  [tick {e.tick:>7}] ({e.category}) {e.text}")
    print()


def run_ticks(sim: Simulation, ticks: int, report_every: int = 0) -> None:
    t0 = time.time()
    for i in range(1, ticks + 1):
        sim.step()
        if report_every and i % report_every == 0:
            print(f"tick {sim.tick:>7}  population {sim.stats.population:>6}  "
                  f"species {sim.stats.species_count:>4}  extinctions {sim.extinction_count:>4}")
    elapsed = time.time() - t0
    print(f"\nRan {ticks} ticks in {elapsed:.2f}s ({ticks / max(elapsed, 1e-6):.1f} ticks/sec).")


def export_charts(sim: Simulation, out_prefix: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ticks, pop = pop_analysis.population_series(sim)
    _, species = pop_analysis.species_series(sim)

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    axes[0].plot(ticks, pop, color="#4fd1c5")
    axes[0].set_ylabel("Population")
    axes[0].set_title(f"World seed={sim.seed}: population and species over time")
    axes[1].plot(ticks, species, color="#f6ad55")
    axes[1].set_ylabel("Living species")
    axes[1].set_xlabel("Tick")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}_population_species.png", dpi=130)
    plt.close(fig)

    trait_series = evo_analysis.all_trait_series(sim)
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, (t, v) in trait_series.items():
        if v:
            ax.plot(t, v, label=name, linewidth=1.2)
    ax.set_title(f"World seed={sim.seed}: average trait values over time")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Trait value (0-1)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}_traits.png", dpi=130)
    plt.close(fig)

    export_world_map(sim, f"{out_prefix}_worldmap.png")
    print(f"Charts written: {out_prefix}_population_species.png, {out_prefix}_traits.png, {out_prefix}_worldmap.png")


def export_world_map(sim: Simulation, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    env = sim.environment
    fig, ax = plt.subplots(figsize=(9, 6))
    terrain = np.where(env.is_water, np.nan, env.resource / np.maximum(env.resource_cap, 1e-6))
    ax.imshow(terrain, cmap="YlGn", origin="upper", vmin=0, vmax=1)
    water_overlay = np.ma.masked_where(~env.is_water, np.ones_like(env.elevation))
    ax.imshow(water_overlay, cmap="Blues", origin="upper", vmin=0, vmax=1, alpha=0.9)

    living = sim.living_organisms()
    if living:
        ys = [o.y for o in living]
        xs = [o.x for o in living]
        ax.scatter(xs, ys, s=4, c="#c53030", alpha=0.7, linewidths=0)

    ax.set_title(f"World seed={sim.seed}, tick {sim.tick}: terrain (green=resource fill, blue=water), red dots=organisms")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def cmd_run(args: argparse.Namespace) -> None:
    sim = Simulation(width=args.width, height=args.height, seed=args.seed, initial_population=args.population)
    run_ticks(sim, args.ticks, report_every=args.report_every)
    print_report(sim)
    if args.charts:
        export_charts(sim, args.charts)
    if args.save:
        save_simulation(sim, args.save)
        print(f"Saved world state to {args.save}")


def cmd_resume(args: argparse.Namespace) -> None:
    sim = load_simulation(args.load)
    print(f"Loaded world from {args.load} at tick {sim.tick}, population {sim.stats.population}.")
    run_ticks(sim, args.ticks, report_every=args.report_every)
    print_report(sim)
    if args.charts:
        export_charts(sim, args.charts)
    save_path = args.save or args.load
    save_simulation(sim, save_path)
    print(f"Saved world state to {save_path}")


def cmd_inspect(args: argparse.Namespace) -> None:
    sim = load_simulation(args.load)
    org = sim.get_organism(args.organism)
    if org is None:
        print(f"No organism with id {args.organism} found in this save.", file=sys.stderr)
        sys.exit(1)
    print(f"SPECIMEN #{org.id}")
    print(f"Species: {org.species_id}")
    print(f"Age: {org.age}   Generation: {org.generation}")
    print(f"Energy: {org.energy:.1f}   Health: {org.health:.1f}")
    print(f"Position: ({org.y}, {org.x})")
    print("Traits:")
    for name, value in org.genome.__dict__.items():
        print(f"  {name:24s} {value:.3f}")
    print(f"Parent: {org.parent_id}")
    print(f"Children born: {org.children_count}")
    print(f"Birth tick: {org.birth_tick}")
    print(f"Status: {'alive' if org.alive else f'dead ({org.death_cause}) at tick {org.death_tick}'}")
    ancestors = sim.lineage.ancestors(org.id, max_depth=10)
    print(f"Recorded ancestor chain (up to 10): {ancestors}")


def cmd_species(args: argparse.Namespace) -> None:
    sim = load_simulation(args.load)
    print("Living species:")
    for row in ext_analysis.living_species_summary(sim)[:30]:
        print(f"  species {row['species_id']:<5} population={row['population']:<5} "
              f"peak={row['peak_population']:<5} created_tick={row['created_tick']:<8} "
              f"parent_species={row['parent_species_id']}")
    print("\nExtinct species (most recent 20):")
    for row in ext_analysis.extinct_species_summary(sim)[-20:]:
        print(f"  species {row['species_id']:<5} lived_ticks={row['lifespan_ticks']:<8} "
              f"peak={row['peak_population']:<5} extinct_at_tick={row['extinction_tick']}")
    scores = behavior_analysis.species_clustering_score(sim)
    if scores:
        print("\nSpatial clustering score (species with >=3 living members; <1.0 means "
              "members sit closer together than random chance would predict):")
        for sid, score in sorted(scores.items(), key=lambda kv: kv[1])[:15]:
            print(f"  species {sid:<5} clustering_score={score:.3f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EON: an artificial-life simulation.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Create a new world and run it.")
    p_run.add_argument("--ticks", type=int, default=2000)
    p_run.add_argument("--width", type=int, default=80)
    p_run.add_argument("--height", type=int, default=50)
    p_run.add_argument("--population", type=int, default=250)
    p_run.add_argument("--seed", type=int, default=0)
    p_run.add_argument("--report-every", type=int, default=200, dest="report_every")
    p_run.add_argument("--save", type=str, default=None, help="Path to write a save file to.")
    p_run.add_argument("--charts", type=str, default=None, help="Path prefix to write PNG charts to.")
    p_run.set_defaults(func=cmd_run)

    p_resume = sub.add_parser("resume", help="Load a saved world and keep running it.")
    p_resume.add_argument("--load", type=str, required=True)
    p_resume.add_argument("--ticks", type=int, default=1000)
    p_resume.add_argument("--report-every", type=int, default=200, dest="report_every")
    p_resume.add_argument("--save", type=str, default=None, help="Defaults to overwriting --load.")
    p_resume.add_argument("--charts", type=str, default=None)
    p_resume.set_defaults(func=cmd_resume)

    p_inspect = sub.add_parser("inspect", help="Inspect a single organism from a saved world.")
    p_inspect.add_argument("--load", type=str, required=True)
    p_inspect.add_argument("--organism", type=int, required=True)
    p_inspect.set_defaults(func=cmd_inspect)

    p_species = sub.add_parser("species", help="List living and extinct species from a saved world.")
    p_species.add_argument("--load", type=str, required=True)
    p_species.set_defaults(func=cmd_species)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
