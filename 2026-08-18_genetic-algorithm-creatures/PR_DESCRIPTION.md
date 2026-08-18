# Add Genetic Algorithm: Evolving Creatures demo

## Summary

This adds a new demo, `genetic_creatures.py`, showing a genetic algorithm
evolving a population of simple creatures to navigate from a start point to
a target while avoiding obstacles. This one comes from the **ML/AI bucket**
of the series. It was picked this round because the last two demos leaned
algorithms (recursive-backtracking maze generation) and physics (wave
interference), so this keeps the rotation mixed, and because "population
of agents visibly getting smarter over generations" is a strong fit for a
short screen-recorded clip — there's a clear visual before/after (random
flailing vs. converged, confident paths) in a way that reads instantly even
muted. It has no overlap with any previously covered topic (checked against
the existing dated folders and the "already covered" list: this is not
Q-learning, not ant colony pheromone optimization, and not boids — it uses
a fixed per-creature genome evolved across discrete generations via
selection/crossover/mutation, which is a distinct mechanism from all three).

## What's included

- `genetic_creatures.py` — the runnable pygame demo (genetic algorithm logic + rendering).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup and run instructions for a non-developer.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — exact copy-paste git/GitHub commands to publish this demo.

## How it works

Each creature's entire behavior is encoded as a **genome**: a fixed list of
20 steering angles ("genes"). When a creature is simulated, it plays its
genes in order, holding each one for a short stretch of frames while its
heading eases smoothly toward that gene's direction (rather than snapping
instantly, which is what gives the paths their curved, organic look instead
of jagged zig-zags). This is fully deterministic and open-loop — a creature
never "sees" the obstacles or reacts to anything; its whole path is baked
into its genome before the generation even starts.

After every creature in the population has played out its full path, each
one gets a **fitness score**: mostly driven by how close it got to the
target at its closest point, with a large bonus for actually reaching the
target (plus extra credit for arriving early) and a penalty for crashing
into an obstacle along the way.

Then comes **selection and reproduction**, which is the actual "genetic
algorithm" part:
- **Elitism** — the top few creatures are copied unchanged into the next
  generation, so a good solution is never accidentally lost.
- **Crossover** — most of the next generation is built by picking two
  parents from the top half of the population and building a child genome
  where each gene is randomly inherited from one parent or the other
  (uniform crossover).
- **Mutation** — after crossover, each gene in a child has a chance to get
  randomly nudged by a small random angle, which is what introduces new
  variation the population hasn't tried yet.
- **Random immigrants** — a handful of completely fresh, random genomes are
  thrown into every new generation. This is a standard technique to stop
  the population from prematurely converging on one mediocre route and
  never discovering a better one.

Run that loop enough times and the population's average and best fitness
trend upward — not because anything was told how to solve the maze of
obstacles, but because bad solutions keep dying out and good (or lucky)
ones keep getting bred and refined.

## Design choices

- **Color palette**: creatures are colored on a continuous gradient from
  deep blue (low fitness this generation) to hot gold (high fitness), with
  the single best creature in each generation rendered pure white. This
  maps the population's fitness spread directly onto color instead of
  printing numbers next to shapes — you can read the swarm's collective
  progress at a glance.
- **Motion style**: this is intentionally different from the series' other
  swarm-style demos (boids, ant colony, N-body gravity). Instead of
  reactive steering rules or continuous force fields, each creature commits
  to a pre-baked genome and plays it forward blind — the visual signature is
  "many independent, curving comet trails converging toward one point,"
  rather than flocking or orbiting.
- **Glow and trails**: creatures are drawn with the same additive-blend,
  layered-circle glow technique used in the gravity demo, and leave a
  short fading streak by drawing their glow onto a trail surface that's
  faded (not cleared) each frame.
- **Target and obstacles**: the target pulses with concentric magenta
  rings so it reads clearly as "the goal," and obstacles have a slow
  breathing outline glow rather than being flat, dead shapes.
- **HUD**: kept to a small rounded panel in the top-left corner (generation
  count, this generation's best fitness, best fitness ever, how many
  creatures reached the target) plus a small glowing sparkline of best
  fitness per generation tucked into the same panel — together well under
  a third of the screen, with the swarm's motion carrying the visual weight.
- **Smoothness**: runs a real 60fps loop (`clock.tick(60)`), and headings
  are eased toward each gene's target direction every frame (linear
  interpolation of the direction vector) rather than snapping, so paths
  curve instead of jittering.

## How it was verified

- `python3 -m py_compile genetic_creatures.py` — passed, no syntax errors.
- Full headless run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 genetic_creatures.py` — pygame initialized, the real render loop executed for its full 400-frame self-test window (multiple generations, including the evolve/reset transition), and exited cleanly with code 0.
- Additional stubbed-logic test (throwaway, deleted before finishing): imported the module's pure GA functions directly and ran 30 generations of a 36-creature population, asserting every single position on every creature's path was finite and within screen bounds (catching the divide-by-zero/blow-up failure mode this checklist calls out). Fitness improved from an initial best of about -428 to a final best of about +506 across 30 generations, and by generation 10 several creatures were successfully reaching the target — confirming the selection/crossover/mutation loop actually converges rather than just running without crashing.

## What it teaches

Genetic algorithms solve problems by generating and repeatedly refining a
population of candidate solutions through survival-of-the-fittest selection,
gene mixing (crossover), and random mutation — with no gradient or explicit
reward signal telling any individual how to improve. This is the same
family of technique used in real-world evolutionary robotics (evolving gait
controllers), procedural game content, and optimization problems (like
scheduling or circuit layout) where the search space is too rough or
poorly understood for gradient-based methods like backpropagation to work
directly.

## To do before posting

- [ ] Run it locally to confirm it looks right on your machine.
- [ ] Record a 10-20 second clip (ideally spanning a generation reset so the improvement is visible).
- [ ] Review caption.txt and adjust if needed for the specific group/page you're posting to.
- [ ] Post natively (upload the video file directly) with the caption.
