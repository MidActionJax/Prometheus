# Add Convex Hull: Gift Wrapping (Jarvis March) demo

## Summary

This adds a new algorithms-bucket demo: an animated visualization of the
Gift Wrapping (Jarvis March) convex hull algorithm. This round's topic was
picked to rebalance the series — the last several posts leaned physics and
ML/AI, and algorithms hadn't had a new entry since Dijkstra's on 8/20.
Convex hull construction also offered a genuinely different visual style
from anything posted so far: a rotating radar-style search beam, rather
than a graph traversal, maze carve, or particle system. It fits the
ongoing series as another "watch the algorithm think" demo in the same
spirit as the Dijkstra and maze-generation posts, but with a distinct
geometric, sweep-based feel.

## What's included

- `convex_hull_gift_wrapping.py` — the runnable demo (pygame, single file).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — copy-paste git/GitHub commands to publish this demo.

## How it works

The convex hull of a set of points is the smallest convex polygon that
contains all of them — think of stretching a rubber band around every dot
and letting it snap taut. Gift Wrapping (Jarvis March) builds that polygon
one edge at a time, using a very simple geometric primitive: the cross
product.

Starting from the leftmost point (guaranteed to be on the hull), the
algorithm repeatedly asks: "of all the remaining points, which one has
every other point to its left?" It answers this by testing each candidate
against the current best guess with a cross product of the two vectors
`(best - current)` and `(candidate - current)`. The sign of that cross
product tells you which side of the line the candidate falls on — if the
new candidate is to the right of the line to the current best, it becomes
the new best, since it makes a "more clockwise" turn. After testing every
point, whichever one survived becomes the next hull vertex, and the
process repeats from there until the sweep returns to the starting point.
This is O(n·h) where h is the number of hull vertices — worse than the
O(n log n) of algorithms like Graham scan for large point sets, but its
step-by-step, one-decision-at-a-time nature is exactly what makes it easy
to animate and understand visually.

The demo layers a presentation choice on top of the raw algorithm: instead
of testing candidate points in arbitrary array order, it sorts them by
angle around the current hull vertex before testing, so the search beam
sweeps continuously in one rotational direction. This has zero effect on
the math (the winning point is the same regardless of test order — it's a
global extremum, not order-dependent), but it makes the "search" phase
read as a clean radar sweep instead of a chaotic scatter of lines.

## Design choices

- **Color story**: dim slate-blue for unclaimed points, bright cyan/teal
  for the active search beam, hot pink for the current best candidate,
  dim purple for rejected candidates (fading quickly), and a gold-to-cyan
  gradient for the confirmed hull polygon itself — so hull progress is
  immediately legible at a glance (gold = done, teal = actively searching,
  pink = "current leader").
- **Motion over readouts**: the actual spectacle is the rotating beam and
  the glowing polygon growing edge by edge — text is confined to a small
  bottom-left HUD (~15% of screen width) showing point/vertex counts,
  comparisons made, and elapsed time, never more than a supporting element.
- **Trail-fade technique**: like `boids_flocking.py` and
  `gravity_nbody.py`, the canvas is faded each frame via a low-alpha
  translucent overlay rather than hard-cleared, so the beam and rejected-
  candidate rays leave soft light trails. Confirmed hull edges are
  redrawn at full brightness every frame on top of the fade, so they stay
  crisp and permanent even as transient search rays fade out.
- **Animation smoothness**: runs a real 60fps loop (`clock.tick(60)`).
  The beam angle is not snapped between candidates — it's continuously
  lerped toward its target angle each frame. The sweep phase itself is
  eased in/out (smoothstep) rather than linear, and the final "commit"
  of a winning edge animates the edge growing from the current vertex to
  the winner over ~0.35s rather than popping in instantly.
- **Performance**: glow effects are drawn onto bounding-box-sized alpha
  surfaces (not full-canvas surfaces) per line/circle, which keeps the
  per-frame cost low even with dozens of glow elements on screen — this
  was tuned during verification after an early version was too slow for
  a smooth 60fps loop.

## How it was verified

- `python3 -m py_compile convex_hull_gift_wrapping.py` — syntax check, passed.
- Ran headless with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` for 3000
  simulated frames (~50 seconds of sim time) via a throwaway test harness
  that called the same `update()`/`draw()` methods the real main loop
  uses, with assertions that every point and hull vertex stayed finite
  and within canvas bounds every frame. Result: completed all 3000 frames
  with no exceptions, 3 full point-cloud resets, 23 hull edges committed
  across those resets, 762 candidate comparisons performed, final hull
  size 7 vertices — all coordinates finite throughout. The throwaway test
  harness was deleted after verification; only the five deliverable files
  remain in this folder.

## What it teaches

Convex hulls are a foundational computational geometry primitive: the
"tightest wrapping" shape around a point set. They show up in collision
detection for games and robotics (approximating an object's outer boundary
cheaply), in GPS/mapping (bounding a set of location pings), and as a
building block for more advanced structures like Delaunay triangulations
and Voronoi diagrams. Gift Wrapping specifically is a good first algorithm
to learn in this space because its logic reduces to one simple geometric
test (the cross product) repeated many times — the same primitive shows
up throughout computational geometry.

## To do before posting

- [ ] Run the script locally to confirm it looks right on your machine.
- [ ] Record a 10–20s clip (see `HOW_TO_RUN.txt` for recording steps).
- [ ] Review `caption.txt` and tweak if needed.
- [ ] Post natively (not as a link) using the caption above.
