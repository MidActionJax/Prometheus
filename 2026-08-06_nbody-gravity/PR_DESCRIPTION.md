# Add N-Body Gravity Simulation demo

## Summary
This demo simulates true N-body gravity: a set of bodies (one heavy "sun" plus several lighter bodies) that all pull on each other simultaneously via Newton's law of gravitation, with no scripted paths. It's a simulations/physics-bucket pick, chosen specifically to be a visually strong follow-up after the self-attention visualization landed as too text/dashboard-heavy — gravity sims are one of the most naturally satisfying things to watch, since glowing bodies with fading trails produce a good-looking result almost by construction, while still teaching a real, well-defined physics/CS concept (numerical simulation of a chaotic system).

## What's included
- `gravity_nbody.py` — the tested pygame simulation.
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions.
- `PR_DESCRIPTION.md` — this file.

## How it works
Each `Body` tracks position, velocity, and mass. On every frame, `apply_gravity_from` computes the gravitational force between the body and every other body in the system using `F = G * m1 * m2 / r²`, sums those forces into a net acceleration, and integrates it into the body's velocity (semi-implicit Euler integration). A small softening constant is added to the squared distance term so that when two bodies pass very close to each other, the force doesn't spike toward infinity and blow up the simulation (a classic numerical-stability issue in naive N-body code). The system starts with one heavy central body and several lighter bodies given a rough tangential velocity so they begin in quasi-circular orbits — but because there are more than two bodies, there's no exact closed-form solution (the "three-body problem" and beyond), so the paths drift and become genuinely chaotic within seconds. Clicking adds a new body with a random velocity, which gets pulled into the existing system's gravity well and visibly perturbs the other orbits.

## Design choices
- **Color story**: each body gets a distinct neon color from a fixed palette (cyan, magenta, yellow, green, violet, orange, electric blue) so a system with 7+ bodies reads as colorful and distinguishable, not monochrome.
- **Glow effect**: since pygame has no built-in bloom/glow, each body is drawn with several layered, increasingly-large, increasingly-transparent circles blended additively (`BLEND_RGBA_ADD`) underneath the solid body, faking a soft glow — this was a deliberate fix for the "debug console" look flagged on the previous demo.
- **Speed-based flare**: a body's color blends toward hot white as its speed increases (`glow_color`), so close, fast gravitational passes visually "flare" rather than just being a number in a HUD.
- **Trails**: a translucent trail surface is redrawn over the previous frame each tick (same technique as `boids_flocking.py`) instead of a hard clear, which is what produces the long, fading orbital trails rather than a static picture.
- **HUD**: kept deliberately small — a semi-transparent rounded box in the top-left corner with body count, average speed, and elapsed time, plus a one-line control hint at the bottom. It occupies a small fraction of the screen so the moving, glowing bodies stay the visual focus.

## How it was verified
1. `python -m py_compile gravity_nbody.py` — passed, no syntax errors.
2. A throwaway logic test stubbed `pygame` in `sys.modules` and ran the physics loop (gravity + integration, no rendering) for 600 frames with 7-8 bodies, asserting every position and velocity stayed finite (no NaN/Inf from a close encounter). Result: 600 frames completed with no exceptions and no non-finite values; final average body speed was a stable, sane ~152 units/sec. The throwaway test file was deleted after running.

## What it teaches
N-body gravity is a foundational simulation problem in physics and computer science: it's how planetary systems, galaxy formation, and orbital mechanics get modeled computationally, and it's a classic example of deterministic chaos — a fully deterministic system (same rules every run) whose outcomes are still practically unpredictable because of extreme sensitivity to starting conditions.

## To do before posting
- [ ] Run `gravity_nbody.py` locally and confirm it looks good on your machine
- [ ] Record a 10-20s clip (let trails build up for a few seconds, then click to add a body)
- [ ] Review `caption.txt`, tweak the hook line per-group if posting to multiple groups
- [ ] Post natively (not as a link) with the caption
