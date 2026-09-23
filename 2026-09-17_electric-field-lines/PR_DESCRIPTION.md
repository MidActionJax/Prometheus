# Add Electric Field Lines & Coulomb's Law demo

## Summary
This demo is this round's pick from the physics/simulations bucket, chosen specifically to keep physics in regular rotation rather than letting it lag behind the AI/ML and algorithms buckets (the last three posts were spring-mass-damper resonance, decision tree growth, and a sorting-algorithm race — physics was due). It visualizes electrostatic field lines from point charges via Coulomb's law and superposition, then adds a stream of small charged test particles that feel the real force and get pushed/pulled through that field — combining a classic "field diagram" with genuine kinetic motion so it reads as alive rather than a static physics-textbook picture.

## What's included
- `electric_field_lines.py` — the tested pygame simulation.
- `caption.txt` — the LinkedIn caption for this post.
- `HOW_TO_RUN.txt` — plain-language setup, run, and recording instructions.
- `PR_DESCRIPTION.md` — this file.

## How it works
Every charge in the scene is a `Charge` with a position and a signed magnitude (positive = magenta, negative = cyan). `field_at(x, y, charges)` computes the electric field vector at any point by summing Coulomb's law, `E = k*q / r^2`, over every charge — this superposition (just adding up each charge's individual contribution) is the entire "physics engine"; there's no separate field equation being solved anywhere. Field LINES are traced by `trace_field_line`: starting just outside a positive charge, it repeatedly asks `field_at` which way the field points right here, takes a small step in that direction, and repeats — the line ends either because it wanders within `ABSORB_RADIUS` of a negative charge (captured) or leaves the screen (field lines technically extend to infinity, so this is just where we stop drawing). Test PARTICLES use the same `field_at` function but turn the field into an actual force (`F = q*E`), then integrate that into velocity and position with light damping so they don't accelerate to infinity near a charge — this is what makes the particles swing and curve around charges instead of snapping directly onto a field line the way the static geometry would suggest.

## Design choices
- **Color story**: field strength is mapped on a *log* scale (since Coulomb's law falls off as 1/r², a linear map would make almost the entire line look "weak") through a five-stop gradient from near-invisible indigo, through violet and hot magenta-pink, up to warm white-gold right next to a charge — so field intensity is something you see, not something printed as a number.
- **Motion over diagram**: rather than a static field-line poster (the "debug console" failure mode flagged on an earlier demo), each line carries a small bright pulse dot that travels along its length continuously, and ~90 glowing gold test particles constantly flow through the scene with fading trails (same translucent-trail-surface technique as `gravity_nbody.py` and `boids_flocking.py`), so there's always real movement to watch even when no charge has been added recently.
- **Glow**: charges and particles are both drawn with layered, shrinking, increasingly transparent circles blended additively (`BLEND_RGBA_ADD`), the same faux-bloom technique used in the N-body demo, so the whole scene reads as neon rather than flat vector shapes.
- **HUD**: a small semi-transparent box in the top-left with charge count, active field-line count, and elapsed time, plus a one-line control hint at the bottom — well under a third of the screen, so the glowing field and particle flow stay the visual focus.
- **Interactivity**: left/right click add positive/negative charges live, immediately re-tracing all field lines around the new layout, which is the clearest way to *show* superposition — the whole field visibly reshapes the instant a new charge lands.

## How it was verified
1. `python3 -m py_compile electric_field_lines.py` — passed, no syntax errors.
2. Full headless run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 electric_field_lines.py` ran the complete script (real pygame, dummy display driver) for its built-in 240-frame headless self-test with no exceptions and a clean exit.
3. A throwaway logic test stubbed `pygame` in `sys.modules`, built the default charge layout plus two extra clicked-in charges, traced field lines, then ran 90 particles through 800 update steps of the real force/integration code. Result: 60 field lines traced, all 800 steps completed with no exceptions, every particle position and velocity stayed finite and in-bounds, and the speed cap was respected throughout (sample final speeds ~7-30 units/sec). The throwaway test file was deleted after running.

## What it teaches
Coulomb's law (`F = k*q1*q2/r²`) is the electrostatic analog of Newton's gravitation — same inverse-square shape, but charge's two signs mean the force can repel as well as attract. Superposition — the idea that the total field from many charges is just the sum of each charge's individual field — is what lets a handful of simple pairwise calculations produce the complex, curving field patterns seen around real capacitors, ion traps, and lightning strikes.

## To do before posting
- [ ] Run `electric_field_lines.py` locally and confirm it looks good on your machine
- [ ] Record a 10-20s clip (let the default field settle, then click to add a charge and watch it reshape)
- [ ] Review `caption.txt`, tweak the hook line per-group if posting to multiple groups
- [ ] Post natively (not as a link) with the caption
