# Add 0/1 Knapsack Dynamic Programming demo

## Summary

This is the biweekly demo for 2026-09-22: an animated visualization of the
0/1 knapsack problem solved via dynamic programming. It comes from the
**algorithms bucket**. The last two posts leaned physics (electric field
lines) and algorithms (sorting race), and the topic list was checked
against every existing dated folder in the repo to make sure nothing
overlapped — knapsack/DP hadn't been covered yet, and it's explicitly
called out in the demo brief as a good "DP table filling in live" example.
It's also a strong visual fit: a 2D grid lends itself naturally to a
heatmap-style glow, which lines up with the series' aesthetic (see
`nbody-gravity` and `boids-flocking` for the established visual language
this continues).

## What's included

- `knapsack_dp.py` — the runnable pygame demo (single file, no exotic deps).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup/run/record instructions for Jax.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — exact copy-paste git/GitHub commands to publish this demo.

## How it works

The 0/1 knapsack problem asks: given a set of items, each with a weight
and a value, and a knapsack with a fixed weight capacity, which subset of
items maximizes total value without exceeding capacity? "0/1" means each
item is either fully taken or fully left behind — no partial items, which
is what makes this harder than the simpler "fractional knapsack" (which a
greedy algorithm can solve directly).

Trying every subset is O(2^n) — intractable once you have more than ~25
items. Dynamic programming instead builds a table `dp[i][w]`, where each
cell answers: "using only the first `i` items, what's the best total value
achievable with a knapsack of capacity `w`?" Every cell depends only on
cells that come before it in the fill order (fewer items considered, and/or
less capacity), so by filling the table in order — one row per item, left
to right across capacities — every answer is available exactly when it's
needed. The recurrence is a single comparison per cell:

- **Skip** item `i`: the answer is whatever was already best using `i-1`
  items at the same capacity `w`.
- **Take** item `i` (only possible if it fits, i.e. `weight[i] <= w`): the
  answer is that item's value plus the best answer using `i-1` items at
  the *reduced* capacity `w - weight[i]`.

Take whichever of those two is larger, and store which choice won. Repeat
for every `(i, w)` pair. The bottom-right cell, `dp[n][W]`, ends up holding
the true optimal value — guaranteed, not approximated, because every
possible combination is implicitly represented in the table.

Once the table is complete, **backtracking** reconstructs the actual items
chosen (not just the optimal value) by walking from `dp[n][W]` backward:
at each step, if `dp[i][w]` differs from `dp[i-1][w]`, item `i` must have
been taken, so the demo marks it and moves diagonally back by that item's
weight; otherwise it moves straight up (item `i` was skipped). This costs
only O(n) extra work — the table already did the hard part.

## Design choices

- **Color story**: rather than printing raw numbers, every filled cell's
  glow color is interpolated from a dim blue (low achievable value) to hot
  magenta/white (near the theoretical maximum value, i.e. the sum of every
  item's value) — data intensity (the DP value) is directly mapped to
  color and glow brightness, per the series' visual bar.
- **Additive persistent glow layer**: cells are stamped onto a separate
  `SRCALPHA` surface using `BLEND_RGBA_ADD` and gently faded each frame,
  so the grid builds up a warm "still glowing" look rather than a flat,
  static heatmap — closer to the trail technique used in
  `gravity_nbody.py`/`boids_flocking.py` than a plain bar chart.
- **Smooth cursor motion**: the active-cell cursor doesn't jump cell to
  cell; its position is linearly interpolated between the previous and
  current cell and passed through a smoothstep ease-in-out curve each
  frame, at a real 60fps clock tick, so the sweep reads as continuous
  motion rather than a series of hard cuts.
- **Backtrace as a glowing trail, not a table dump**: the reconstructed
  path is drawn as a continuous glowing gold line with additive blending,
  animated one step at a time (slower cadence than the fill, for drama),
  rather than just printing which items were chosen.
- **HUD kept small and secondary**: a compact translucent panel in the
  top-right corner shows fill progress and the running/optimal value —
  it occupies a small fraction of the screen, with the grid and item
  panel doing the visual heavy lifting, avoiding a "debug console" look.
- **Item panel doubles as a legend**: each item's bar is colored with a
  distinct neon hue, bar length maps to value, and taken items get a
  white outline + glow flash when selected during backtrace — tying the
  abstract grid back to concrete, identifiable items.

## How it was verified

- `python3 -m py_compile knapsack_dp.py` — passed, no syntax errors.
- Headless execution: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 12 python3 knapsack_dp.py` — pygame initialized, the window/render loop ran continuously for the full 12-second window with no exceptions, and was terminated cleanly by `timeout` (exit code 124, the expected "still running" signal). This confirms the full DP fill, backtrace, and auto-restart logic executes without errors across multiple frames and phase transitions.

## What it teaches

Dynamic programming is one of the most widely applicable techniques in
computer science: whenever a problem has overlapping subproblems and
optimal substructure (the best solution to the whole is built from best
solutions to its pieces), building a table once and reusing it beats
recomputation every time. The same pattern underlies real-world systems
like sequence alignment in bioinformatics, shortest-path routing, text
diffing (e.g. `git diff`), and resource-allocation problems in logistics
and finance — anywhere "pick the best combination under a constraint"
shows up.

## To do before posting

- [ ] Run `knapsack_dp.py` locally to confirm it looks right on your machine.
- [ ] Record a 10-20 second clip (see `HOW_TO_RUN.txt`).
- [ ] Review `caption.txt` and tweak if needed.
- [ ] Post natively with the video + caption.
