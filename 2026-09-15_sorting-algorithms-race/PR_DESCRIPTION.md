# Add Sorting Algorithms Race demo

## Summary

This adds a new algorithms-bucket demo: Bubble Sort, Insertion Sort, and
Quicksort racing side by side against the exact same shuffled array,
each processing one comparison/swap at the same fixed rate. This round's
topic was picked to rebalance the series — algorithms had only 3 entries
(maze generation, Dijkstra's, convex hull) against 6 apiece for the
physics and ML/AI buckets, so this cycle went to algorithms. It also
directly answers one of the example topics called out for this bucket
("a sorting-algorithm bar-chart race") while avoiding the flat, unstyled
bar-chart look that's explicitly called out as a failure mode — bars
here are neon-gradient-colored by value, glow, leave particle bursts on
every swap, and glide (not snap) between positions.

## What's included

- `sorting_algorithms_race.py` — the runnable demo (pygame, single file).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — copy-paste git/GitHub commands to publish this demo.

## How it works

All three algorithms receive the same shuffled list of 24 unique values
at the start of each race, and each is expressed as a Python generator
that yields one decision at a time (`('compare', i, j)` or
`('swap', i, j)`) instead of running to completion instantly. A shared
driver pulls exactly one event per column at a fixed rate (30
operations/second), so the only thing that varies between columns is
how many events their algorithm actually needs to finish — not how fast
they're allowed to run.

- **Bubble Sort** repeatedly walks the array comparing each adjacent
  pair and swapping when they're out of order, with an early-exit flag
  if a full pass makes no swaps. Worst case: roughly n²/2 comparisons.
- **Insertion Sort** builds up a sorted prefix one element at a time,
  sliding each newly-considered value backward past everything larger
  than it until it finds its spot. Also roughly n²/2 comparisons worst
  case, though it tends to do noticeably less work than Bubble Sort on
  partially-ordered data because it stops sliding as soon as it finds
  the right spot instead of doing a full pass.
- **Quicksort** uses Lomuto partitioning: pick the last element as a
  pivot, walk the range once swapping anything smaller than the pivot
  into a growing "smaller" region on the left, then drop the pivot into
  its final resting place between the two regions and recurse on each
  half independently. That recursive halving is what gives it roughly
  n·log(n) comparisons on average — each recursive call only has to
  examine its own (shrinking) sub-range, not the whole array again.

Because all three run under the identical fixed decision-rate, the race
outcome is a direct, honest visualization of algorithmic complexity —
Quicksort doesn't "run faster," it simply needs to make far fewer
decisions to reach the same sorted result.

## Design choices

- **Color story**: every bar's color comes from a 5-stop neon gradient
  (deep blue -> cyan -> magenta -> orange -> gold) keyed to its value, so
  a fully-sorted column resolves into a smooth rainbow ramp — the value
  itself drives color, not just a flat per-column accent tint. This was
  the direct fix for the flagged "debug console" failure mode: instead
  of plain bars or printed numbers, the data itself has genuine color
  and glow (`glow_rect`, layered additive-blend surfaces per bar).
- **Motion over readouts**: comparisons trigger a bright white glow
  flash on the two bars involved; swaps fire a 9-particle spark burst at
  the swap location using gravity-affected, fading particles; sorted
  columns get a pulsing green frame and a "SORTED" badge. Text (the
  per-column comparisons/swaps/time HUD) is confined to three small
  lines at the top of each panel — a supporting element, never more than
  a small fraction of the screen.
- **Animation smoothness**: runs a real 60fps loop (`clock.tick(60)`).
  Bar positions are not snapped between array slots — each bar has a
  `visual_x` that exponentially eases toward its true (logical) array
  index every frame, decoupled from how fast the underlying algorithm is
  actually stepping. This means a bar mid-swap visibly slides across its
  neighbor rather than teleporting, regardless of the algorithm's pace.
- **Genuine layout variety**: earlier demos in this repo favor open-space
  particle/agent motion (gravity, boids, ant colony) or graph/point-cloud
  sweeps (Dijkstra, convex hull, maze). This one uses a three-panel
  grid-race layout instead — different composition, different color
  logic (data-value-driven rather than agent-state-driven), and a
  head-to-head structure none of the earlier entries use.

## How it was verified

The sandbox's shell tool was unavailable for this entire run (a known
"Windows update from September 8" mount failure affecting this
environment — confirmed by retrying the shell four times with the same
RPC mount error each time before stopping per the tool's own guidance).
That ruled out every execution-based verification path this run
normally uses: headless pygame via `SDL_VIDEODRIVER=dummy`,
`py_compile`, and a stubbed-GUI logic harness.

In place of that, the script got a careful manual/static review:
- A full line-by-line read for syntax issues (balanced brackets,
  consistent indentation, no stray references) — no issues found.
- A hand-traced dry run of the Quicksort generator against a concrete
  3-element example (`[3, 1, 2]`), tracking every yielded compare/swap
  event and the resulting array state at each step, confirming it
  terminates with `[1, 2, 3]` and the expected yields.
- Bubble Sort and Insertion Sort were checked against their textbook
  reference forms (early-exit optimization for Bubble Sort; backward-
  shift-until-in-place for Insertion Sort) and are structurally standard.
- Traced the animation/event-processing path (the `op_accum` fixed-rate
  step driver, particle lifecycle, compare-flash timer) for off-by-one
  and division-by-zero risks; none found (all denominators are
  compile-time constants).

This is a weaker guarantee than an actual run, so **please run it
locally first** (step 3 in `HOW_TO_RUN.txt`) before recording — flag
anything that looks off and it'll get fixed before the next round.

## What it teaches

Big-O notation describes how an algorithm's workload scales with input
size, not how fast any single run happens to feel — and the cleanest way
to see that is to force multiple algorithms to make decisions at exactly
the same rate and watch how many decisions each one needs. Bubble Sort
and Insertion Sort are both quadratic (O(n²)) in the worst case because
they reason about the array in small, local, repeated comparisons.
Quicksort's divide-and-conquer structure gets it down to O(n·log n) on
average by throwing away half the remaining problem with each partition
— though its worst case (bad pivot choices, e.g. already-sorted input)
degrades back to O(n²), which is why real-world implementations
randomize pivot selection or hybridize with another sort. This same
divide-and-conquer idea — solve smaller subproblems, combine the
results — is the backbone of merge sort, binary search, FFT, and much
of algorithm design generally.

## To do before posting

- [ ] Run the script locally to confirm it looks right on your machine
      (this run's verification was manual/static only — see above).
- [ ] Record a 10–20s clip (see `HOW_TO_RUN.txt` for recording steps).
- [ ] Review `caption.txt` and tweak if needed.
- [ ] Post natively (not as a link) using the caption above.
