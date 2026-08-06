# Prometheus

A collection of small, visual Python demos exploring AI, algorithms, and
software engineering concepts — built to be screen-recorded and shared.

Each demo lives in its own dated folder and includes:
- the runnable Python script
- `caption.txt` — the write-up used when posting
- `HOW_TO_RUN.txt` — plain-language setup and run instructions

## Demos

- [2026-08-06 — Self-Attention Visualization](2026-08-06_self-attention-visualization/) — the Transformer self-attention mechanism (softmax of scaled query-key dot products) rendered as glowing lines between sentence tokens, featuring a coreference example where "it" attends back to "cat".
- [2026-08-04 — Q-Learning Grid World](2026-08-04_q-learning-gridworld/) — a reinforcement-learning agent learns, from step-cost/hazard/goal rewards alone, to navigate a walled grid to a hidden goal, with a live Q-value heatmap and policy arrows showing the route emerge.
- [2026-07-30 — Ant Colony Optimization](2026-07-30_ant-colony-optimization/) — four simulated ant colonies race along different-length paths to food, using pheromone deposition and evaporation to converge on the shortest route with no central planner.
- [2026-07-28 — Boids Flocking Simulation](2026-07-28_boids-flocking/) — emergent
  flocking behavior from three simple local rules (separation, alignment, cohesion).
