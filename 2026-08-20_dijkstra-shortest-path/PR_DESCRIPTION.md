# Add Dijkstra's Shortest Path demo

## Summary

This demo visualizes Dijkstra's shortest-path algorithm running over a randomly generated weighted graph of 30 nodes, with edges relaxing and a "heat wavefront" of settled distances spreading outward from a source node in real time. It comes from the **algorithms bucket** — the rotation was slightly overdue for one, since the last several demos leaned ML/AI and physics. It's also a deliberately different visual take on "algorithms" than the two previous entries in that bucket (recursive-backtracking maze generation and ant colony optimization): instead of a grid maze or pheromone trails, this one uses a general node-link graph and a priority-queue-driven "wavefront," which reads more like a signal propagating through a network than a maze being carved. It continues the series' pattern of pairing a real, well-known algorithm with a genuinely different rendering style each time.

## What's included

- `dijkstra_shortest_path.py` — the runnable pygame demo (single file, well-commented, screen-record-ready).
- `caption.txt` — the LinkedIn caption for this post, following the confirmed hook / bridge / teaching-beats / closing-line / hashtags template.
- `HOW_TO_RUN.txt` — plain-language setup, run, controls, and screen-recording instructions for a non-developer.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — the exact git commands to branch, commit, and push this demo, plus PR/merge instructions.

## How it works

The graph itself is built in two layers so the algorithm actually has meaningful choices to make. First, 30 points are scattered across the canvas with minimum-distance rejection sampling so nodes don't overlap. Then a minimum spanning tree is built over those points using Prim's algorithm, which guarantees every node is reachable from every other node with the fewest possible edges. On top of that tree, each node gets 1–2 extra "shortcut" edges to its nearest neighbors that aren't already connected — these extra edges are what create alternate routes between nodes, which is what makes Dijkstra's core behavior (finding a *shorter* alternate path and overwriting a previous guess) visible at all. Without them, there'd only ever be one path to each node and nothing would ever need to "relax."

Dijkstra's algorithm itself works off a simple idea: maintain a "tentative distance" for every node (infinity until proven otherwise), and repeatedly settle whichever unsettled, reachable node currently has the smallest tentative distance — using a min-heap (priority queue) so that lookup is fast. Settling a node means its distance is now known to be final and can't improve. Every time a settled node checks its neighbors, if going through it produces a shorter distance than what that neighbor currently has on record, the neighbor's distance is updated and its "parent" pointer is set to the node that produced the improvement — that update is called a "relaxation," and it's the one operation the entire algorithm is built from. Because the algorithm always processes the globally-cheapest unsettled node next, once a node is settled its distance is provably final; no cheaper route to it can be discovered later. That greedy-but-provably-correct property is what makes Dijkstra's algorithm both fast and exact for graphs without negative edge weights.

The parent pointers collected along the way form a shortest-path tree rooted at the source: walking backward from any settled node through its parent chain traces the actual shortest route back to the source. Once every reachable node is settled, the demo picks the farthest one by distance and animates a comet-like particle retracing that path from source to target, using the same tree the algorithm built as it ran.

## Design choices

The color story is the centerpiece: every settled node is colored by a heat gradient (electric cyan → green → gold → hot magenta) mapped to its shortest distance from the source, so the wavefront of settling nodes visibly reads as "heat" spreading outward rather than as printed numbers. Nodes still waiting in the priority queue pulse in cyan (sine-wave alpha/size, eased continuously, not a hard blink) so you can see the "frontier" distinct from both unsettled gray nodes and finalized colored ones. Every relaxation triggers a bright white flash directly on the edge that fades and thins over ~380ms, and every settle triggers an expanding, fading ripple ring (eased outward with `ease_out_cubic`) colored to match that node's heat value — so key algorithm events are visual events, not text. The shortest-path tree itself is drawn as thicker glowing lines colored by each child node's heat value, layered under the flashes and ripples but over the faint gray background edges, so the growing tree structure is always visible without dominating the frame. All circular glows use the same additive-blend layered-circle technique as the earlier nbody and boids demos in this repo, so bright colors actually look like light rather than flat fills.

For motion: the whole thing runs on a real 60fps `clock.tick(60)` loop. The algorithm doesn't hard-cut between steps — it advances one settle every ~230ms on a timer, so relaxation flashes and ripples have room to animate independently of the step cadence. The final path-trace comet moves along the tree's actual polyline using arc-length parametrization (not just per-edge lerping, which would speed up and slow down inconsistently across long vs. short edges) and is eased with `ease_in_out_quad` so it accelerates into and decelerates out of the run rather than moving at constant linear speed, with a fading comet trail behind it. The HUD is a small translucent box in the top-left (settled count, relaxation count, frontier size, phase, elapsed time) — well under a third of the screen, consistent with the "supporting element, not centerpiece" requirement.

## How it was verified

1. `python3 -m py_compile dijkstra_shortest_path.py` — syntax check, passed.
2. Headless execution with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 dijkstra_shortest_path.py` — ran for 420 frames (the built-in headless frame cap) with no exceptions, exit code 0.
3. A second headless run with the frame cap temporarily raised to 1500 frames (~25 seconds of sim time) confirmed a full cycle through all four phases — SEARCHING → DONE → TRACING → HOLDING — including the automatic reset back into a fresh randomly generated graph, with no exceptions and no unbounded values. This also caught and fixed a real bug: a `ZeroDivisionError` in the heat-color calculation that occurred in the brief window right after the source node settles (before any other node has settled, `max_settled_dist()` is legitimately 0). Fixed by centralizing all heat-normalization math into one `heat_t()` helper that treats a zero or negative max distance as "closest" (0.0) instead of dividing by it.

## What it teaches

Dijkstra's algorithm is the classic solution to "find the cheapest path through a network," and it's the conceptual ancestor of the routing logic behind GPS navigation, internet packet routing (link-state protocols like OSPF), and flight/transit connection search — anywhere you need the truly cheapest path through a graph of weighted connections, not just any path. Its key insight — always greedily commit to the currently-cheapest option, and prove it's optimal by never revisiting a settled node — is also a foundational example of a greedy algorithm that happens to be provably correct, which makes it a useful mental model even outside pathfinding.

## To do before posting

- [ ] Run the script locally and confirm the window renders correctly.
- [ ] Record a 10–20 second clip (see HOW_TO_RUN.txt for suggested framing).
- [ ] Review caption.txt and lightly reword if needed for the posting context (LinkedIn group vs. own page).
- [ ] Post natively with the recorded video.
