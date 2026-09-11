# Add Decision Tree Growth demo

## Summary

This is a new demo in the ML/AI bucket: a CART decision tree learning to
classify a 2D checkerboard dataset, animated one axis-aligned split at a
time. This round specifically targeted the ML/AI bucket because the last
several posts skewed heavily toward physics (spring-mass-damper, elastic
gas, double pendulum) with only one ML post (perceptron/gradient descent)
in between — this keeps the "mixed bag" rotation genuinely balanced rather
than letting one bucket dominate. Decision trees were also a clean fit for
the visual-richness bar: unlike a flat readout of numbers, a tree's greedy
splitting process maps naturally onto a literal, watchable carving-up of
colored 2D space, which is exactly the kind of "actual motion and spectacle"
the series aims for.

## What's included

- `decision_tree_growth.py` — the runnable pygame demo; builds a full CART
  tree up front, then animates its construction split-by-split.
- `caption.txt` — the LinkedIn post copy for this demo.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — exact git/GitHub commands to publish this demo.

## How it works

The dataset is a 3x3 checkerboard: the unit square is divided into 9 cells,
alternating between two classes, and ~18 jittered points are sampled inside
each cell (162 points total), with 5% of points given a deliberately flipped
label to simulate real-world label noise. This is a deliberately hard case
for a tree: a single split along one axis alone doesn't cleanly separate the
classes, so the tree has to compound several splits to approximate the
pattern.

The core algorithm is CART (Classification and Regression Tree) with Gini
impurity as the splitting criterion: `Gini = 1 - p0^2 - p1^2`, where p0/p1
are the class fractions in a node. Zero means the node is pure (one class
only); 0.5 means maximally mixed. For every node, the script tries every
candidate threshold on both the x and y axis, computes the weighted average
Gini of the resulting two children, and picks whichever split reduces
impurity the most versus the parent. This repeats recursively on each child
until a node hits `MAX_DEPTH` (4), gets too pure to bother (`purity >= 0.97`),
or has too few points left to split (`MIN_LEAF = 6` per side). This greedy,
one-step-at-a-time strategy — never looking further ahead than the
immediate best split — is exactly what real-world decision tree
implementations (scikit-learn's `DecisionTreeClassifier`, and by extension
random forests and gradient boosting) do under the hood.

The full tree is actually built before the animation starts (so the
"performance" you see is a faithful replay of a real completed model, not a
scripted fake), then replayed split-by-split in breadth-first (level) order
— shallow, high-impact splits appear before deeper, finer ones, matching
the order the algorithm actually reasons about the data.

## Design choices

- **Color story**: every revealed region is filled with a color blended
  between class-A cyan and class-B magenta based on that region's class
  mix, and the fill's *opacity* scales with purity — mixed/impure regions
  stay dim and desaturated, while pure regions glow vividly. This maps the
  actual Gini impurity value directly onto what you see, rather than
  printing it as a number.
- **Motion over readout**: the centerpiece is the glowing gold split line
  that sweeps into place (eased, not an instant cut) each time the tree
  makes a decision, followed by a soft crossfade as the two new child
  regions fade in over their parent. Data points glow via layered
  translucent circles (additive-style falloff), and points the current
  partial tree still gets wrong carry a thin pulsing gold ring — a
  live "error signal" that visibly shrinks as splits land.
- **Supporting HUD, not dominant**: the only plain-text elements are a
  small stats panel (splits made, depth, active leaves, live accuracy) and
  a compact mini tree diagram that grows new glowing nodes/edges in sync
  with the main animation — together they occupy well under a third of the
  screen, in the bottom/side margins rather than the center.
- **Smoothness**: runs a real 60fps `clock.tick(60)` loop; every split line
  grows via an eased (`ease_out_cubic`) sweep rather than snapping in, and
  every new region fades in via the same eased alpha ramp rather than a
  hard cut — consistent with the animation-polish bar set by
  `gravity_nbody.py`.
- **Genuine topic variety**: this is a fill/carve/mosaic visual built from
  translucent rectangles and a graph diagram — a different technique from
  the particle-trail approach used in the physics demos and the prior
  boids/ant-colony/gravity demos, so the series keeps looking varied.

## How it was verified

**Important environment note:** the sandbox's shell tool was completely
unavailable this run — every `bash` call failed with a workspace mount/RPC
error ("failed to mount ... outputs ... Bash has now failed 5 times in a
row ... workspace appears wedged"), even after multiple retries and a wait.
This blocked all three of the usual verification paths (headless
`SDL_VIDEODRIVER=dummy` run, `py_compile`, and a stubbed-GUI logic test) —
none of them could be executed.

In place of execution, I did a full manual line-by-line trace of the script
instead: verified bracket/indentation balance, traced the coordinate-mapping
math (`data_to_plane`, including the y-axis flip) to confirm every rectangle
and split-line endpoint produces positive, in-bounds width/height, traced
the BFS event ordering against the animation state machine, and traced the
point-to-leaf path assignment logic used by both the live-accuracy stat and
the misclassification rings. This review surfaced and fixed two real bugs
before they could ship: (1) a potential `IndexError` crash if a randomly
generated dataset ever produced a tree with zero valid splits (now guarded
— falls straight to the end-hold/restart phase instead), and (2) the plane
border being drawn before the glow-layer blit, which let the root node's
full-opacity wash paint over and dim it (reordered so the border is crisp
on top).

I was not able to confirm the script executes cleanly end-to-end this run.
**Please run it locally per HOW_TO_RUN.txt before recording** — if pygame
surfaces anything my manual review missed, flag it and I'll fix it in a
follow-up commit.

## What it teaches

Decision trees are one of the most widely used and most interpretable model
families in ML — and the building block behind ensemble methods like random
forests and gradient-boosted trees (XGBoost, LightGBM) that power a huge
share of real-world tabular-data systems (credit scoring, fraud detection,
recommendation ranking, and more). The core idea — greedily pick the split
that most reduces impurity, repeat — is simple enough to fit in a few lines
of code, yet it's genuinely how production-grade tree models are trained.
Watching it run also makes the model's real limitation visible: because
every cut is a straight line, trees approximate curved or diagonal patterns
as a staircase of rectangles, which is exactly why ensembles of many trees
(rather than one deep tree) tend to generalize better in practice.

## To do before posting

- [ ] Run `python decision_tree_growth.py` locally to confirm it launches
      and animates as expected (see verification note above).
- [ ] Record a 10–20s clip (see HOW_TO_RUN.txt for a suggested window).
- [ ] Review/trim caption.txt to taste.
- [ ] Post natively with the video + caption.
