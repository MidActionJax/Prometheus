# Add Spring-Mass-Damper: Damping & Resonance demo

## Summary

This is the biweekly demo for 2026-09-08, drawn from the **physics** bucket.
Physics has been getting real, regular rotation in this series (N-body
gravity, wave interference, double pendulum, elastic gas thermalization),
and this round continues that with a topic that hasn't been touched yet:
the damped harmonic oscillator, shown both as an everyday mechanical
picture (a spring and a mass) and as the abstract signal it produces
(a scrolling x(t) trace). It was picked because it has an unusually clean
teaching hook — one governing equation, one parameter (the damping ratio
zeta) controls three very different, very recognizable real-world
behaviors — and because a "resonance building up live" moment is genuinely
dramatic to watch, similar to how the N-body sim's close encounters read
as dramatic.

## What's included

- `spring_mass_damper.py` — the runnable demo. Four damped-harmonic-
  oscillator lanes (underdamped, critically damped, overdamped, and a
  continuously driven/resonant lane), each rendered as a glowing coil
  spring plus a glowing scrolling oscilloscope trace.
- `caption.txt` — the LinkedIn post write-up (hook, what was built, the
  teaching beats, closing line, hashtags).
- `HOW_TO_RUN.txt` — plain-language install/run/record/post instructions
  for Jax.
- `PR_DESCRIPTION.md` — this file.
- `GIT_COMMANDS.txt` — the exact copy-paste git/GitHub commands to publish
  this demo.

## How it works

Each lane is an independent numerical solution to the classic damped
(and optionally driven) harmonic oscillator: `m*x'' + c*x' + k*x = F(t)`.
`x` is displacement from equilibrium, `m` is mass, `k` is the spring's
stiffness (Hooke's law: force pulls back toward equilibrium proportional
to displacement), and `c` is the damping coefficient (a drag force
proportional to velocity, modeling friction/air resistance/a shock
absorber). `F(t)` is an optional external driving force.

The three undriven lanes share the same mass and stiffness, so they share
the same natural frequency `omega0 = sqrt(k/m)`, and differ only in the
damping ratio `zeta = c / c_critical` where `c_critical = 2*sqrt(m*k)` is
the exact damping level at which the system returns to rest as fast as
possible with no oscillation. Underdamped (`zeta < 1`) overshoots and
oscillates while decaying; critically damped (`zeta = 1`) is the fastest
clean return; overdamped (`zeta > 1`) returns slowly without oscillating.
This single ratio is why some doors slam and swing, some close smoothly
in one motion, and some drift shut in slow motion.

The fourth lane adds a periodic external force `F(t) = F0*cos(omega*t)`
with light damping, and slowly sweeps `omega` back and forth across
`omega0`. Steady-state driven-oscillator theory says amplitude scales
roughly like `1 / sqrt((omega0^2 - omega^2)^2 + (c*omega/m)^2)`, which
spikes sharply as `omega` approaches `omega0` — that spike is resonance,
visible live as the gold trace's amplitude swelling and then receding as
the sweep passes through and beyond the natural frequency.

All four lanes are integrated with classic 4th-order Runge-Kutta (RK4) at
240 physics steps per second (60fps x 4 substeps), the same integration
approach used in the double-pendulum and N-body demos, chosen because
explicit Euler integration would visibly drift/blow up on the stiffer
(overdamped, high-c) lane.

## Design choices

- **Color story**: each lane has a distinct neon identity (cyan =
  underdamped, green = critically damped, magenta = overdamped, gold =
  driven/resonant), and within each lane the spring/mass color blends
  toward hot white as instantaneous speed increases — so velocity itself
  is visually legible, not just position.
- **Two synchronized visuals per lane**: a physical coil-spring render
  (zigzag polyline that stretches/compresses with real displacement) sits
  next to a glowing scrolling oscilloscope trace of the same signal, so
  the viewer gets both the intuitive mechanical picture and the more
  abstract "this is a signal" framing at once, without either one being a
  flat, undecorated readout.
- **Glow throughout**: both the coil springs and the waveform traces are
  drawn via an additive-blend glow helper (multiple translucent passes of
  increasing width, blended with `BLEND_RGBA_ADD`), the same technique
  used in the N-body and boids demos that tested well — avoids the "debug
  console" look explicitly flagged as a miss on the self-attention demo.
  There is no plain monospace text as a dominant element; the small stat
  lines per lane and the HUD occupy a clearly minority share of the frame.
  There is no unstyled bar chart or thin single-pixel line anywhere.
- **Motion and pacing**: undriven lanes auto re-kick themselves the
  instant they settle near equilibrium, so the demo is never visually
  dead no matter when a recording starts. The driven lane's frequency
  sweep is tuned (8-second half-period) so a resonance swell-and-fade is
  visible within a normal 10-20s recording window.
- **Smoothness**: real 60fps `clock.tick(60)` loop, with the physics
  itself run at 4 substeps per frame (240Hz) via RK4 for a numerically
  accurate, visually smooth response even on the stiffest (overdamped)
  lane — no snapping or discontinuous jumps.

## How it was verified

Two methods were used:

1. `python3 -m py_compile spring_mass_damper.py` — passed, confirms valid
   syntax.
2. A throwaway headless test (deleted after use, not part of this PR)
   ran the actual `Oscillator` update logic *and* the actual rendering
   functions (`draw_spring`, `glow_circle`, `draw_glow_line`) for 1200
   frames (20 simulated seconds) across all 4 lanes, using
   `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` pygame so the real
   render calls executed without a physical display. Every frame asserted
   `x` and `v` were finite (no NaN) and bounded (`< 1e6`). Result: **all
   1200 frames across all 4 lanes completed with no exceptions and no
   NaN/blowup**; final state was sane for every lane (e.g. underdamped
   settled to a small oscillation having self-re-kicked 3 times;
   critically damped re-kicked 15 times, consistent with its fast
   settle-and-repeat cycle; overdamped barely moving; driven lane mid-
   oscillation as expected).

## What it teaches

The damped harmonic oscillator is one of the most widely applicable
equations in engineering: it governs car suspensions, door closers,
building/bridge sway under wind or seismic load, shock absorbers,
electrical RLC circuits, and audio equalizer filters. The damping ratio
is the single dial that separates "absorbs energy smoothly" from
"oscillates dangerously," and resonance — amplitude spiking when a
driving frequency matches a system's natural frequency — is the same
mechanism behind phenomena from shattering a wine glass with sound to
the (partially mythologized but instructive) Tacoma Narrows Bridge
collapse, and is why engineers deliberately design structures to keep
their natural frequency away from expected external vibration sources.

## To do before posting

- [ ] Run the script locally and confirm the window looks right
- [ ] Record a 10-20s clip (try to catch the gold lane's resonance swell)
- [ ] Review caption.txt, adjust if desired
- [ ] Post natively (upload video directly, don't link out)
