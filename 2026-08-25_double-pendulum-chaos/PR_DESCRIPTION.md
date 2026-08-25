# Add Double Pendulum Chaos demo

## Summary

This adds a new demo, `double_pendulum_chaos.py`, from the **physics/simulations** bucket. Jax's series has leaned on physics only twice so far (N-body gravity, wave interference) against several algorithm and ML entries, so this round deliberately pulls from that bucket to keep it in regular rotation rather than an occasional treat. Double pendulums are one of the cleanest, most visually honest demonstrations of chaos theory available — a real, well-known physical system (not a toy example) that produces genuinely unpredictable motion from a textbook set of equations. It's a natural sibling to the N-body gravity demo (both show sensitive, chaotic dynamics with glowing trails) while looking and behaving nothing like it.

## What's included

- `double_pendulum_chaos.py` — the runnable demo: a fan of 7 double pendulums, released from nearly identical starting angles, visibly diverging over time.
- `caption.txt` — the LinkedIn caption for this post, following Jax's hook / bridge / teaching-beats / closer / hashtags template.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions for a non-developer.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — the exact git commands Jax runs locally to publish this demo.

## How it works

A double pendulum is a rod-and-mass pendulum with a second rod-and-mass hanging off the end of the first. A single pendulum's motion is simple harmonic-ish and totally predictable. Adding the second joint couples the two arms' motion through nonlinear equations, and that coupling is what turns a boring back-and-forth swing into a chaotic system: nearby starting states diverge from each other exponentially fast instead of staying close together.

The demo integrates the standard Lagrangian double-pendulum equations of motion — the same ones in any classical mechanics textbook — for two point masses (m1, m2) on massless rigid rods (L1, L2) under real gravity (g = 9.81 m/s²). Each pendulum's state is `(theta1, omega1, theta2, omega2)`: the two angles from vertical and their two angular velocities. Every frame, each pendulum's state is advanced with 4th-order Runge-Kutta (RK4) integration rather than simple Euler stepping, because double pendulums are numerically stiff near the bottom of each swing — Euler visibly leaks energy and drifts off the true trajectory, while RK4 keeps the simulated motion honest.

All seven pendulums share identical mass, rod length, and gravity — the only difference between them is their starting angle, offset from a shared base angle by tiny increments (as small as ~0.01 degrees by default). Because the system is chaotic, that vanishingly small initial difference gets amplified over time until the pendulums' outer bobs are swinging in completely unrelated directions. This is "sensitive dependence on initial conditions," the formal name for what's colloquially called the butterfly effect — and unlike a lot of pop-science explanations, this demo actually shows the mechanism rather than just asserting it.

## Design choices

- **Color story**: each of the 7 pendulums gets its own neon hue (cyan, electric blue, violet, magenta, orange, yellow, green) so the "family" of trajectories reads as a rainbow fan tearing apart rather than an indistinct blob. The outer (chaotic) bob's glow color additionally blends toward hot white as that pendulum's angular speed increases, so fast passes through the bottom of the swing visibly flare — mapping a physical quantity (kinetic energy / angular speed) directly to color and glow intensity rather than just printing a number.
- **Motion/trails**: only the outer bob's path is trailed (the inner bob mostly just hinges), using the same translucent fading-trail-surface technique as the N-body gravity demo — each frame the old frame is blitted at low alpha over a persistent surface so trails fade smoothly rather than being hard-cleared. Bob glow uses additive-blend (`BLEND_RGBA_ADD`) radial gradients, same family of technique as gravity but a different composition: pendulums fan out from one fixed pivot near the top of the screen instead of floating freely, which is the layout that makes "starting together, ending apart" legible at a glance.
- **HUD**: a small rounded box in the top-left corner (roughly 300x130px against a 1100x750 canvas, well under a third of the screen) shows elapsed time, step count, current starting-angle spread in degrees, and — the key "proof it's really chaos" stat — the live angular divergence in degrees between the first and last pendulum in the fan. This is a supporting element, not the visual centerpiece.
- **Smoothness**: real 60fps loop via `clock.tick(60)`, with 4 RK4 substeps per rendered frame for extra numerical stability without changing the visual frame rate. There's no discrete "step reveal" to animate here (unlike a graph algorithm) — the physics itself is already continuous motion, so the smoothness requirement is met by the integrator and render loop rather than by tweening between states.

## How it was verified

Two methods, both passing:

1. **Headless render run**: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 double_pendulum_chaos.py` — runs the real script through pygame's dummy video driver for its full 240-frame headless self-test loop (the same pattern used in `gravity_nbody.py`). Exited cleanly with code 0, no exceptions, no display required.
2. **Stubbed physics stress test**: pygame was stubbed out in `sys.modules` and the physics module (`derivs`, `rk4_step`, `Pendulum`, `make_fan`) was exercised directly for 3,000 integration steps x 4 starting-angle spreads (0.0002 to 0.2 rad) x 5 random base-angle seeds — 60,000 total pendulum-steps. Every angle, angular velocity, and derived pixel position was asserted finite (`math.isfinite`) after every step. Result: all 60,000 steps passed with no non-finite values; the largest angular-velocity-like state component observed was ~154 (bounded, no blow-up). The throwaway test script was removed after the run — only the five required files remain in this folder.

## What it teaches

Chaos theory is often summarized as "a butterfly flaps its wings and causes a hurricane," but that framing makes chaotic systems sound random or mystical. They're not — they're fully deterministic, governed by the same equations every time, but practically unpredictable past a short horizon because immeasurably small differences in starting conditions get amplified exponentially. This shows up anywhere engineers model real systems: weather forecasting loses accuracy past about two weeks for exactly this reason, robotic and orbital-mechanics simulations need to account for it, and it's a foundational concept in nonlinear dynamics and control theory.

## To do before posting

- [ ] Run the script locally to confirm it looks right on your machine
- [ ] Record a 10-20 second clip (see HOW_TO_RUN.txt for the best moment to capture)
- [ ] Review caption.txt, tweak if desired
- [ ] Post natively with the video attached
