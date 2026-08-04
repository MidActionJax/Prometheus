# Add Q-Learning Grid World demo

## Summary

This adds a new pygame demo, `q_learning_gridworld.py`, that visualizes
tabular Q-learning: an agent with no map and no instructions learns, purely
from a running score (-1 per step, -20 for hitting a hazard, +50 for
reaching the goal), to navigate a walled grid to a hidden goal. This
round's topic comes from the **ML/AI** bucket. It was picked because
reinforcement learning hasn't appeared anywhere in the repo yet (the
existing demos cover supervised learning shapes like K-means/CNNs/feedforward
nets, or emergent-but-unlearned behavior like boids/ACO), and because a
live Q-value heatmap plus an emerging arrow-field policy is one of the
most visually satisfying ways to show "the agent is actually learning"
rather than just moving. It continues the series' mixed-bag rotation
across algorithms, ML, and simulation topics.

## What's included

- `q_learning_gridworld.py` — the runnable pygame demo: the grid-world
  environment, tabular Q-learning agent, training loop, and the rendering
  (heatmap, policy arrows, agent trail, HUD).
- `caption.txt` — the LinkedIn post copy for this demo.
- `HOW_TO_RUN.txt` — plain-language setup, run, recording, and posting
  instructions for Jax.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — the exact copy-paste git/GitHub commands to publish
  this demo.

## How it works

The environment is a 14x9 grid with two staggered wall segments (forcing an
S-shaped detour rather than a straight line), a two-cell hazard patch, a
fixed start cell, and a fixed goal cell. The agent can move up/down/left/
right; bumping a wall or the grid edge just wastes a step (it stays put).
Every (cell, action) pair has a learned "Q-value" stored in a table,
initialized to zero. Each step, the agent picks an action with an
epsilon-greedy rule: with probability epsilon it moves randomly (explore),
otherwise it takes whatever action currently has the highest Q-value from
its cell (exploit). After moving, it applies the core Q-learning update —
`Q(s,a) += alpha * (reward + gamma * max(Q(s', ·)) - Q(s,a))` — which nudges
its estimate for the action it just took toward the reward it actually got,
plus a discounted estimate of the best it can do from wherever it landed.
Because the goal has a large terminal reward and the hazard has a large
terminal penalty, those values "seed" the table at the goal/hazard cells
first, and then propagate backward, one Bellman update at a time, into
neighboring cells, then their neighbors, and so on — which is exactly why
the heatmap visibly "lights up" outward from the goal over the course of
training rather than appearing all at once. Epsilon decays after every
completed episode (`epsilon = max(0.05, 1.0 * 0.90^episode)`), so the agent
explores heavily at first and increasingly commits to its best-known route
as training progresses.

## Design choices

- **Palette**: cells are shaded on a 4-stop gradient (near-black indigo ->
  purple -> cyan -> bright gold) keyed to each cell's best current
  Q-value, matching the established neon-on-dark aesthetic while doubling
  as an actual data visualization (a real heatmap, not decoration).
- **Policy arrows**: a small white triangle is drawn in every visited,
  non-wall cell pointing toward its current best action. This turns an
  otherwise invisible data structure (the Q-table) into a live, readable
  "policy field" that visibly reorganizes as training proceeds — this is
  the single most important visual for teaching what Q-learning actually
  produces.
- **Hazard / goal markers**: the hazard pulses red, the goal pulses gold,
  both using a simple triangle-wave alpha/radius pulse so they stay
  noticeable without being distracting.
- **Agent trail**: the agent is drawn onto a persistent alpha surface that
  fades toward transparent each frame (the same trick used in the boids
  and ant-colony demos), cleared at the start of each new episode so every
  episode's path is easy to read on its own rather than smearing into the
  previous one.
- **HUD**: shows episode count, total steps trained, current epsilon, the
  most recently completed episode's length and reward, and the best
  (shortest successful) episode length seen so far — the "proof it's
  really learning" element, since that best-length number visibly drops
  over the course of a run.
- **Implementation note**: `GridWorld`, `QLearningAgent`, and
  `TrainingSession` are written with zero pygame calls anywhere in them;
  `main()` only reads their state to draw a frame. This mirrors the
  approach used in the ant-colony demo and is what made headless
  verification possible (see below).

## How it was verified

The sandbox this was built in has no network access (`pip install pygame`
fails with a proxy 403) and no display, so pygame itself could not be run
directly. Two fallback methods were used:

1. `python3 -m py_compile q_learning_gridworld.py` — passed, confirming the
   file is syntactically valid.
2. A throwaway test stubbed `pygame` in `sys.modules` with no-op fakes (so
   the file's `import pygame` and all rendering calls succeed harmlessly),
   then imported the real `TrainingSession` class and ran `tick()` for
   60,000 steps. Per-step assertions checked the agent's state always
   stayed in-bounds and out of walls, and that every stored Q-value stayed
   finite. Result: all checks passed — 3,146 episodes completed, 109 of the
   112 non-wall cells were visited, and the agent's best episode reached the
   goal in 16 steps. A BFS over the same wall layout confirmed 16 steps is
   the true shortest possible path (ignoring the hazard) — the agent found
   the actual optimum, not just *an* answer. A learning-trend check also
   confirmed the average length of its last 20% of episodes (17.0 steps)
   was meaningfully shorter than its first 20% (27.0 steps), i.e. the
   policy demonstrably improved over the run rather than staying flat. The
   throwaway test file was deleted after verification; only the five files
   listed above remain in this folder.

## What it teaches

Q-learning shows how an agent can learn a full multi-step decision policy
from nothing but scalar rewards and repeated experience — no map, no
labeled examples, no human demonstration of the "right" path. The core
mechanism (propagate value backward from outcomes via the Bellman
equation, balance exploring the unknown against exploiting what you've
already learned) is the direct ancestor of the reinforcement learning used
in game-playing AI, robotics control, and recommendation/ranking systems
that learn from user feedback over time.

## To do before posting

- [ ] Run it locally to confirm it looks right on your machine.
- [ ] Record a 10-20s clip (let it run 30-45s first so the policy has
      visibly organized, or speed up the clip in editing).
- [ ] Review caption.txt and tweak if anything doesn't sound like you.
- [ ] Post natively to LinkedIn with the video uploaded directly.
