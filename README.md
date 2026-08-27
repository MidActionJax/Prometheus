# Prometheus

A collection of small, visual Python demos exploring AI, algorithms, and
software engineering concepts — built to be screen-recorded and shared.

Each demo lives in its own dated folder and includes:
- the runnable Python script
- `caption.txt` — the write-up used when posting
- `HOW_TO_RUN.txt` — plain-language setup and run instructions

## Demos

- [2026-08-27 — Gradient Descent: Learning a Linear Separator](2026-08-27_perceptron-gradient-descent/) — a logistic-regression perceptron trains live via gradient descent on binary cross-entropy loss, rendering its confidence as a glowing cyan-to-magenta field with a bright seam at the 50/50 decision boundary that slides into place between two data clouds.
- [2026-08-25 — Double Pendulum Chaos](2026-08-25_double-pendulum-chaos/) — a fan of double pendulums released from starting angles a fraction of a degree apart, integrated with real Lagrangian mechanics via RK4, visibly tearing apart into chaos as sensitive dependence on initial conditions plays out live.
- [2026-08-20 — Dijkstra's Shortest Path: Animated Edge Relaxation](2026-08-20_dijkstra-shortest-path/) — a priority-queue-driven shortest-path search over a random weighted graph, with settled nodes colored by a cyan-to-magenta heat gradient as the distance wavefront spreads from the source and a comet particle traces the final shortest-path tree.
- [2026-08-18 — Genetic Algorithm: Evolving Creatures](2026-08-18_genetic-algorithm-creatures/) — a population of creatures, each carrying a fixed steering genome, evolves across generations via elitism, crossover, and mutation to route around obstacles and reach a target, with color shifting from cold blue to hot gold as fitness improves.
- [2026-08-13 — Wave Interference](2026-08-13_wave-interference/) — two glowing point sources emit circular waves that sum by pure superposition, producing live constructive hot spots and the dark hyperbolic nodal lines behind Young's double-slit experiment.
- [2026-08-11 — Recursive Backtracking Maze Generation](2026-08-11_maze-generation-backtracking/) — a randomized depth-first search carves a perfect maze in real time, with corridor hue mapped to recursion depth and a gold finale tracing the maze's longest path.
- [2026-08-06 — N-Body Gravity Simulation](2026-08-06_nbody-gravity/) — true N-body gravity (every body pulls on every other body via Newton's law) with glowing trails, producing chaotic, never-repeating orbital paths from a heavy central body plus several lighter ones.
- [2026-08-06 — Self-Attention Visualization](2026-08-06_self-attention-visualization/) — the Transformer self-attention mechanism (softmax of scaled query-key dot products) rendered as glowing lines between sentence tokens, featuring a coreference example where "it" attends back to "cat".
- [2026-08-04 — Q-Learning Grid World](2026-08-04_q-learning-gridworld/) — a reinforcement-learning agent learns, from step-cost/hazard/goal rewards alone, to navigate a walled grid to a hidden goal, with a live Q-value heatmap and policy arrows showing the route emerge.
- [2026-07-30 — Ant Colony Optimization](2026-07-30_ant-colony-optimization/) — four simulated ant colonies race along different-length paths to food, using pheromone deposition and evaporation to converge on the shortest route with no central planner.
- [2026-07-28 — Boids Flocking Simulation](2026-07-28_boids-flocking/) — emergent
  flocking behavior from three simple local rules (separation, alignment, cohesion).
