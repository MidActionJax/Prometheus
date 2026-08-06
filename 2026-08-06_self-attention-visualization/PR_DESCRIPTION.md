# Add Self-Attention Visualization demo

## Summary

This is the biweekly Prometheus demo: a visualization of self-attention, the
mechanism at the core of every Transformer model (GPT, BERT, Claude,
included). It comes from the ML/AI bucket — the last two demos (ant colony
optimization, Q-learning grid world) leaned on agent-based simulation and
heatmaps, so this round intentionally goes in a different visual direction:
text tokens, glowing connection lines, and a live bar chart, rather than
particles or grids. It's also a topic that's currently top-of-mind for a lot
of the audience (everyone's heard "attention" and "Transformers" but fewer
people have seen the actual score → softmax → weighted-focus mechanic laid
out visually), which makes it a strong teaching fit for the series.

## What's included

- `self_attention.py` — the runnable pygame demo (single file, well-commented).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup, run, and screen-recording instructions.
- `PR_DESCRIPTION.md` — this file.

## How it works

The demo shows the sentence "The cat sat on the mat because it was tired,"
with each word rendered as a glowing box. Every word gets two vectors: a
**key** vector (a fixed representation of what that word "contains") and a
**query** vector (what that word is currently "looking for" in the rest of
the sentence). For a given query word, the demo takes the dot product of
its query vector against every other word's key vector, scales the result,
and runs it through softmax — this is literally `attention(Q, K) =
softmax(Q · Kᵀ / √d)`, the real formula used inside Transformer attention
layers. The output is a set of weights that sum to 1, one per word,
representing how much the query word "attends to" each other word. Those
weights are drawn as glowing lines (brighter and thicker = higher weight)
and as a small bar chart underneath the sentence.

Most words' query vectors are built mostly from their own key vector plus a
small amount of their immediate left/right neighbor — a simple stand-in for
"words mostly care about themselves and nearby context," which is why most
steps in the demo show a word attending mostly to itself. The interesting
exception, and the whole point of the demo, is the pronoun "it": its query
vector is deliberately built as a blend of "cat"'s and "mat"'s key vectors
(60%/40%), so when the demo's rotating spotlight lands on "it," the glow
visibly jumps away from itself and over to "cat" (and, to a lesser extent,
"mat"). That's a simplified stand-in for coreference resolution — the real
task of figuring out what a pronoun refers to — which trained attention
heads in real language models learn to do from data. "tired" gets a
smaller nudge toward "cat" for the same reason (it's describing the cat).
None of this is a trained model; the vectors are small, fixed, hand-seeded,
and in two cases hand-shaped specifically to make the mechanism legible on
camera. The math applied to them (dot product, scaling, softmax) is exactly
the real attention computation.

## Design choices

Visual style deliberately breaks from the last few demos' look (particle
trails, heatmaps) since the concept is symbolic/relational rather than
physical. Dark navy background, a two-stop cyan → yellow gradient for
attention weight (dim cyan for near-zero, bright yellow for high),
consistent with the channel's neon aesthetic but distinct in application —
the "glow" is a line/box brightness gradient rather than particle color.
The currently active query word gets a pulsing yellow border (sine wave)
so it's unambiguous which word is "asking the question" at any moment.

Smoothness: full 60fps loop via `clock.tick(60)`. Rather than hard-cutting
between query words, every weight change is tweened over 0.6 seconds with
an ease-in-out cubic curve (`ease_in_out_cubic`), so lines fade/brighten and
bars grow/shrink smoothly rather than snapping — directly following the
guidance to animate step-based transitions instead of instant reveals. A
translucent per-frame surface (`pygame.SRCALPHA`) is used for the glow
lines (two passes per line — a soft wide outer glow plus a brighter core)
for a genuine glow effect; the background itself is a plain redraw each
frame rather than a fading trail, since this is a discrete relational graph
rather than continuous physical motion, so a motion trail wouldn't map to
anything meaningful here — tweening does the smoothness work instead.

## How it was verified

The sandbox this ran in has no network route to PyPI, so `pip install
pygame` failed and a headless `SDL_VIDEODRIVER=dummy` run wasn't possible.
Verification used the two-part fallback:

1. `python3 -m py_compile self_attention.py` — passed, no syntax errors.
2. A throwaway test script stubbed `pygame` in `sys.modules` (so the module
   imports cleanly without the real library) and exercised all of the pure
   logic directly: built the key/query vectors, ran `compute_attention` for
   every token 50 times (500 total attention computations) checking that
   weights always sum to 1 and stay in [0, 1], and that entropy stays in
   valid bounds; confirmed "The" and "the" share an identical key vector;
   confirmed every non-"it" token attends most to itself (baseline sanity);
   confirmed "it" attends most to "cat" with weight 0.34 (comfortably above
   the next-highest, "mat" at 0.16); then ran the full tween/hold state
   machine for 1,500 simulated frames (25 seconds at 60fps), checking every
   frame's eased interpolation value, weight bounds, and color mapping for
   exceptions. Result: all checks passed, 11 query-token transitions
   observed across the simulated run, no exceptions. The throwaway test
   file was discarded after the run — only the five deliverable files ship.

## What it teaches

Self-attention is the mechanism that lets a model weigh which other words
in a sentence matter for understanding a given word — instead of only ever
looking at fixed neighboring words, it can reach anywhere in the sequence
with a learned, data-dependent weighting. This is why Transformer models
are good at long-range dependencies and ambiguity (like figuring out what
"it" refers to several words later), and it's the same core computation
that scales up — across many heads and many layers — into the attention
patterns behind GPT, BERT, and Claude. Understanding this one small
computation is genuinely most of the way to understanding how modern LLMs
process context.

## To do before posting

- [ ] Run `self_attention.py` locally to confirm it looks right on your machine.
- [ ] Record a 10–20s clip (see HOW_TO_RUN.txt) — capture at least one full
      transition into "it" so the coreference jump is visible.
- [ ] Review caption.txt, tweak if needed for the specific posting context (group vs. page).
- [ ] Post natively with the video attached.
