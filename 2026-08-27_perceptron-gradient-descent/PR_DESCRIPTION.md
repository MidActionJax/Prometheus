# Add Gradient Descent Linear Separator demo

## Summary

This demo comes from the ML/AI bucket: it trains a single linear classifier
(the "perceptron" idea, run with a smooth logistic/sigmoid activation, i.e.
logistic regression) on a synthetic 2D dataset using gradient descent, and
renders the model's live confidence as a glowing color field rather than a
static scatter plot. It was picked this round because the series hadn't yet
shown the single most foundational training loop in ML — loss, gradient,
step, repeat — the same mechanism that scales up to today's largest neural
networks. It also directly follows up on the self-attention demo's feedback:
that one leaned too hard on plain text/lines and read as a debug console, so
this demo is built around a continuous, glowing visual field as the *primary*
visual element, with numbers relegated to a small corner HUD.

## What's included

- `perceptron_gradient_descent.py` — the runnable pygame demo (main script).
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language install/run/record instructions for Jax.
- `PR_DESCRIPTION.md` — this file.

## How it works

The dataset is two Gaussian point clouds in 2D (cyan = class 0, magenta =
class 1), generated with a bit of overlap so the model has real mistakes to
correct rather than a trivially perfect split. The model is a linear function
`z = w1*x + w2*y + b`, squashed through a sigmoid into a probability `p` that
a point belongs to class 1. Each frame, the training loop computes the binary
cross-entropy loss between `p` and the true labels, derives the gradient of
that loss with respect to `w1`, `w2`, and `b`, and moves each weight a small
step in the direction that reduces the loss (gradient *descent* — literally
descending the loss surface). Repeated over hundreds of frames, a randomly
initialized, badly-placed line converges to a genuinely good separator with
no hand-coded rule about where the boundary should sit.

The background "confidence field" is the same sigmoid function evaluated at
every point on a low-resolution grid covering the whole screen, then
upscaled — so the whole screen is effectively a live heatmap of "what does
the model currently believe about every possible point in this space,"
not just the labeled training points. The bright glowing seam is
mathematically exactly where `p = 0.5`, i.e. the decision boundary, and it
visibly slides and rotates as the weights update.

## Design choices

- **Color story**: cyan-to-magenta gradient mapped directly to the model's
  probability output, not printed numbers next to shapes. The seam glow
  intensity is a function of distance from the true 50/50 boundary, so the
  most visually prominent thing on screen is also the most information-dense
  thing (where the model is uncertain vs. confident).
- **Avoiding the "debug console" look**: no plain text scatter plot, no thin
  unstyled lines as the main visual. The boundary and the field are one
  continuous, glowing, actively-updating surface. The HUD is a small
  translucent rounded panel in the top-left corner (well under a third of
  the screen), showing epoch/loss/accuracy/weights as supporting detail only.
- **Motion**: points glow via additive-blended soft circles and gently pulse;
  misclassified points flash amber and fade back over several frames rather
  than snapping, so mistakes being corrected are visually legible. The field
  itself has a slow global pulse tied to a sine wave for a subtle "alive"
  feel even when training has momentarily plateaued.
- **Smoothness**: runs on a real `clock.tick(60)` loop; the field, points,
  and boundary all update every frame from continuously-changing weights
  (no hard-cut redraws), and the demo automatically reshuffles to a fresh
  dataset once converged so it loops naturally for repeated recording takes.

## How it was verified

Ran via `SDL_VIDEODRIVER=dummy` (headless SDL) with `event.get` monkey-patched
to feed synthetic frames instead of real input: executed the full `main()`
render + training loop for 300 frames with no exceptions, confirming both the
gradient descent math (numpy) and the pygame rendering path (field
computation, surfarray upscaling, glow blitting, HUD panel) run cleanly
end-to-end. Also ran `python3 -m py_compile perceptron_gradient_descent.py`
as a plain syntax check (passed). The throwaway headless test script was
deleted after verification; only the five required files remain in this
folder.

## What it teaches

Gradient descent is the workhorse optimization algorithm behind essentially
all of modern machine learning: define a loss function that measures how
wrong a model is, compute its gradient, and repeatedly nudge the model's
parameters opposite that gradient until the loss is minimized. This demo
shows that loop at its simplest — two weights and a bias — but the exact
same update rule (scaled up to billions of parameters via backpropagation)
is what trains today's neural networks, including large language models.

## To do before posting

- [ ] Run the script locally to confirm it looks right on your machine
- [ ] Record a 10-20s clip (Win+Alt+R or OBS)
- [ ] Review/tweak caption.txt if needed
- [ ] Post natively (video upload, not a link) using caption.txt
