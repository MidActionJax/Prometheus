# Add Ant Colony Optimization demo

## Summary

This adds a new pygame demo, `ant_colony_optimization.py`, that visualizes Ant
Colony Optimization (ACO): a colony of simulated ants finds the shortest of
four candidate routes between a nest and a food source purely through
pheromone deposition and evaporation, with no ant ever comparing path lengths
directly. This round's topic comes from the **simulations/swarm-intelligence**
bucket. It was picked because it's visually rich (four independently glowing,
fading trails competing for dominance in real time) while teaching a genuinely
different mechanism than anything already in the repo — the closest existing
demo (boids flocking) is about *coordinated movement*, whereas this one is
about *decentralized optimization via shared environment feedback*
(stigmergy), which is a distinct and important AI/algorithms concept in its
own right. It continues the series' mixed-bag rotation across algorithms, ML,
and simulation topics.

## What's included

- `ant_colony_optimization.py` — the runnable pygame demo: the ACO simulation
  (paths, ants, pheromone deposition/evaporation) plus the rendering loop and
  live HUD.
- `caption.txt` — the LinkedIn post copy for this demo.
- `HOW_TO_RUN.txt` — plain-language setup, run, recording, and posting
  instructions for Jax.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — the exact copy-paste git/GitHub commands to publish
  this demo.

## How it works

Four possible routes are drawn from NEST to FOOD as quadratic Bezier curves
with slightly different lengths (roughly 841px to 884px), sampled into
polylines so both their pixel path and their true length can be computed.
Every fraction of a second, a small wave of new "ants" is dispatched; each
one independently picks a route using the same weighted-random rule real ACO
algorithms use: `desirability = pheromone^alpha * (1/length)^beta`, normalized
across all four routes into a probability distribution. An ant then walks its
chosen route at a constant pixel speed. Because routes differ in length, ants
on shorter routes complete their trip sooner — meaning they deposit pheromone
(`+= Q / length`) more frequently per unit of real time, not because they're
"smarter" but purely because they get more trips in. Every path's pheromone
also evaporates continuously (`pheromone *= (1 - rate)^dt`), so pheromone has
to be actively replenished to persist, which prevents the system from
freezing on an early, possibly-wrong answer and keeps a small but nonzero
chance of any path being chosen (a pheromone floor keeps this true even after
long runs). The net effect: a path that is even slightly shorter accumulates
pheromone slightly faster, which raises its selection probability, which
sends it more ants, which raises its pheromone further — a positive feedback
loop that reliably (not guaranteed on every single run, but overwhelmingly in
practice) converges on the globally shortest route with no ant, and no
central process, ever computing "which path is shortest."

## Design choices

- **Palette**: each of the four paths gets its own neon hue (cyan, magenta,
  yellow, green) against a near-black background, matching the established
  aesthetic. Line brightness and thickness both scale with that path's
  current pheromone level relative to the strongest path, so the "winning"
  path visibly pulls away from the others instead of the viewer needing to
  read numbers to see what's happening.
- **Ant trail glow**: ants are drawn as small bright dots onto a persistent
  alpha surface that's multiplied down toward transparent each frame (rather
  than cleared), producing a soft fading comet trail behind each ant — the
  same category of trail effect used in the boids demo, adapted here to
  individual agents rather than the whole flock.
- **HUD**: shows tick count, total ants dispatched/arrived, and — per path —
  its length in pixels, current pheromone value, and live selection
  probability, with a "currently favored" tag on whichever path is winning
  after the first couple of seconds. This is the "proof it's really running"
  element: the probabilities visibly shift in response to the pheromone
  race, not on a fixed timer.
- **Implementation note**: all of the actual algorithm state (`PheromonePath`,
  `Ant`, `Simulation` classes) is written with zero pygame calls anywhere in
  it — `main()` only reads that state to draw. This was done specifically so
  the algorithm could be verified headlessly (see below) and, incidentally,
  makes the code easier to read next to a screen recording since the "math"
  and the "drawing" are cleanly separated.

## How it was verified

The sandbox this was built in has no network access (can't `pip install
pygame`) and no display, so pygame itself could not be run directly. Two
fallback methods were used instead:

1. `python3 -m py_compile ant_colony_optimization.py` — passed, confirming
   the file is syntactically valid.
2. A throwaway test stubbed `pygame` in `sys.modules` with no-op fakes (so
   the file's `import pygame` and rendering calls succeed harmlessly), then
   imported the real `Simulation` class and ran it for 6,000 steps at a
   fixed 1/60s timestep (~100 simulated seconds) with per-step assertions
   that every path's pheromone stayed finite and above its floor, every
   ant's progress stayed finite and non-negative, and dispatch/arrival
   counts behaved sanely. Result: all checks passed — 798 ants dispatched,
   774 arrived, and critically, the simulation converged onto path 0 (the
   geometrically shortest at 840.7px), which finished with ~99.4% selection
   probability vs. ~0.1-0.3% for the other three. This confirms the
   algorithm doesn't just run without crashing — it actually produces the
   intended result. The throwaway test file was deleted after verification;
   only the five files listed above remain in this folder.

## What it teaches

Ant Colony Optimization shows that a system-level "smart" outcome (finding a
shortest path) doesn't require any individual agent to be smart, or to have
any awareness of alternatives — it can emerge purely from simple local
behavior (walk, deposit, evaporate) plus a feedback loop. The same principle
underlies real ACO algorithms used for vehicle routing, network packet
routing, and job-shop scheduling, and more broadly is a core idea in
swarm intelligence and decentralized/emergent systems design.

## To do before posting

- [ ] Run it locally to confirm it looks right on your machine.
- [ ] Record a 10-20s clip (let it run 20-30s first so the divergence is
      already visible, or speed up the clip in editing).
- [ ] Review caption.txt and tweak if anything doesn't sound like you.
- [ ] Post natively to LinkedIn with the video uploaded directly.
