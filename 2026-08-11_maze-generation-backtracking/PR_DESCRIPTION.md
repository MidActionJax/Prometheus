# Add Recursive Backtracking Maze Generation demo

## Summary

This adds a single-file pygame demo that generates a "perfect" maze live on screen using recursive backtracking (randomized depth-first search), then finishes by tracing the longest path inside the finished maze in gold. It comes from the **algorithms** bucket, which was last visited on 2026-07-30 (ant colony optimization) — the two most recent demos were ML and physics, so algorithms was due.

Topic fit: maze generation is one of the rare algorithms where the *process* is more visually interesting than the *result*. A growing, branching, colour-shifting tunnel network gives real motion and spectacle for the full run, and the underlying concept (DFS with an explicit stack, and the spanning-tree property that makes the maze perfect) has enough substance for genuine teaching beats. It also sits in the series as a natural companion to the earlier A*/BFS *solver* demos — this is the other half of that story, where the maze comes from rather than how it's solved.

## What's included

| File | Purpose |
|---|---|
| `maze_recursive_backtracking.py` | The demo. Single file, pygame only, heavily commented for on-screen reading while recording. |
| `caption.txt` | The LinkedIn caption — hook, mechanism, spanning-tree explanation, colour-mapping explanation, closing line, 6 hashtags. |
| `HOW_TO_RUN.txt` | Plain-language setup: install Python, `pip install pygame`, exact `cd` + run commands, controls, Game Bar / OBS recording steps, clip-length advice. |
| `PR_DESCRIPTION.md` | This file. |
| `GIT_COMMANDS.txt` | Copy-paste branch / commit / push commands plus PR + merge walkthrough. |

## How it works

**The generation algorithm.** The maze is a grid of `COLS x ROWS` cells with every wall initially intact. The generator keeps an explicit stack (rather than actual Python recursion, so it can be stepped one move at a time for animation) and a `visited` set. Each `step()` call does one of two things:

1. **Carve.** Look at the cell on top of the stack. Collect its in-bounds, *unvisited* neighbours. If there are any, pick one uniformly at random, record a link between the two cells (this is the "wall removal"), mark the neighbour visited, and push it onto the stack. The head moves forward.
2. **Backtrack.** If the top-of-stack cell has no unvisited neighbours, it's a dead end — pop it. The head retreats to the previous cell and tries again from there.

The algorithm terminates when the stack empties, which happens only after every reachable cell has been visited. Because the grid is fully connected, that's every cell, period.

**Why the maze is "perfect."** Every cell is pushed onto the stack exactly once, and every push is accompanied by exactly one carved link. So for N cells you end up with exactly N-1 links. A connected graph on N nodes with N-1 edges is, by definition, a tree — a **spanning tree** of the grid graph. Trees contain no cycles, so the finished maze has no loops, no isolated regions, and exactly one unique path between any two cells. This is not something the code checks or enforces; it's a structural consequence of "one new cell, one new corridor." The verification test asserts this property (`len(links) == N-1` plus a full connectivity flood) across 40 randomly seeded mazes.

**Bias note (worth knowing).** Randomized DFS produces mazes with a characteristic look: long, winding, low-branching corridors, because the search commits hard to one direction until it physically cannot continue. Other spanning-tree generators (Prim's, Kruskal's, Wilson's) produce visibly different textures from the same grid. That bias is exactly what the depth-to-hue colour mapping makes visible.

**The finale.** Once carving completes, the demo finds the maze's *diameter* — the longest shortest-path between any two cells — using the standard double-BFS trick that works on trees: run a breadth-first search from an arbitrary cell to find the farthest cell A, then run BFS again from A; the farthest cell from A is B, and A→B is a longest path in the tree. The maze dims and a gold comet sweeps that path on a loop. (This is deliberately a *tree property* showcase, not a repeat of the earlier BFS maze-solver demo — the point here is the structure that generation produced, not the act of solving.)

## Design choices

**Colour story.** Corridor hue is mapped directly to the recursion stack depth at the moment that corridor was carved (`depth_color()` walks HSV hue at 0.017 per level, starting at cyan). This isn't decoration — it makes the algorithm's core dynamic legible: long unbroken hue runs are the search burrowing deep, and abrupt hue reversals are it retreating out of a dead end. Every stroke on screen therefore carries data.

**No "debug console" surfaces.** The screen is dominated by glowing neon corridors on near-black navy. The stats HUD is a ~208px panel in the bottom-left corner (roughly 4% of screen area) and there are no bar charts, no dominant monospace text blocks, and no thin unstyled lines — corridors are 13px cores with two wider translucent halo passes underneath.

**Layered rendering for both looks and cost.** Four surfaces: a persistent `core` (solid strokes), a persistent `glow` (additively blended halos), a `trail` surface that self-fades via `BLEND_RGBA_SUB` each frame (giving the carve head its comet tail), and a per-frame `fx` layer for sparks, rings and the head bloom. Because the two maze layers are only ever appended to, a fully carved maze still costs two blits per frame — the frame rate doesn't degrade as the maze fills in.

**Smoothness.** Real `clock.tick(60)` loop with `dt` clamped at 50ms so a stutter can't teleport the simulation. The carve head is *tweened* between cell centres with a smoothstep ease (`t²(3-2t)`) rather than hard-cutting from cell to cell, and the corridor being carved is drawn growing toward the head each frame, so a new tunnel visibly extends rather than popping into existence. Backtracks fire an expanding pink ring pulse; carves throw 4 drag-damped sparks. Default speed is 33 moves/sec, which completes a 23×15 maze in roughly 20 seconds — matched to the target clip length — and is adjustable live with UP/DOWN.

**Distinct from prior demos.** Previous entries used free-floating particle motion (boids, N-body) or heatmap grids (Q-learning). This one is grid-locked, additive, and *accumulative* — the image builds up permanently instead of continuously moving, which is a genuinely different motion language for the feed.

## How it was verified

The sandbox running this task has no network access to PyPI, so pygame could not be installed and a headless `SDL_VIDEODRIVER=dummy` run was not possible. Verification instead used two methods:

1. **`python3 -m py_compile maze_recursive_backtracking.py`** — passed, no syntax errors.
2. **Stubbed-library test** — `pygame` was replaced with a `MagicMock` in `sys.modules` before import, then:
   - **Logic:** 40 independently seeded mazes generated to completion. For each: all 345 cells visited (`carved == 345`), exactly 344 links (spanning-tree property), full connectivity confirmed by an independent flood-fill from (0,0) reaching all 345 cells, and the returned diameter path validated edge-by-edge (every consecutive pair is orthogonally adjacent AND a real carved link). All 40 passed, zero exceptions.
   - **Render path:** the full `Visualizer` was driven for **2400 frames** (40 simulated seconds at 60fps) calling `update()` + `draw()` every frame, covering both the CARVING phase and the LONGEST PATH finale, plus a `reset()` and a further frame. No exceptions. End state: phase = LONGEST PATH, 345 cells carved, 345 backtracks, 230-cell longest path.

The throwaway test file was deleted; only the five intended files remain in the folder. The demo still needs a real local run on Jax's machine before recording (Step 3 in `HOW_TO_RUN.txt`) since actual pixel output could not be inspected here.

## What it teaches

Recursive backtracking is the clearest possible picture of how a depth-first search behaves: commit to a direction, exhaust it, unwind to the last decision point that still has options, continue. That "stack of unfinished decisions" pattern is the engine underneath maze solvers, Sudoku and N-Queens solvers, regex backtracking, SAT/constraint solvers, and package dependency resolution — anywhere a program has to explore a space of choices and be able to un-choose.

The second lesson is structural: enforcing "one new node, one new edge" is enough to guarantee a spanning tree, which in turn guarantees unique paths and no cycles. That's the same reasoning that underpins minimum spanning trees in network routing and clustering — a global property purchased entirely with a local rule.

## To do before posting

- [ ] Run it locally: `cd E:\Linkedin\2026-08-11_maze-generation-backtracking` then `python maze_recursive_backtracking.py`
- [ ] Confirm it looks right (colours, glow, HUD legible, gold finale fires)
- [ ] Record a 10-20s clip (Win+Alt+R, or OBS) — press `R` first for a clean start
- [ ] Read through `caption.txt` and reword lightly for the target audience/group
- [ ] Upload the video natively to LinkedIn and paste the caption
