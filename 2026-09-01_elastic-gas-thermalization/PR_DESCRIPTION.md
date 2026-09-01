# Add Elastic Gas Thermalization demo

## Summary

This adds a new demo, `elastic_gas_thermalization.py`, from the physics
bucket. The series has recently leaned toward algorithms and ML/AI topics
(Dijkstra, genetic algorithms, perceptron/gradient descent all landed in the
last few rounds), so this round intentionally goes back to physics to keep
that bucket in regular rotation, since it's historically been one of the
strongest-performing categories (the N-body gravity sim). The topic —
elastic collisions converging to the Maxwell-Boltzmann speed distribution —
was picked because it has a genuine, well-known physical law behind it
(conservation of momentum and kinetic energy), a satisfying visual "event"
(a divider dropping and two populations mixing), and a real statistical
payoff (a histogram visibly converging onto a theoretical curve) that gives
the caption real substance to teach from.

## What's included

- `elastic_gas_thermalization.py` — the runnable demo (pygame, single file).
- `caption.txt` — the LinkedIn post copy for this demo.
- `HOW_TO_RUN.txt` — plain-language setup and run instructions for Jax.
- `PR_DESCRIPTION.md` — this file.

## How it works

70 particles start inside a sealed box, split by an invisible divider into
two populations: a slow "cold" cluster (speeds ~20–60) on the left and a
fast "hot" cluster (speeds ~220–340) on the right. Every particle has equal
mass. Each frame, particles move, bounce off the box walls, and are checked
pairwise for collisions with every other particle (a simple O(n²) check,
which is completely fine at 70 particles / 60fps).

When two particles collide, the simulation applies real elastic-collision
physics: for two equal-mass circles, an elastic collision exchanges only the
component of each particle's velocity that lies along the line connecting
their centers — the perpendicular component is untouched. This is a
well-known simplification of the general elastic collision equations that
falls out cleanly when the two masses are equal. No approximation or fudge
factor is involved beyond that.

After about 2.2 seconds, the invisible divider "drops" (visually, a glowing
vertical line retracts), and the hot and cold populations are free to
collide with each other. From that point on, every collision is a tiny
transfer of kinetic energy from a faster particle to a slower one (or vice
versa) — never a net creation or destruction of energy. Despite there being
no rule that pushes the system toward any particular "balanced" state, the
distribution of speeds across all 70 particles converges, empirically,
toward the 2D Maxwell-Boltzmann speed distribution: f(v) = (v/σ²)·e^(−v²/2σ²),
where σ² is derived live from the population's current mean squared speed.
This is the same statistical law that describes the spread of molecular
speeds in a real gas at a given temperature — it's why gases have a
predictable pressure and temperature relationship even though no individual
molecule's speed is "controlled."

## Design choices

- **Color as data, not decoration**: every particle's color is driven by its
  instantaneous speed via a five-stop gradient (deep blue → cyan → green →
  yellow → hot red/magenta), so the whole box reads as a live thermal map at
  a glance — you can see the hot cluster and cold cluster as literal color
  regions before the divider even drops, and watch the colors interleave as
  they mix.
- **Glow + additive blending**: particles are drawn with layered translucent
  circles blitted with `BLEND_RGBA_ADD` (same technique as `gravity_nbody.py`),
  and each collision spawns a quickly-expanding, fading ring in the collision
  color — a visible "event" marker so collisions read as things actually
  happening, not just particles passing through each other.
- **Fading trail surface**: rather than a hard clear each frame, a
  translucent surface is re-blitted over the screen every frame (same
  pattern as the existing boids/gravity demos), so motion leaves soft
  streaks instead of a static frame-by-frame snap.
- **HUD kept small and in a corner**: momentum, kinetic-energy ratio,
  collision count, and elapsed time are shown as four short lines in a
  translucent panel in the top-left — under a third of the screen — so the
  box of moving, glowing particles stays the dominant visual element rather
  than the numbers.
- **Histogram as a styled supporting element, not the centerpiece**: the
  live speed histogram is a small bottom-right panel with color-matched,
  glow-toned bars (not plain gray/white bars) and the theoretical
  Maxwell-Boltzmann curve overlaid in bright white — deliberately avoiding
  a "plain bar chart" look while still making the statistical convergence
  visible and legible.
- **A genuinely different motion style from prior demos**: instead of
  orbital/gravitational attraction (N-body) or steering/flocking (boids),
  this is hard-body elastic collision physics — a box, not open space; a
  divider "event" as a narrative beat; short-lived collision flashes instead
  of long comet trails as the main motion signature.

## How it was verified

Two methods were used:

1. **Headless full-loop run**: the real `main()` function was run under
   SDL's dummy video/audio drivers (`SDL_VIDEODRIVER=dummy`), with
   `pygame.event.get` monkey-patched to inject a QUIT event after 500
   frames. Result: **ran 500 frames through the full render loop (physics +
   drawing + HUD + histogram) with no exceptions.**
2. **Stubbed physics-only test**: the core simulation functions
   (`make_particles`, `resolve_wall_collisions`, `resolve_particle_collision`,
   `total_momentum`, `total_kinetic_energy`) were exercised directly for
   1000 simulation steps (no rendering) with a fixed random seed. Result:
   **425 particle-particle collisions occurred; kinetic energy ratio
   E1/E0 = 1.0000 (exactly conserved, as expected for elastic collisions);
   all particle positions and velocities remained finite and within the box
   bounds throughout.**

## What it teaches

Elastic collisions conserve both momentum and kinetic energy — this demo
makes that law directly checkable on screen instead of asking you to take
it on faith. More importantly, it shows how a macroscopic, predictable
pattern (the Maxwell-Boltzmann distribution) can emerge from purely local,
reversible, energy-conserving rules with no global coordination — the same
principle that underlies the kinetic theory of gases, and ultimately why
temperature and pressure are well-defined, predictable quantities for a gas
made of trillions of chaotically colliding molecules.

## To do before posting

- [ ] Run it locally to confirm it looks right on your machine
- [ ] Record a 10–20s clip (see HOW_TO_RUN.txt for the suggested moment to capture)
- [ ] Review/tweak caption.txt
- [ ] Post natively (own page Thursday / relevant groups Tuesday, per usual cadence)
